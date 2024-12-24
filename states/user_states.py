# states/user_states.py
from aiogram.fsm.state import State, StatesGroup

class UserForm(StatesGroup):
    """Состояния для формы регистрации пользователя"""
    name = State()        # Состояние ожидания ввода имени
    age = State()         # Состояние ожидания ввода возраста
    gender = State()      # Состояние ожидания ввода пола
    confirm = State()     # Состояние подтверждения данных