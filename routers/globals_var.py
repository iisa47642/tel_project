from collections import defaultdict
import asyncio
from datetime import datetime
import logging

from database.db import select_battle_settings

# Глобальные переменные
vote_states = {}
user_clicks = {}
pair_locks = defaultdict(asyncio.Lock)
vote_states_locks = defaultdict(asyncio.Lock)
user_last_click = defaultdict(lambda: datetime.min)
click_counters = defaultdict(int)
click_reset_times = defaultdict(lambda: datetime.min)
ROUND_DURATION = 0


# async def initialize_globals():
#     """Инициализирует глобальные переменные, связанные с настройками"""
#     global ROUND_DURATION
#     try:
#         BATTLE_SETTINGS = await select_battle_settings()
#         ROUND_DURATION = BATTLE_SETTINGS[0] // 60
#         logging.info(f"Initialized ROUND_DURATION: {ROUND_DURATION}")
#     except Exception as e:
#         logging.error(f"Error initializing globals: {e}")


async def reset_vote_states():
    """Сбрасывает глобальные переменные, связанные с голосованием"""
    try:
        global vote_states, user_clicks, pair_locks, vote_states_locks, ROUND_DURATION
        global user_last_click, click_counters, click_reset_times

        # Очищаем все состояния
        vote_states.clear()
        user_clicks.clear()
        
        # Пересоздаем defaultdict
        user_last_click = defaultdict(lambda: datetime.min)
        click_counters = defaultdict(int)
        click_reset_times = defaultdict(lambda: datetime.min)
        pair_locks = defaultdict(asyncio.Lock)
        vote_states_locks = defaultdict(asyncio.Lock)
        BATTLE_SETTINGS = await select_battle_settings()
        ROUND_DURATION = BATTLE_SETTINGS[0]
        logging.info("Vote states reset completed")
        return True
    except Exception as e:
        logging.error(f"Error in reset_vote_states: {e}")
        return False

# Экспортируем все необходимые переменные и функции
__all__ = [
    'vote_states', 'user_clicks', 'pair_locks', 'vote_states_locks',
    'user_last_click', 'click_counters', 'click_reset_times',
    'monitor_tasks', 'reset_vote_states','ROUND_DURATION'
]
