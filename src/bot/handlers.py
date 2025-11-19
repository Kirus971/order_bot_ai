"""Bot handlers"""
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from .states import RegistrationStates, OrderStates
from .keyboards import (
    get_confirm_order_keyboard,
    get_user_approval_keyboard,
    get_admin_confirm_order_keyboard
)
from src.config import get_settings
from src.database import User, Order as OrderModel
from src.ai_service import get_order_parser
from src.utils import format_order_response, format_admin_order_message
from src.text import start_0, start_1, start_2
from src.google_sheets import get_google_sheets_service
from datetime import datetime


logger = logging.getLogger(__name__)


def setup_handlers(router: Router, bot: Bot, dp: Dispatcher):
    """Setup all bot handlers"""
    settings = get_settings()
    admin_ids = settings.bot.admin_ids
    
    # Store bot instance for use in nested functions
    bot_instance = bot
    
    @router.message(Command("start"))
    async def cmd_start(message: Message, state: FSMContext):
        """Handle /start command - user registration"""
        user_id = message.from_user.id
        logger.info(f"User {user_id} started bot")
        
        # Check if user exists in database
        user = await User.get_by_id(user_id)
        
        if user:
            if user.approved:
                await message.answer(start_2)
                await state.set_state(OrderStates.waiting_for_order)
            else:
                await message.answer("Ваша регистрация ожидает подтверждения администратора.")
        else:
            # Start registration
            await message.answer(start_1)
            await state.set_state(RegistrationStates.waiting_for_organization)

    @router.message(RegistrationStates.waiting_for_organization)
    async def process_organization(message: Message, state: FSMContext):
        """Process organization name during registration"""
        user_id = message.from_user.id
        current_date = datetime.now()
        mysql_timestamp = current_date.strftime('%Y-%m-%d %H:%M:%S')
        # Create user in database
        user = User(
            user_id=user_id,
            tg_account=f'@{message.from_user.username}',
            user_info=message.text,
            approved=False,
            date_register=mysql_timestamp,
            user_name=message.from_user.first_name
        )
        await user.save()
        
        # Send approval request to admin
        keyboard = get_user_approval_keyboard(user_id)
        
        for admin_id in admin_ids:
            try:
                await bot_instance.send_message(
                    admin_id,
                    f"🔔 Новый пользователь хочет зарегистрироваться:\n"
                    f"ID: {user_id}\n"
                    f"Имя: {message.from_user.first_name or 'Не указано'}\n"
                    f"Username: @{message.from_user.username or 'Не указано'}\n"
                    f"Организация: {message.text}",
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Failed to send message to admin {admin_id}: {e}")
        
        await message.answer("Спасибо! Ваша заявка отправлена администратору на подтверждение.")
        await state.clear()

    @router.callback_query(F.data.startswith("approve_user:"))
    async def approve_user(callback: CallbackQuery):
        """Handle user approval by admin"""
        if callback.from_user.id not in admin_ids:
            await callback.answer("У вас нет прав для этого действия", show_alert=True)
            return
        
        user_id = int(callback.data.split(":")[1])
        user = await User.get_by_id(user_id)
        
        if user:
            await user.update_approval(True)
            
            # Notify user
            try:
                await bot_instance.send_message(user_id, start_2)
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
            
            # Update admin message
            await callback.message.edit_text(
                f"✅ ПОЛЬЗОВАТЕЛЬ ПОДТВЕРЖДЕН\n\n{callback.message.text}",
                reply_markup=None
            )
            
            await callback.answer("Пользователь подтвержден!")
        else:
            await callback.answer("Пользователь не найден!", show_alert=True)

    @router.callback_query(F.data.startswith("reject_user:"))
    async def reject_user(callback: CallbackQuery):
        """Handle user rejection by admin"""
        if callback.from_user.id not in admin_ids:
            await callback.answer("У вас нет прав для этого действия", show_alert=True)
            return
        
        user_id = int(callback.data.split(":")[1])
        user = await User.get_by_id(user_id)
        
        if user:
            # Delete user (or mark as rejected)
            # For now, we'll just update approval to False
            await user.update_approval(False)
            
            # Notify user
            try:
                await bot_instance.send_message(user_id, "❌ Ваша регистрация отклонена администратором.")
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
            
            # Update admin message
            await callback.message.edit_text(
                f"❌ ПОЛЬЗОВАТЕЛЬ ОТКЛОНЕН\n\n{callback.message.text}",
                reply_markup=None
            )
            
            await callback.answer("Пользователь отклонен!")
        else:
            await callback.answer("Пользователь не найден!", show_alert=True)

    @router.message(F.text)
    async def handle_message(message: Message, state: FSMContext):
        """Handle all text messages"""
        user_id = message.from_user.id
        
        # Check registration
        user = await User.get_by_id(user_id)
        if not user or not user.approved:
            await message.answer(start_0)
            return
        
        current_state = await state.get_state()
        
        # If user is not in order flow, start new order
        if current_state is None or current_state == OrderStates.waiting_for_order.state:
            await handle_new_order(message, state, user)
        # If user is waiting for confirmation, treat as updated order
        elif current_state == OrderStates.waiting_for_confirmation.state:
            await handle_updated_order(message, state, user)

    async def handle_new_order(message: Message, state: FSMContext, user: User):
        """Handle new order"""
        user_id = message.from_user.id
        
        # Show processing message
        processing_msg = await message.answer("🔄 Обрабатываю ваш заказ...")
        
        try:
            # Parse order with AI
            parser = get_order_parser()
            orders_data = await parser.parse_order(message.text)
            
            logger.info(f"Parsed order for user {user_id}: {orders_data}")
            
            # Format response
            response_text = await format_order_response(orders_data)

            response_text += "\n✅ Если все верно - подтвердите заказ кнопкой ниже.\n"
            response_text += "❌ Если есть ошибки - отправьте исправленный текст заказа."
            
            # Send order message with confirmation button
            order_message = await message.answer(
                response_text,
                reply_markup=get_confirm_order_keyboard()
            )
            
            # Save order data to state
            await state.update_data(
                order_message_id=order_message.message_id,
                order_data=orders_data,
                user_message=message.text
            )
            
            await state.set_state(OrderStates.waiting_for_confirmation)
            
        except Exception as e:
            logger.error(f"Error processing order: {e}", exc_info=True)
            await message.answer("❌ Произошла ошибка при обработке заказа. Попробуйте еще раз.")
        finally:
            try:
                await processing_msg.delete()
            except:
                pass

    async def handle_updated_order(message: Message, state: FSMContext, user: User):
        """Handle updated order (when user sends correction)"""
        user_id = message.from_user.id
        
        # Show processing message
        processing_msg = await message.answer("🔄 Обрабатываю уточненный заказ...")
        
        try:
            # Get previous order message ID
            current_data = await state.get_data()
            previous_order_msg_id = current_data.get('order_message_id')
            
            # Update previous message (mark as cancelled)
            if previous_order_msg_id:
                try:
                    await bot_instance.edit_message_text(
                        chat_id=user_id,
                        message_id=previous_order_msg_id,
                        text="❌ ЗАКАЗ ОТМЕНЕН (отправлен уточненный заказ)",
                        reply_markup=None
                    )
                except Exception as e:
                    logger.warning(f"Failed to update previous message: {e}")
            
            # Parse new order
            parser = get_order_parser()
            orders_data = await parser.parse_order(message.text)
            
            # Format response
            response_text = await format_order_response(orders_data)
            
            # Send new order message
            order_message = await message.answer(
                response_text,
                reply_markup=get_confirm_order_keyboard()
            )
            
            # Update state
            await state.update_data(
                order_message_id=order_message.message_id,
                order_data=orders_data,
                user_message=message.text
            )
            
            await state.set_state(OrderStates.waiting_for_confirmation)
            
        except Exception as e:
            logger.error(f"Error processing updated order: {e}", exc_info=True)
            await message.answer("❌ Произошла ошибка при обработке заказа. Попробуйте еще раз.")
        finally:
            try:
                await processing_msg.delete()
            except:
                pass

    @router.callback_query(OrderStates.waiting_for_confirmation, F.data == "confirm_order")
    async def confirm_user_order(callback: CallbackQuery, state: FSMContext):
        """Handle order confirmation by user"""
        user_id = callback.from_user.id
        
        try:
            # Get order data from state
            current_data = await state.get_data()
            order_data = current_data.get('order_data')
            order_message_id = current_data.get('order_message_id')
            
            if not order_data:
                await callback.answer("❌ Данные заказа не найдены", show_alert=True)
                return
            
            # Save order to database
            order = OrderModel(
                order_id=None,
                user_id=user_id,
                order_data=order_data,
                status='pending_admin'
            )
            await order.save()
            
            # Get user info
            user = await User.get_by_id(user_id)
            
            # Format message for admin
            admin_message_text = await format_admin_order_message(
                callback.from_user,
                order_data,
                user.user_info if user else "Неизвестно"
            )
            
            # Send to all admins
            admin_keyboard = get_admin_confirm_order_keyboard(user_id, order_message_id)
            
            for admin_id in admin_ids:
                try:
                    await bot_instance.send_message(
                        admin_id,
                        admin_message_text,
                        reply_markup=admin_keyboard
                    )
                except Exception as e:
                    logger.error(f"Failed to send order to admin {admin_id}: {e}")
            
            # Update user message
            await callback.message.edit_text(
                f"✅ Ваш заказ подтвержден и отправлен менеджеру!\n\n{callback.message.text}",
                reply_markup=None
            )
            
            # Update state
            await state.update_data(admin_order_id=order.order_id)
            # await state.set_state(OrderStates.waiting_for_admin)
            await state.set_state(OrderStates.waiting_for_order)
            
            await callback.answer("Заказ подтвержден и отправлен менеджеру!")
            
        except Exception as e:
            logger.error(f"Error confirming order: {e}", exc_info=True)
            await callback.message.answer("❌ Произошла ошибка при отправке заказа. Попробуйте еще раз.")
            await callback.answer()

    @router.callback_query(F.data.startswith("admin_confirm:"))
    async def confirm_admin_order(callback: CallbackQuery, state: FSMContext):
        """Handle order confirmation by admin"""
        if callback.from_user.id not in admin_ids:
            await callback.answer("У вас нет прав для этого действия", show_alert=True)
            return
        
        try:
            # Parse callback data
            _, user_id_str, order_message_id_str = callback.data.split(":")
            user_id = int(user_id_str)
            order_message_id = int(order_message_id_str)
            
            # Get user and order data
            user = await User.get_by_id(user_id)
            if not user:
                await callback.answer("Пользователь не найден", show_alert=True)
                return
            
            # Get order from database (we need to find it by user_id and order_message_id)
            # For now, we'll extract order_data from the message text or state
            # In a real implementation, you might want to store order_id in callback data
            
            logger.info(f"Order confirmed by admin. User ID: {user_id}, Order Message ID: {order_message_id}")
            
            # Try to get order data from database
            # We'll search for the most recent order from this user with pending_admin status
            from src.database.connection import get_database
            db = get_database()
            orders = await db.execute_query(
                "SELECT * FROM orders WHERE user_id = %s AND status = 'pending_admin' ORDER BY created_at DESC LIMIT 1",
                (user_id,)
            )
            username = await db.execute_query(
                "SELECT tg_account FROM users WHERE user_id = %s LIMIT 1",
                (user_id,)
            )
            order_data = None
            if orders:
                import json
                order_data = json.loads(orders[0]['order_data'])
                # Update order status
                await db.execute_command(
                    "UPDATE orders SET status = 'confirmed' WHERE order_id = %s",
                    (orders[0]['order_id'],)
                )
            
            # Write to Google Sheets
            if order_data:
                try:
                    sheets_service = get_google_sheets_service()
                    # Get user phone if available (you might want to store it in User model)
                    phone = None  # TODO: Get phone from user profile or database
                    
                    # Get username from callback or try to get from user
                    # username = callback.from_user.username or callback.from_user.first_name or ""
                    
                    success = await sheets_service.write_order(
                        user_id=user_id,
                        username=username[0]['tg_account'],
                        phone=phone,
                        organization=user.user_info,
                        order_data=order_data,
                        order_date=datetime.now()
                    )
                    
                    if success:
                        logger.info(f"Order written to Google Sheets for user {user_id}")
                    else:
                        logger.warning(f"Failed to write order to Google Sheets for user {user_id}")
                except Exception as e:
                    logger.error(f"Error writing to Google Sheets: {e}", exc_info=True)
            
            # Update admin message
            await callback.message.edit_text(
                f"✅ ЗАКАЗ ПОДТВЕРЖДЕН АДМИНОМ\n\n{callback.message.text}",
                reply_markup=None
            )
            
            # Notify user
            try:
                await bot_instance.send_message(
                    user_id,
                    "🎉 Ваш заказ подтвержден администратором!"
                )
                await state.set_state(OrderStates.waiting_for_order)
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
            
            await callback.answer("Заказ подтвержден!")
            
        except Exception as e:
            logger.error(f"Error confirming order by admin: {e}", exc_info=True)
            await callback.answer("❌ Ошибка при подтверждении заказа", show_alert=True)

