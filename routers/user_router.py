from aiogram import F, Router, Bot
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, MessageOriginChannel, PhotoSize
from aiogram.utils.deep_linking import create_start_link, decode_payload
from database.db import *
from keyboards.user_keyboards import main_user_kb, vote_user_kb, support_user_kb
from keyboards.admin_keyboards import *


from filters.mode_filter import mode_filter
from states.user_states import FSMFillForm
from filters.isAdmin import is_admin
from keyboards import user_keyboards

_bot: Bot = None  # Placeholder for the bot instance

def setup_router(dp, bot: Bot):
    global _bot
    _bot = bot

user_router = Router()
#user_router.message.filter(lambda message: not is_admin(message))


# -----------
# хэндлеры для канала
@user_router.channel_post()
async def send_message(message: MessageOriginChannel):
    await _bot.send_message(chat_id=message.chat.id, text = 'Привет!')
# -----------
#-----------
# Команды для пользователей
@user_router.message(mode_filter(1),CommandStart() ,StateFilter(default_state))
async def cmd_start(message: Message,state: FSMContext,command: Command):
    # декод рефералки и добавление реферала в бд
    args = message.text.split()[1] if len(message.text.split()) > 1 else None
    if args:
            payload = decode_payload(args)
            referrer_id = int(payload)
            user_id = message.from_user.id
            await create_user(user_id, "user")
            if user_id != referrer_id:
                await edit_user(user_id, 'ref_owner', referrer_id)
    else:
        await create_user(message.from_user.id, "user")
    await message.reply("Привет! Отправь мне /battle для участия в баттле",reply_markup=main_user_kb)


@user_router.message(Command("battle"), StateFilter(default_state))
@user_router.message(F.text=="Принять участие",StateFilter(default_state))
async def cmd_battle(message: Message, state: FSMContext):
    user_id = message.from_user.id
    application = await select_application(user_id)
    if not application:
        await message.answer("Отправь мне свое фото для баттла.")
        await state.set_state(FSMFillForm.fill_photo)
    else:
        await message.answer("Вы уже зарегистрированы на баттл")



@user_router.message(StateFilter(FSMFillForm.fill_photo),
            F.photo[-1].as_('largest_photo'))
async def process_photo_sent(message: Message,
                             state: FSMContext,
                             largest_photo: PhotoSize):
    await state.update_data(
        photo_unique_id=largest_photo.file_unique_id,
        photo_id=largest_photo.file_id
    )
    data = await state.get_data()
    await message.answer(
        text='Спасибо!\n\nОжидайте сообщения о начале раунда'
    )
    await create_application(message.from_user.id, data["photo_id"])

    await state.clear()


@user_router.message(StateFilter(FSMFillForm.fill_photo))
async def warning_not_photo(message: Message):
    await message.answer(
        text='Пожалуйста, на этом шаге отправьте '
             'ваше фото\n\nЕсли вы хотите прервать '
             'заполнение анкеты - отправьте команду /cancel'
    )


@user_router.message(lambda message: message.text == "Поддержка", StateFilter(default_state))
async def support(message: Message, state: FSMContext):
    await message.answer(
        text=
        "Если у вас есть какие-либо вопросы, "+
        "не стесняйтесь и воспользуйтесь этими ссылками.",
        reply_markup=support_user_kb
    )

@user_router.message(lambda message: message.text == "Профиль", StateFilter(default_state))
async def profile(message: Message, state: FSMContext):
    
    user = await get_user(message.from_user.id)
    
    buttle_win = user[1]
    dual_win = user[2]
    plays_buttle = user[3]
    referals = user[4]
    additional_voices = user[5]
    
    await message.answer(
        text=
        f"ID: {message.from_user.id}\n"+
        f"Ник: @{message.from_user.username}\n"+
        f"Выйгранных фотобатлов: {buttle_win} \n"+
        f"Общее число фотобатлов: {plays_buttle} \n"+
        f"Выйгранных дуэлей: {dual_win}\n\n"+
        f"Дополнительные голоса: {additional_voices}\n"
        f"Приглашенных рефералов: {referals}"
    )
    
# хендлер для создания рефералок 
@user_router.message(lambda message: message.text == "Получить голоса", StateFilter(default_state))
async def mt_referal_menu (message: Message, state: FSMContext, bot: Bot):
    link = await create_start_link(bot,str(message.from_user.id), encode=True)
    await message.answer(
        text=f"Ваша реферальная ссылка {link}"
    )



@user_router.message()
async def echo(message: Message):
    await message.answer(f"Вы сказали: {message.text}")



