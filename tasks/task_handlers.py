from aiogram import Bot
from typing import Optional
import logging
from functools import wraps
from middlewares.middlewares import get_current_mode
# Декоратор для задач определенного режима
def mode_task(mode_number: int):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if get_current_mode() == mode_number:
                return await func(*args, **kwargs)
        return wrapper
    return decorator


class TaskManager:
    def __init__(self):
        self.admin_id: int = 842589261
        self._bot: Optional[Bot] = None

    @property
    def bot(self) -> Bot:
        return self._bot

    @bot.setter
    def bot(self, bot: Bot):
        self._bot = bot

    @mode_task(mode_number=1)
    async def mode_1_task(self):
        print('Внутри задачи 1')
        await self.bot.send_message(
            self.admin_id,
            "Выполняется задача режима 1"
        )

    @mode_task(mode_number=2)
    async def mode_2_task(self):
        await self.bot.send_message(
            self.admin_id,
            "Выполняется задача режима 2"
        )

    @mode_task(mode_number=3)
    async def mode_3_task(self):
        await self.bot.send_message(
            self.admin_id,
            "Выполняется задача режима 3"
        )

    async def general_task(self):
        """Общая задача, не зависящая от режима"""
        await self.bot.send_message(
            self.admin_id,
            "Выполняется общая задача"
        )
