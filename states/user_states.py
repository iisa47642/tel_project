# states/user_states.py
from aiogram.fsm.state import State, StatesGroup

class FSMFillForm(StatesGroup):
    fill_photo = State()