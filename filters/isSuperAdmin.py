import os

from config.config import load_config

dirname = os.path.dirname(__file__)
filename = os.path.abspath(os.path.join(dirname, '..', 'config/config.env'))
config = load_config(filename)
SUPER_ADMIN_IDS = config.tg_bot.super_admin_ids


def is_super_admin(user):
    return user in SUPER_ADMIN_IDS