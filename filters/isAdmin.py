import os

from aiogram.types import Message

from config.config import load_config
from database.db import select_all_admins

#ADMIN_ID = [842589261,1270990667]

dirname = os.path.dirname(__file__)
filename = os.path.abspath(os.path.join(dirname, '..', 'config/config.env'))
config = load_config(filename)
SUPER_ADMIN_IDS = config.tg_bot.super_admin_ids


# 842589261,1270990667

async def is_admin(message: Message) -> bool:
    if message.from_user.id in SUPER_ADMIN_IDS:
        return True
    ADMIN_ID = await select_all_admins()
    if ADMIN_ID:
        ADMIN_ID = [i[0] for i in ADMIN_ID]
        return message.from_user.id in ADMIN_ID
    else:
        return False
