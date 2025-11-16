"""AI service for parsing orders from text"""
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from openai import AsyncOpenAI, BadRequestError
from src.config import get_settings
from src.database import Assortment

logger = logging.getLogger(__name__)


class OrderParser:
    """Service for parsing orders using OpenAI"""
    
    def __init__(self):
        settings = get_settings().ai
        self.client = AsyncOpenAI(api_key=settings.api_key)
        self.model = settings.model
        self.max_tokens = settings.max_tokens
        self._assortment_cache: Optional[List[Dict]] = None
        self._system_prompt: Optional[str] = None

    async def _get_assortment(self) -> List[Dict]:
        """Get assortment from database and cache it"""
        if self._assortment_cache is None:
            products = await Assortment.get_all()
            self._assortment_cache = [
                {
                    "good_id": p.good_id,
                    "name": p.name,
                    "type": p.type,
                    "price_c": p.price_c,
                    "price_amt": p.price_amt,
                    "min_size": p.min_size,
                }
                for p in products
            ]
        return self._assortment_cache

    def _build_system_prompt(self, assortment: List[Dict]) -> str:
        """Build system prompt for AI"""
        content = '''
1. Товары (Ассортимент) в формате JSON:
%s
End

Твоя задача: прочитать сообщение от клиента и выявить что он хотел заказать. Определить good_id по названию товара (name)  и кол-во! Выявить Дату доставки,
Выявить Адресса Заказов. 
Вернуть ответ в JSON
[
{'date_delivery':'(дата доставки)','adress':'(Наименование адреса)','goods':{(good_id из ассортимента 1,2 20 и тп):(кол-во товара), ... },'payment_type':(тип оплаты- price_c или price_amt ), company_name : (Название компании из сообщения если явно указанно либо null)
}, ...]
Если Адресов больше 1, то вернуть столько же json в списке
Без переносов строки без посторонних символов
Адрес может быть как 1м словом так и сцифрой или дробью "\\" или "/" или любым знаком
    Пример: [Наименование адреса] 69/1 , [Наименование адреса] 12\\1, [Наименование адреса] 4 или [Наименование адреса]

Примечание: Цены указаны в рублях. "Нал" - оплата наличными, "Безнал" - безналичный расчет. "Мин. объем/партия" - минимальный объем заказа в литрах или минимальное количество штук.
 1 кега - 30 литров. Заказ всегда нужно переаодить в ЛИТРЫ (л.) например если пользватель написал Гаус 1 кега или Гаус 1 то это будет - Гаус 30
 1 термокега - 20 или 25 литров. Если явно не указано что клиент хочет термокегу то считать то он хочет обычную кегу. Если явно не указан объем термокеги считать 25 литров

Заказ может быть в литрах, кегах , термокегах или штуках поле type из ассортемента
    Примечание: Минимальный заказ — определяется min_size из ассортимента.
        литры / кеги : Можно заказать 60 л, 90 л, 120 л и т.д. (кратно полю min_size). В ответах используй правильные склонения: 1 кега, 2 кеги, 5 кег.
        термокеги : Можно заказать 20 / 25 л, 40 /50 ли т.д. (кратно полю min_size). В ответах используй правильные склонения: 1 термокега, 2 термокеги, 5 термокег.
        Штуки : Можно заказать 1, 2, 3 и т.д. (кратно полю min_size). В ответах используй правильные склонения: 1 штука, 2 штуки, 5 штук.

'''
        assortment_json = json.dumps(assortment, ensure_ascii=False)
        return (content % assortment_json).replace("'", '"')

    async def parse_order(self, text: str, previous_messages: Optional[List[str]] = None) -> List[Dict]:
        """
        Parse order from text using AI
        
        Args:
            text: Order text from user
            previous_messages: Optional list of previous messages for context
            
        Returns:
            List of parsed order dictionaries
        """
        try:
            # Get assortment and build prompt
            assortment = await self._get_assortment()
            system_prompt = self._build_system_prompt(assortment)
            
            messages = [
                {'role': 'system', 'content': system_prompt}
            ]
            
            # Add context
            context = f"Сегодняшняя дата: {datetime.now().strftime('%Y-%m-%d')}\n"
            if previous_messages:
                context += "Предыдущие сообщения: " + " | ".join(previous_messages) + "\n"
            context += f"Сообщение: {text}"
            
            messages.append({"role": "user", "content": context})
            
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens
            )
            
            ai_response = response.choices[0].message.content
            messages.append({"role": "assistant", "content": ai_response})
            
            # Parse JSON response
            try:
                parsed = json.loads(ai_response)
                logger.info(f"AI returned valid JSON: {parsed}")
                return parsed if isinstance(parsed, list) else [parsed]
            except json.JSONDecodeError:
                logger.error(f"AI returned invalid JSON: {ai_response}")
                # Try to extract JSON from text
                import re
                json_match = re.search(r'\[.*\]', ai_response, re.DOTALL)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                        return parsed if isinstance(parsed, list) else [parsed]
                    except json.JSONDecodeError:
                        pass
                
                # Return error response
                return [{
                    'date_delivery': None,
                    'adress': None,
                    'goods': {},
                    'payment_type': None,
                    'company_name': None,
                    'message': 'Не удалось распознать заказ. Пожалуйста, попробуйте еще раз или уточните детали заказа.'
                }]
                
        except BadRequestError as e:
            logger.error(f"OpenAI API error: {e}")
            return [{
                'date_delivery': None,
                'adress': None,
                'goods': {},
                'payment_type': None,
                'company_name': None,
                'message': 'Ошибка при обработке заказа. Попробуйте позже.'
            }]
        except Exception as e:
            logger.error(f"Unexpected error in order parsing: {e}")
            return [{
                'date_delivery': None,
                'adress': None,
                'goods': {},
                'payment_type': None,
                'company_name': None,
                'message': 'Произошла ошибка. Попробуйте еще раз.'
            }]


# Global parser instance
_parser: Optional[OrderParser] = None


def get_order_parser() -> OrderParser:
    """Get order parser instance (singleton)"""
    global _parser
    if _parser is None:
        _parser = OrderParser()
    return _parser

