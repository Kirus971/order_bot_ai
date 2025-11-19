"""Database models and data access"""
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime
from .connection import get_database


@dataclass
class User:
    """User model for new database structure"""
    user_id: int
    user_name: str
    tg_account: Optional[str] = None
    user_info: Optional[str] = None
    phone: Optional[str] = None
    approved: bool = False
    date_register: Optional[datetime] = None

    def __init__(self, user_id: int, user_name: str, tg_account: Optional[str] = None, 
                 user_info: Optional[str] = None, phone: Optional[str] = None, 
                 approved: bool = False, date_register: Optional[datetime] = None):
        self.user_id = user_id
        self.user_name = user_name
        self.tg_account = tg_account
        self.user_info = user_info
        self.phone = phone
        self.approved = approved
        self.date_register = date_register

    @classmethod
    async def get_by_id(cls, user_id: int) -> Optional["User"]:
        """Get user by ID"""
        db = get_database()
        result = await db.execute_query(
            "SELECT * FROM users WHERE user_id = %s",
            (user_id,)
        )
        if result:
            row = result[0]
            return cls(
                user_id=row["user_id"],
                user_name=row["user_name"],
                tg_account=row.get("tg_account"),
                user_info=row.get("user_info"),
                phone=row.get("phone"),
                approved=bool(row["approved"]),
                date_register=row.get("date_register"),
            )
        return None

    @classmethod
    async def get_by_username(cls, user_name: str) -> Optional["User"]:
        """Get user by username"""
        db = get_database()
        result = await db.execute_query(
            "SELECT * FROM users WHERE user_name = %s",
            (user_name,)
        )
        if result:
            row = result[0]
            return cls(
                user_id=row["user_id"],
                user_name=row["user_name"],
                tg_account=row.get("tg_account"),
                user_info=row.get("user_info"),
                phone=row.get("phone"),
                approved=bool(row["approved"]),
                date_register=row.get("date_register"),
            )
        return None

    async def save(self):
        """Save user to database"""
        db = get_database()
        await db.execute_command(
            """INSERT INTO users (user_id, user_name, tg_account, user_info, phone, approved, date_register)
               VALUES (%s, %s, %s, %s, %s, %s, COALESCE(%s, NOW()))
               ON DUPLICATE KEY UPDATE
               user_name = VALUES(user_name),
               tg_account = VALUES(tg_account),
               user_info = VALUES(user_info),
               phone = VALUES(phone),
               approved = VALUES(approved)""",
            (self.user_id, self.user_name, self.tg_account, self.user_info, 
             self.phone, int(self.approved), self.date_register)
        )

    async def update_approval(self, approved: bool):
        """Update user approval status"""
        self.approved = approved
        db = get_database()
        await db.execute_command(
            "UPDATE users SET approved = %s WHERE user_id = %s",
            (int(approved), self.user_id)
        )

    async def update_info(self, user_name: Optional[str] = None, tg_account: Optional[str] = None,
                         user_info: Optional[str] = None, phone: Optional[str] = None):
        """Update user information"""
        if user_name is not None:
            self.user_name = user_name
        if tg_account is not None:
            self.tg_account = tg_account
        if user_info is not None:
            self.user_info = user_info
        if phone is not None:
            self.phone = phone

        db = get_database()
        await db.execute_command(
            """UPDATE users 
               SET user_name = COALESCE(%s, user_name),
                   tg_account = COALESCE(%s, tg_account),
                   user_info = COALESCE(%s, user_info),
                   phone = COALESCE(%s, phone)
               WHERE user_id = %s""",
            (user_name, tg_account, user_info, phone, self.user_id)
        )

    @classmethod
    async def create(cls, user_id: int, user_name: str, tg_account: Optional[str] = None,
                    user_info: Optional[str] = None, phone: Optional[str] = None, 
                    approved: bool = False) -> "User":
        """Create new user"""
        user = cls(
            user_id=user_id,
            user_name=user_name,
            tg_account=tg_account,
            user_info=user_info,
            phone=phone,
            approved=approved,
            date_register=datetime.now()
        )
        await user.save()
        return user

    def to_dict(self) -> dict:
        """Convert user to dictionary"""
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "tg_account": self.tg_account,
            "user_info": self.user_info,
            "phone": self.phone,
            "approved": self.approved,
            "date_register": self.date_register.isoformat() if self.date_register else None
        }

    def __str__(self) -> str:
        return f"User({self.user_id}, {self.user_name}, approved: {self.approved})"


@dataclass
class Assortment:
    """Product assortment model"""
    good_id: int
    name: str
    type: str
    price_c: float
    price_amt: float
    min_size: float

    @classmethod
    async def get_all(cls) -> List["Assortment"]:
        """Get all products from assortment"""
        db = get_database()
        result = await db.execute_query("SELECT * FROM assortment")
        return [
            cls(
                good_id=row["good_id"],
                name=row["name"],
                type=row["type"],
                price_c=float(row["price_c"]),
                price_amt=float(row["price_amt"]),
                min_size=float(row["min_size"]),
            )
            for row in result
        ]

    @classmethod
    async def get_by_id(cls, good_id: int) -> Optional["Assortment"]:
        """Get product by ID"""
        db = get_database()
        result = await db.execute_query(
            "SELECT * FROM assortment WHERE good_id = %s",
            (good_id,)
        )
        if result:
            row = result[0]
            return cls(
                good_id=row["good_id"],
                name=row["name"],
                type=row["type"],
                price_c=float(row["price_c"]),
                price_amt=float(row["price_amt"]),
                min_size=float(row["min_size"]),
            )
        return None


@dataclass
class Order:
    """Order model"""
    order_id: Optional[int]
    user_id: int
    order_data: Dict
    status: str
    created_at: Optional[datetime] = None

    async def save(self) -> int:
        """Save order to database"""
        import json
        db = get_database()
        order_id = await db.execute_command(
            """INSERT INTO orders (user_id, order_data, status, created_at)
               VALUES (%s, %s, %s, NOW())""",
            (self.user_id, json.dumps(self.order_data, ensure_ascii=False), self.status)
        )
        self.order_id = order_id
        return order_id

    async def update_status(self, status: str):
        """Update order status"""
        self.status = status
        db = get_database()
        await db.execute_command(
            "UPDATE orders SET status = %s WHERE order_id = %s",
            (status, self.order_id)
        )

