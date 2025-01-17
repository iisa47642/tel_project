import asyncio

# Глобальная блокировка для управления баттлом
battle_lock = asyncio.Lock()
