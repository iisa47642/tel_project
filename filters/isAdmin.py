from aiogram.types import Message

ADMIN_ID = [842589261]
# 842589261,1270990667

def is_admin(message: Message) -> bool:
    return message.from_user.id in ADMIN_ID
