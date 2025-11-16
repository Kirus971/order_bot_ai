"""Inline keyboards for bot"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_confirm_order_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for order confirmation"""
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data="confirm_order")
        ]]
    )


def get_user_approval_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Get keyboard for user approval by admin"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_user:{user_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_user:{user_id}")
            ]
        ]
    )


def get_admin_confirm_order_keyboard(user_id: int, order_message_id: int) -> InlineKeyboardMarkup:
    """Get keyboard for admin order confirmation"""
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data=f"admin_confirm:{user_id}:{order_message_id}")
        ]]
    )

