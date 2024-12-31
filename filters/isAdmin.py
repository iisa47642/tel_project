from aiogram.types import Message
from database.db import select_all_admins

#ADMIN_ID = [842589261,1270990667]


# 842589261,1270990667

async def is_admin(message: Message) -> bool:
    ADMIN_ID = await select_all_admins()
    if ADMIN_ID:
        ADMIN_ID = [i[0] for i in ADMIN_ID]
        return message.from_user.id in ADMIN_ID
    else:
        return False
