# tasks/task_handlers.py
from aiogram import Bot
from typing import Optional
import asyncio
from routers.channel_router import send_battle_pairs, end_round, announce_winner, delete_previous_messages
from database.db import get_participants, remove_losers, save_message_ids, delete_users_in_batl

class TaskManager:
    def __init__(self):
        self.admin_id: int = 842589261
        self._bot: Optional[Bot] = None
        self.channel_id: int = -1002430244531
        self.round_duration: int = 30
        self.break_duration: int = 30
        self.min_votes_for_single: int = 2  # Минимум голосов для одиночного участника

    @property
    def bot(self) -> Bot:
        return self._bot

    @bot.setter
    def bot(self, bot: Bot):
        self._bot = bot

    async def start_battle(self):
        round_number = 1
        while True:
            participants = await get_participants()
            if len(participants) == 1:
                await self.end_battle(participants[0])
                break
            
            # Удаляем сообщения предыдущего раунда
            await delete_previous_messages(self.bot, self.channel_id)
            
            # Отправляем сообщение о начале нового раунда
            start_message = await self.bot.send_message(self.channel_id, f"Начинается раунд {round_number}!")
            await save_message_ids([start_message.message_id])
            
            # Отправляем пары участников и сохраняем ID сообщений
            message_ids = await send_battle_pairs(self.bot, self.channel_id)
            await save_message_ids(message_ids)
            # вот тут можно будет добавить остановку на ночь
            # Ждем окончания раунда
            await asyncio.sleep(self.round_duration)
            
            # Завершаем раунд и сохраняем ID итоговых сообщений
            end_values = await end_round(self.bot, self.channel_id, self.min_votes_for_single)
            end_message_ids = end_values[0]
            await save_message_ids(end_message_ids)
            losers = end_values[1]
            
            # Удаляем проигравших из базы данных
            await remove_losers(losers)
            round_number += 1
            
            # Делаем перерыв перед следующим раундом
            await asyncio.sleep(self.break_duration)

    async def end_battle(self, winner):
        # Удаляем все предыдущие сообщения
        await delete_previous_messages(self.bot, self.channel_id)
        
        # Объявляем победителя
        final_message_ids = await announce_winner(self.bot, self.channel_id, winner)
        await save_message_ids(final_message_ids)
        await delete_users_in_batl()
        
        # Отправляем личное сообщение победителю
        await self.bot.send_message(winner['user_id'], "Поздравляем! Вы победили в баттле!")