import asyncio
from collections import defaultdict
from dataclasses import dataclass
import os

from aiogram import BaseMiddleware, Bot
from typing import Callable, Dict, Any, Awaitable, List, Union
from aiogram.types import Message, CallbackQuery, TelegramObject

from config.config import load_config
from database.db import get_user, select_battle_settings
from datetime import datetime, time, timedelta
import pytz
import logging
from tasks.task_handlers import TaskManager
from database.db import select_all_admins

import asyncio
from typing import Any, Callable, Dict, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from cachetools import TTLCache

class MiddlewareData:
    _bot: Bot = None
    _task_manager: TaskManager = None

def setup_router(dp, bot: Bot, tm: TaskManager):
    MiddlewareData._bot = bot
    MiddlewareData._task_manager = tm





class AlbumsMiddleware(BaseMiddleware):
    def __init__(self, wait_time_seconds: int):
        super().__init__()
        self.wait_time_seconds = wait_time_seconds
        self.albums_cache = TTLCache(
            ttl=float(wait_time_seconds) + 20.0,
            maxsize=1000
        )
        self.lock = asyncio.Lock()

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        event: Message

        # Если нет media_group_id (не альбом), просто передаем дальше
        if event.media_group_id is None:
            return await handler(event, data)

        album_id: str = event.media_group_id

        async with self.lock:
            self.albums_cache.setdefault(album_id, list())
            self.albums_cache[album_id].append(event)

        # Ждем некоторое время, пока соберутся все сообщения альбома
        await asyncio.sleep(self.wait_time_seconds)

        # Находим наименьший message_id в альбоме
        my_message_id = smallest_message_id = event.message_id

        for item in self.albums_cache[album_id]:
            smallest_message_id = min(smallest_message_id, item.message_id)

        # Если текущий message_id не наименьший, пропускаем
        if my_message_id != smallest_message_id:
            return

        # Если текущий message_id наименьший,
        # добавляем все сообщения альбома в data
        data['album'] = self.albums_cache[album_id]

        return await handler(event, data)

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, limit: float = 1.0, admin_ids: List[int] = []) -> None:
        self.rate_limit = limit
        self.user_timeouts: Dict[int, datetime] = {}
        self.cleanup_threshold = 1000
        self.admin_ids = admin_ids
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id

        # Пропускаем проверку для админов
        if user_id in self.admin_ids:
            return await handler(event, data)

        # Очистка старых записей
        if len(self.user_timeouts) > self.cleanup_threshold:
            current_time = datetime.now()
            self.user_timeouts = {
                user_id: timestamp 
                for user_id, timestamp in self.user_timeouts.items()
                if (current_time - timestamp).total_seconds() < self.rate_limit
            }

        current_time = datetime.now()

        # Проверяем ограничение
        if user_id in self.user_timeouts:
            last_time = self.user_timeouts[user_id]
            time_passed = (current_time - last_time).total_seconds()
            
            if time_passed < self.rate_limit:
                if isinstance(event, Message):
                    await event.answer(
                        f"😤 Пожалуйста, подождите {self.rate_limit - time_passed:.1f} секунд"
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        f"😤 Пожалуйста, подождите {self.rate_limit - time_passed:.1f} секунд",
                        show_alert=True
                    )
                return

        # Обновляем время последнего запроса
        self.user_timeouts[user_id] = current_time
        
        # Продолжаем обработку
        return await handler(event, data)



class UserCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        try:
            user_id = event.from_user.id
        except Exception as e:
            print("Не удалось получить id пользователя " + e)
        existing_user = await get_user(user_id=user_id)
        if not existing_user and not event.text.startswith('/start'):
            await event.answer("Пожалуйста, используйте команду /start, чтобы начать работу с ботом.")
            return
        
        if existing_user and existing_user[9] == 1:
            await event.answer("Ваш профиль был заблокирован, вы не имеете возможности пользоваться ботом")
            return
        
        return await handler(event, data)



class ModeMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self.previous_mode = None
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        try:
            if not MiddlewareData._task_manager:
                logging.error("TaskManager not initialized in middleware")
                return await handler(event, data)

            current_mode = await MiddlewareData._task_manager.get_current_mode()
            
            if self.previous_mode != current_mode:
                await self.notify_mode_change(current_mode)
                self.previous_mode = current_mode

            data['current_mode'] = current_mode

            logging.info(f"Request processed in mode {current_mode}")

            return await handler(event, data)

        except Exception as e:
            logging.error(f"Error in middleware: {e}")
            return await handler(event, data)

    async def notify_mode_change(self, new_mode: int):
        """Уведомление об изменении режима"""
        if not MiddlewareData._bot:
            logging.error("Bot not initialized in middleware")
            return

        mode_descriptions = {
            1: "нет активного баттла",
            2: "активный баттл"
        }
        
        if self.previous_mode is not None and self.previous_mode != new_mode:
            message = (
                f"🔄 Режим работы изменен\n"
                f"Предыдущий режим: {self.previous_mode} ({mode_descriptions[self.previous_mode]})\n"
                f"Новый режим: {new_mode} ({mode_descriptions[new_mode]})"
            )

            dirname = os.path.dirname(__file__)
            filename = os.path.abspath(os.path.join(dirname, '..', 'config/config.env'))
            config = load_config(filename)
            SUPER_ADMIN_IDS = config.tg_bot.super_admin_ids

            #TODO
            ADMIN_IDS = await select_all_admins()
            admins_list = []
            if ADMIN_IDS:
                admins_list = [i[0] for i in ADMIN_IDS]
            admins_list += SUPER_ADMIN_IDS
            for admin_id in admins_list:
                try:
                    await MiddlewareData._bot.send_message(admin_id, message)
                    logging.info(f"Mode changed from {self.previous_mode} to {new_mode}")
                except Exception as e:
                    logging.error(f"Failed to send mode change notification: {e}")


