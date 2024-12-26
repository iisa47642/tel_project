import sqlite3
from aiogram import BaseMiddleware, Bot
from typing import Callable, Dict, Any, Awaitable, Union
from aiogram.types import Message, CallbackQuery, TelegramObject
from database.db import get_user
from datetime import datetime, time
import pytz

_bot: Bot = None  # Placeholder for the bot instance

def setup_router(dp, bot: Bot):
    global _bot
    _bot = bot


class UserCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        existing_user = await get_user(user_id=user_id)

        if not existing_user and event.text != '/start':
            await event.answer("Пожалуйста, используйте команду /start, чтобы начать работу с ботом.")
            return

        return await handler(event, data)


# Настройки
TIMEZONE = pytz.timezone('Europe/Moscow')
SWITCH_TIME = time(hour=14, minute=0)

class ModeMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self.previous_mode = None
        super().__init__()
        
    def get_current_mode(self) -> int:
        current_time = datetime.now(TIMEZONE).time()
        return 2 if current_time >= SWITCH_TIME else 1

    async def notify_mode_change(self, new_mode: int) -> None:
        if self.previous_mode is not None and self.previous_mode != new_mode:
            admin_id = 842589261
            await _bot.send_message(
                admin_id,
                f"Режим работы бота изменен на {new_mode}"
            )
            await self.log_mode_change(new_mode)
        self.previous_mode = new_mode

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Получаем текущий режим
        current_mode = self.get_current_mode()
        
        # Проверяем изменение режима
        if self.previous_mode != current_mode:
            await self.notify_mode_change(current_mode)
            self.previous_mode = current_mode

        # Добавляем текущий режим в data для использования в фильтре
        data['current_mode'] = current_mode
        return await handler(event, data)
