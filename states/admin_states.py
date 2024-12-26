from aiogram.fsm.state import State, StatesGroup

class FSMFillForm(StatesGroup):
    fill_duration_of_battle = State()
    fill_amount_of_prize = State()
    fill_minimal_number_of_votes = State()
    fill_interval_between_battles = State()
    fill_id_of_new_admin = State()
    fill_id_of_old_admin = State()
