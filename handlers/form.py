# handlers/form.py
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from states.user_states import UserForm
from keyboards.form_kb import gender_kb, confirm_kb

# Создаем роутер для формы
form_router = Router()


@form_router.message(Command("register"))
async def cmd_register(message: Message, state: FSMContext):
    """
    Начало регистрации
    """
    await message.answer(
        "Давайте начнем регистрацию!\n"
        "Как вас зовут?",
        reply_markup=ReplyKeyboardRemove()
    )
    # Устанавливаем состояние ожидания ввода имени
    await state.set_state(UserForm.name)


@form_router.message(StateFilter(UserForm.name))
async def process_name(message: Message, state: FSMContext):
    """
    Обработка ввода имени
    """
    # Сохраняем имя в данные состояния
    await state.update_data(name=message.text)

    await message.answer(
        "Отлично! Теперь введите ваш возраст (полных лет):"
    )
    # Переходим к следующему состоянию
    await state.set_state(UserForm.age)


@form_router.message(StateFilter(UserForm.age))
async def process_age(message: Message, state: FSMContext):
    """
    Обработка ввода возраста
    """
    # Проверяем корректность введенного возраста
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число!")
        return

    age = int(message.text)
    if age < 12 or age > 100:
        await message.answer("Возраст должен быть от 12 до 100 лет!")
        return

    await state.update_data(age=age)

    await message.answer(
        "Выберите ваш пол:",
        reply_markup=gender_kb
    )
    await state.set_state(UserForm.gender)


@form_router.message(StateFilter(UserForm.gender))
async def process_gender(message: Message, state: FSMContext):
    """
    Обработка выбора пола
    """
    if message.text not in ["Мужской", "Женский"]:
        await message.answer("Пожалуйста, используйте клавиатуру!")
        return

    await state.update_data(gender=message.text)

    # Получаем все сохраненные данные
    data = await state.get_data()

    # Формируем текст для подтверждения
    confirm_text = (
        "Пожалуйста, проверьте введенные данные:\n"
        f"Имя: {data['name']}\n"
        f"Возраст: {data['age']}\n"
        f"Пол: {data['gender']}\n\n"
        "Все верно?"
    )

    await message.answer(
        confirm_text,
        reply_markup=confirm_kb
    )
    await state.set_state(UserForm.confirm)


@form_router.message(StateFilter(UserForm.confirm))
async def process_confirm(message: Message, state: FSMContext):
    """
    Обработка подтверждения данных
    """
    if message.text == "Подтвердить":
        # Получаем финальные данные
        data = await state.get_data()

        # Здесь можно сохранить данные в БД

        await message.answer(
            "Спасибо за регистрацию!",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await message.answer(
            "Регистрация отменена. Для начала новой используйте /register",
            reply_markup=ReplyKeyboardRemove()
        )

    # Очищаем состояние
    await state.clear()


# Общий обработчик отмены для всех состояний
@form_router.message(F.text == "Отмена", StateFilter("*"))
async def cancel_handler(message: Message, state: FSMContext):
    """
    Отмена процесса регистрации из любого состояния
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer(
        "Действие отменено. Для новой регистрации используйте /register",
        reply_markup=ReplyKeyboardRemove()
    )