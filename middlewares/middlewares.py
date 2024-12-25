import sqlite3
from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable
from aiogram.types import Message
from database.db import get_user

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