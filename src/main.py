"""Main application entry point with FastAPI and webhooks"""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.fsm.storage.memory import MemoryStorage

from src.config import get_settings
from src.database import get_database
from src.bot import setup_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global bot and dispatcher instances
bot: Bot = None
dp: Dispatcher = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    global bot, dp
    
    # Startup
    settings = get_settings()
    
    # Initialize database
    db = get_database()
    await db.connect()
    logger.info("Database connected")
    
    # Initialize bot
    bot = Bot(token=settings.bot.token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    router = dp.router
    
    # Setup handlers
    setup_handlers(router, bot, dp)
    
    # Initialize bot (don't start polling if webhook is configured)
    if not settings.webhook:
        # Start polling only if webhook is not configured
        await dp.start_polling(bot, skip_updates=True)
        logger.info("Bot started with polling")
    else:
        # Setup webhook
        webhook_info = await bot.get_webhook_info()
        
        if webhook_info.url != settings.webhook.webhook_url:
            webhook_kwargs = {"url": settings.webhook.webhook_url}
            
            # Add certificate if provided
            if settings.webhook.certificate_path:
                try:
                    with open(settings.webhook.certificate_path, 'rb') as cert:
                        webhook_kwargs["certificate"] = cert.read()
                except FileNotFoundError:
                    logger.warning(f"Certificate file not found: {settings.webhook.certificate_path}")
            
            await bot.set_webhook(**webhook_kwargs)
            logger.info(f"Webhook set to: {settings.webhook.webhook_url}")
        else:
            logger.info("Webhook already set, no action taken")
        
        logger.info("Bot started with webhook")
    
    yield
    
    # Shutdown
    if settings.webhook:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted")
    
    await db.close()
    await bot.session.close()
    logger.info("Bot stopped")


# Create FastAPI app
app = FastAPI(
    title="Order Bot API",
    description="Telegram bot for order processing with AI",
    lifespan=lifespan
)

# Путь для webhook нужно сделать сложнее для безопасности
@app.post("/webhook")
async def webhook_handler(request: Request):
    """Handle webhook requests from Telegram"""
    try:
        data = await request.json()
        update = Update(**data)
        
        if dp and bot:
            await dp.feed_update(bot, update)
        
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "bot": "active" if bot else "inactive"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    import os
    
    # Run FastAPI server
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        log_level="info"
    )
