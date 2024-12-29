from dataclasses import dataclass
from environs import Env
from typing import List

# @dataclass
# class DbConfig:
#     """Конфигурация базы данных"""
#     database: str         # Название базы данных
#     db_host: str         # Хост базы данных
#     db_user: str         # Пользователь базы данных
#     db_password: str     # Пароль от базы данных
#     db_port: int         # Порт базы данных

@dataclass
class TgBot:
    """Конфигурация бота"""
    token: str           # Токен для доступа к телеграм-боту
    super_admin_ids: List[int] # Список id администраторов бота
    channel_id: int
#    use_redis: bool      # Использовать Redis

@dataclass
class Config:
    """Общий класс конфигурации"""
    tg_bot: TgBot
    # db: DbConfig
    # misc: Miscellaneous

def load_config(path: str = None) -> Config:
    """Загрузка конфигурации из переменных окружения или .env файла"""
    env = Env()
    env.read_env(path)

    return Config(
        tg_bot=TgBot(
            token=env.str("BOT_TOKEN"),
            super_admin_ids=list(map(int, env.list("SUPER_ADMIN_IDS"))),
            channel_id=int(env.str("CHANNEL_ID")),
            #use_redis=env.bool("USE_REDIS")
        ),
        # db=DbConfig(
        #     database=env.str('DB_NAME'),
        #     db_host=env.str('DB_HOST'),
        #     db_user=env.str('DB_USER'),
        #     db_password=env.str('DB_PASSWORD'),
        #     db_port=env.int('DB_PORT')
        # ),
        # misc=Miscellaneous(
        #     other_params=env.str('OTHER_PARAMS')
        # )
    )

# Простой вариант без dataclass
"""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = str(os.getenv("BOT_TOKEN"))
ADMINS = list(map(int, os.getenv("ADMINS").split(',')))

DB_NAME = str(os.getenv("DB_NAME"))
DB_HOST = str(os.getenv("DB_HOST"))
DB_USER = str(os.getenv("DB_USER"))
DB_PASSWORD = str(os.getenv("DB_PASSWORD"))
DB_PORT = int(os.getenv("DB_PORT"))

REDIS_HOST = str(os.getenv("REDIS_HOST", "localhost"))
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

PAY_TOKEN = str(os.getenv("PAY_TOKEN"))
"""

# Пример .env файла:
"""
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMINS=123456789,987654321
USE_REDIS=False

DB_NAME=bot_db
DB_HOST=localhost
DB_USER=postgres
DB_PASSWORD=password
DB_PORT=5432

REDIS_HOST=localhost
REDIS_PORT=6379

OTHER_PARAMS=some_value
"""

# Использование:
"""
from config import load_config

config = load_config(".env")

# Доступ к параметрам:
bot_token = config.tg_bot.token
admin_ids = config.tg_bot.admin_ids
database = config.db.database
"""