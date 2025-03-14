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
INITIAL_UPDATE_DELAY = 5  # Начальная задержка при ошибке
MAX_UPDATE_DELAY = 30      # Максимальная задержка при повторных ошибках
DELAY_INCREASE_FACTOR = 2  # Множитель увеличения задержки

END_PHASE_THRESHOLD = 0.85  # Последние 15% времени считаются концом раунда
MIN_REQUIRED_VOTES = 5  # Минимальное количество голосов для прохождения
MIN_VOTE_INCREMENT = 1   # Минимальный прирост голосов
MAX_VOTE_INCREMENT = 2   # Максимальный прирост голосов

# Константы для задержек в разных фазах (в секундах)
INITIAL_PHASE_UPDATE_DELAYS = (60.0, 80.0)  # Большие задержки в начальной фазе
MIDDLE_PHASE_UPDATE_DELAYS = (40.0, 50.0)   # Средние задержки в средней фазе
FINAL_PHASE_UPDATE_DELAYS = (5.0, 15.0)    # Минимальные задержки в финальной фазе

# Константы для задержек при пошаговом обновлении счета
INITIAL_PHASE_STEP_DELAYS = (30, 40)
MIDDLE_PHASE_STEP_DELAYS = (20, 25)
FINAL_PHASE_STEP_DELAYS = (20, 25)


MIN_UPDATE_INTERVAL = 2.0  # Минимальный интервал между обновлениями в секундах
FLOOD_CONTROL_RESET = 10# Время сброса флуд-контроля в секундах

CLICK_COOLDOWN = 1.0  # Уменьшаем задержку между кликами до 300мс
MAX_CLICKS_PER_INTERVAL = 5  # Увеличиваем количество разрешенных кликов
RESET_INTERVAL = 5.0  # Интервал сброса счетчика кликов



PHASE_1_END = 0.15    # 0% - 15%
PHASE_2_END = 0.30    # 15% - 30%
PHASE_3_END = 0.45    # 30% - 45%
PHASE_4_END = 0.60    # 45% - 60%
PHASE_5_END = 0.75    # 60% - 75%
PHASE_6_END = 0.90    # 75% - 90%
FINAL_PHASE = 1.0     # 90% - 100%

# Константы для задержек и обновлений
ERROR_RETRY_DELAY = 2.0
BEHAVIOR_UPDATE_INTERVAL = 30  # Интервал обновления параметров поведения


# Разница голосов для разных фаз
INITIAL_PHASE_VOTE_DIFF = 5
MIDDLE_PHASE_VOTE_DIFF = 4
FINAL_PHASE_VOTE_DIFF = 3
MIN_WINNING_MARGIN = 10
BEHAVIOR_LAG = 'lag'
BEHAVIOR_LEAD = 'lead'
BEHAVIOR_NORMAL = 'normal'
PHASE_PARAMETERS = {}

async def reset_vote_states():
    """Сбрасывает глобальные переменные, связанные с голосованием"""
    try:
        global vote_states, user_clicks, pair_locks, vote_states_locks, ROUND_DURATION
        global user_last_click, click_counters, click_reset_times
        global INITIAL_UPDATE_DELAY, MAX_UPDATE_DELAY, DELAY_INCREASE_FACTOR
        global END_PHASE_THRESHOLD, MIN_REQUIRED_VOTES, MIN_VOTE_INCREMENT, MAX_VOTE_INCREMENT
        global INITIAL_PHASE_UPDATE_DELAYS, MIDDLE_PHASE_UPDATE_DELAYS, FINAL_PHASE_UPDATE_DELAYS
        global INITIAL_PHASE_STEP_DELAYS, MIDDLE_PHASE_STEP_DELAYS, FINAL_PHASE_STEP_DELAYS
        global MIN_UPDATE_INTERVAL, FLOOD_CONTROL_RESET, CLICK_COOLDOWN, MAX_CLICKS_PER_INTERVAL, RESET_INTERVAL
        global PHASE_1_END, PHASE_2_END, PHASE_3_END, PHASE_4_END, PHASE_5_END, PHASE_6_END, FINAL_PHASE
        global BEHAVIOR_LAG, BEHAVIOR_LEAD, BEHAVIOR_NORMAL, ERROR_RETRY_DELAY, BEHAVIOR_UPDATE_INTERVAL
        global INITIAL_PHASE_VOTE_DIFF, MIDDLE_PHASE_VOTE_DIFF, FINAL_PHASE_VOTE_DIFF, MIN_WINNING_MARGIN
        global PHASE_PARAMETERS
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
        INITIAL_UPDATE_DELAY = 20
        MAX_UPDATE_DELAY = 60
        DELAY_INCREASE_FACTOR = 2
        END_PHASE_THRESHOLD = 0.85
        MIN_REQUIRED_VOTES = 5
        MIN_VOTE_INCREMENT = 1
        MAX_VOTE_INCREMENT = 2
        INITIAL_PHASE_UPDATE_DELAYS = (60.0, 80.0)
        MIDDLE_PHASE_UPDATE_DELAYS = (40.0, 50.0)
        FINAL_PHASE_UPDATE_DELAYS = (5.0, 15.0)
        INITIAL_PHASE_STEP_DELAYS = (30, 40)
        MIDDLE_PHASE_STEP_DELAYS = (20, 25)
        FINAL_PHASE_STEP_DELAYS = (5.0, 15.0)
        MIN_UPDATE_INTERVAL = 0.5
        FLOOD_CONTROL_RESET = 10
        CLICK_COOLDOWN = 1.0
        MAX_CLICKS_PER_INTERVAL = 5
        RESET_INTERVAL = 30.0
        PHASE_1_END = 0.15
        PHASE_2_END = 0.30
        PHASE_3_END = 0.45
        PHASE_4_END = 0.60
        PHASE_5_END = 0.75
        PHASE_6_END = 0.90
        FINAL_PHASE = 1.0
        BEHAVIOR_LAG = 'lag'
        BEHAVIOR_LEAD = 'lead'
        BEHAVIOR_NORMAL = 'normal'
        ERROR_RETRY_DELAY = 2.0
        BEHAVIOR_UPDATE_INTERVAL = 30
        INITIAL_PHASE_VOTE_DIFF = 5
        MIDDLE_PHASE_VOTE_DIFF = 4
        FINAL_PHASE_VOTE_DIFF = 3
        MIN_WINNING_MARGIN = 10
        PHASE_PARAMETERS = {
        1: {  # 0-15%
        'allowed_difference': INITIAL_PHASE_VOTE_DIFF,
        'step_delays': INITIAL_PHASE_STEP_DELAYS,
        'update_delays': INITIAL_PHASE_UPDATE_DELAYS,
        'behavior': BEHAVIOR_LAG,
        'behavior_params': {
            'min_duration': 1,
            'max_duration': 2,
            'min_difference': 3,
            'max_difference': 5
        }
    },
    2: {  # 15-30%
        'allowed_difference': MIDDLE_PHASE_VOTE_DIFF,
        'step_delays': MIDDLE_PHASE_STEP_DELAYS,
        'update_delays': MIDDLE_PHASE_UPDATE_DELAYS,
        'behavior': BEHAVIOR_LEAD,
        'behavior_params': {
            'min_duration': 1,
            'max_duration': 2,
            'min_difference': 1,
            'max_difference': 4
        }
    },
    3: {  # 30-45%
        'allowed_difference': MIDDLE_PHASE_VOTE_DIFF,
        'step_delays': MIDDLE_PHASE_STEP_DELAYS,
        'update_delays': MIDDLE_PHASE_UPDATE_DELAYS,
        'behavior': BEHAVIOR_LAG,
        'behavior_params': {
            'min_duration': 1,
            'max_duration': 3,
            'min_difference': 3,
            'max_difference': 5
        }
    },
    4: {  # 45-60%
        'allowed_difference': MIDDLE_PHASE_VOTE_DIFF,
        'step_delays': MIDDLE_PHASE_STEP_DELAYS,
        'update_delays': MIDDLE_PHASE_UPDATE_DELAYS,
        'behavior': BEHAVIOR_NORMAL,
        'allowed_difference': 3
    },
    5: {  # 60-75%
        'allowed_difference': FINAL_PHASE_VOTE_DIFF,
        'step_delays': FINAL_PHASE_STEP_DELAYS,
        'update_delays': FINAL_PHASE_UPDATE_DELAYS,
        'behavior': BEHAVIOR_LEAD,
        'behavior_params': {
            'min_duration': 1,
            'max_duration': 3,
            'min_difference': 3,
            'max_difference': 6
        }
    },
    6: {  # 75-90%
        'allowed_difference': FINAL_PHASE_VOTE_DIFF,
        'step_delays': FINAL_PHASE_STEP_DELAYS,
        'update_delays': FINAL_PHASE_UPDATE_DELAYS,
        'behavior': BEHAVIOR_LEAD,
        'behavior_params': {
            'min_duration': 1,
            'max_duration': 3,
            'min_difference': 3,
            'max_difference': 8
        }
    },
    7: {  # 90-100%
        'allowed_difference': 0,
        'step_delays': FINAL_PHASE_STEP_DELAYS,
        'update_delays': FINAL_PHASE_UPDATE_DELAYS,
        'behavior': BEHAVIOR_LEAD,
        'behavior_params': {
            'min_duration': 1,
            'max_duration': 3,
            'min_difference': 7,
            'max_difference': 10
        }
    }
}
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
