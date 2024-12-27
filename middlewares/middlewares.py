import asyncio
import sqlite3
from aiogram import BaseMiddleware, Bot
from typing import Callable, Dict, Any, Awaitable, Union
from aiogram.types import Message, CallbackQuery, TelegramObject
from database.db import get_user
from datetime import datetime, time, timedelta
import pytz
import logging

_bot: Bot = None  # Placeholder for the bot instance

def setup_router(dp, bot: Bot):
    global _bot
    _bot = bot
    
    
TIMEZONE = pytz.timezone('Europe/Moscow')
MODE_2_START = time(hour=14, minute=0)
MODE_2_END = time(hour=16, minute=0)
MODE_3_END = time(hour=18, minute=0)

def get_current_mode() -> int:
    current_time = datetime.now(TIMEZONE).time()
    
    if MODE_2_START <= current_time < MODE_2_END:
        mode = 2
    elif MODE_2_END <= current_time < MODE_3_END:
        mode = 3
    else:
        mode = 1
    
    logging.info(f"Current time: {current_time}, Current mode: {mode}")
    return mode


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, limit=0.75):
        self.rate_limit = limit
        self.user_timeouts = {}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id

        if user_id in self.user_timeouts:
            last_time = self.user_timeouts[user_id]
            if datetime.now() - last_time < timedelta(seconds=self.rate_limit):
                return

        self.user_timeouts[user_id] = datetime.now()
        return await handler(event, data)

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

class ModeMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self.previous_mode = None
        super().__init__()
        
    def get_current_mode(self) -> int:
        return get_current_mode()

    async def notify_mode_change(self, new_mode: int) -> None:
        if self.previous_mode is not None and self.previous_mode != new_mode:
            admin_id = 842589261
            mode_descriptions = {
                1: "стандартный режим",
                2: "второй режим",
                3: "третий режим"
            }
            await _bot.send_message(
                admin_id,
                f"Режим работы бота изменен на {new_mode} ({mode_descriptions[new_mode]})"
            )
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


