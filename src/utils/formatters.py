"""Message formatters"""
import logging
from typing import List, Dict
from src.database import Assortment

logger = logging.getLogger(__name__)


async def format_order_response(orders_data: List[Dict]) -> str:
    """Format order data into readable text"""
    response = "📦 ВАШ ЗАКАЗ:\n"
    
    if not orders_data:
        return "❌ Не удалось обработать заказ. Попробуйте еще раз."
    
    # Check if it's just a message (no order)
    first_order = orders_data[0]
    if first_order.get('message') and not first_order.get('adress'):
        return first_order.get('message', '')
    
    # Get all products for lookup
    all_products = await Assortment.get_all()
    product_map = {p.good_id: p for p in all_products}
    
    for i, order in enumerate(orders_data, 1):
        response += f"\nЗаказ #{i}:\n"
        response += f"Организация {order.get('company_name','не распознано')}:\n"
        response += f"📅 Дата доставки: {order.get('date_delivery', 'Не указана')}\n"
        response += f"🏠 Адрес: {order.get('adress', 'Не указан')}\n"
        response += "🛒 Товары:\n"
        
        goods = order.get('goods', {})

        cost_all = 0
        
        if goods:
            for product_id_str, quantity in goods.items():
                try:
                    product_id = int(product_id_str)
                    product = product_map.get(product_id)
                    quantity_all = quantity * product.min_size
                    
                    if product:
                        response += f"  • {product.name}: {quantity_all} {product.type}\n"
                        # Calculate cost
                        payment_type = order.get('payment_type', 'price_amt')
                        price = product.price_c if payment_type == 'price_c' else product.price_amt
                        cost_all += price * (quantity_all)
                    else:
                        response += f"  • Товар ID {product_id}: {quantity}\n"
                except (ValueError, TypeError):
                    response += f"  • {product_id_str}: {quantity}\n"
        else:
            response += "  • Товары не распознаны. Напишите ваш заказ заново\n"
        
        if cost_all > 0:
            payment_type = order.get('payment_type', 'price_amt')
            payment_text = 'наличный расчет' if payment_type == 'price_c' else 'безналичный расчет'
            response += f"\n💰 Сумма заказа: {cost_all:.2f} руб. ({payment_text})\n"
    
    
    return response


async def format_admin_order_message(from_user, order_data: List[Dict], organization: str = "Неизвестно") -> str:
    """Format order message for admin"""
    user_id = from_user.id
    user_name = from_user.username or from_user.first_name or "Неизвестно"
    
    message = f"📦 НОВЫЙ ЗАКАЗ\n\n"
    message += f"👤 Клиент: @{user_name} (ID: {user_id})\n\n"
    
    # Add order details
    order_text = await format_order_response(order_data)
    message += order_text
    
    return message

