"""Database models and data access"""
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime
from .connection import get_database


@dataclass
class User:
    """User model"""
    user_id: int
    organization: str
    approved: bool
    created_at: Optional[datetime] = None

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
                organization=row["organization"],
                approved=bool(row["approved"]),
                created_at=row.get("created_at"),
            )
        return None

    async def save(self):
        """Save user to database"""
        db = get_database()
        await db.execute_command(
            """INSERT INTO users (user_id, organization, approved, created_at)
               VALUES (%s, %s, %s, NOW())
               ON DUPLICATE KEY UPDATE
               organization = VALUES(organization),
               approved = VALUES(approved)""",
            (self.user_id, self.organization, int(self.approved))
        )

    async def update_approval(self, approved: bool):
        """Update user approval status"""
        self.approved = approved
        db = get_database()
        await db.execute_command(
            "UPDATE users SET approved = %s WHERE user_id = %s",
            (int(approved), self.user_id)
        )


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

