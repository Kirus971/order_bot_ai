"""Google Sheets service for writing orders"""
import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from src.config import get_settings
from src.database import Assortment

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """Service for writing orders to Google Sheets"""
    
    def __init__(self):
        settings = get_settings().google_sheets
        self.spreadsheet_id = settings.spreadsheet_id
        self.worksheet_name = settings.worksheet_name
        self._client: Optional[gspread.Client] = None
        self._worksheet: Optional[gspread.Worksheet] = None
        
        # Initialize credentials
        if settings.credentials_json:
            import json
            creds_info = json.loads(settings.credentials_json)
            scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
            credentials = Credentials.from_service_account_info(creds_info, scopes=scope)
            self._client = gspread.authorize(credentials)
        elif settings.credentials_path:
            scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
            credentials = Credentials.from_service_account_file(
                settings.credentials_path, 
                scopes=scope
            )
            self._client = gspread.authorize(credentials)
        else:
            logger.warning("Google Sheets credentials not configured")

    async def _get_worksheet(self):
        """Get or create worksheet (async wrapper)"""
        if not self._client:
            raise ValueError("Google Sheets client not initialized")
        
        if not self._worksheet:
            # Run synchronous operations in thread pool
            def _sync_get_worksheet():
                spreadsheet = self._client.open_by_key(self.spreadsheet_id)
                try:
                    return spreadsheet.worksheet(self.worksheet_name)
                except gspread.exceptions.WorksheetNotFound:
                    # Create worksheet if it doesn't exist
                    worksheet = spreadsheet.add_worksheet(
                        title=self.worksheet_name,
                        rows=1000,
                        cols=10
                    )
                    # Add headers
                    headers = [
                        "id клиента",
                        "Telegram клиента",
                        "Номер телефона",
                        "Организация",
                        "адрес доставки",
                        "Товары",
                        "Общая сумма",
                        "Дата",
                        "форма оплаты",
                        "дата доставки"
                    ]
                    worksheet.append_row(headers)
                    return worksheet
            
            self._worksheet = await asyncio.to_thread(_sync_get_worksheet)
        
        return self._worksheet

    async def write_order(
        self,
        user_id: int,
        username: Optional[str],
        phone: Optional[str],
        organization: str,
        order_data: List[Dict],
        order_date: Optional[datetime] = None
    ) -> bool:
        """
        Write order to Google Sheets
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            phone: User phone number
            organization: Organization name
            order_data: List of order dictionaries from AI parser
            order_date: Order creation date
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self._client:
                logger.error("Google Sheets client not initialized")
                return False
            
            worksheet = await self._get_worksheet()
            
            # Get all products for lookup
            all_products = await Assortment.get_all()
            product_map = {p.good_id: p for p in all_products}
            
            # Process each order (multiple addresses)
            row_all = []
            for order in order_data:
                # Skip if it's just a message
                if order.get('message') and not order.get('adress'):
                    continue
                
                # Format goods
                goods_text = ""
                total_sum = 0.0
                goods = order.get('goods', {})
                
                for product_id_str, quantity in goods.items():
                    try:
                        product_id = int(product_id_str)
                        product = product_map.get(product_id)
                        q_a = quantity * product.min_size
                        if product:
                            payment_type = order.get('payment_type', 'price_amt')
                            price = product.price_c if payment_type == 'price_c' else product.price_amt
                            cost = price * (q_a)
                            total_sum += cost
                            
                            goods_text += f"{product.name} - {q_a} {product.type} {cost:.2f} р.\n"
                    except (ValueError, TypeError):
                        pass
                
                # Format payment type
                payment_type = order.get('payment_type', 'price_amt')
                payment_form = 'НАЛИЧНЫЙ' if payment_type == 'price_c' else 'БЕЗНАЛИЧНЫЙ'
                
                # Format dates
                order_datetime = order_date or datetime.now()
                order_date_str = order_datetime.strftime('%Y-%m-%d %H:%M:%S')
                delivery_date = order.get('date_delivery', '')
                
                # Prepare row data
                row = [
                    order.get('company_name','Не распознано'),  # Организация
                    order.get('adress', ''),  # адрес доставки
                    goods_text.strip(),  # Товары
                    total_sum,  # Общая сумма
                    order_date_str,  # Дата
                    payment_form,  # форма оплаты
                    delivery_date,  # дата доставки
                    str(user_id),  # id клиента
                    f"{username}" if username else "",  # Telegram клиента
                    phone or "",  # Номер телефона
                ]
                # logger.info(f"row ={row}")
                row_all.append(row)
            
            # Append rows to worksheet (run in thread pool)
            def _sync_append_rows():
                worksheet.append_rows(row_all, value_input_option='RAW', insert_data_option='INSERT_ROWS', table_range='A:B')
            
            await asyncio.to_thread(_sync_append_rows)
                # logger.info(f"Order written to Google Sheets: user_id={user_id}, address={order.get('adress')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error writing order to Google Sheets: {e}", exc_info=True)
            return False


# Global service instance
_sheets_service: Optional[GoogleSheetsService] = None


def get_google_sheets_service() -> GoogleSheetsService:
    """Get Google Sheets service instance (singleton)"""
    global _sheets_service
    if _sheets_service is None:
        _sheets_service = GoogleSheetsService()
    return _sheets_service

