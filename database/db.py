# database/database.py
import sqlite3 as sq
from dataclasses import dataclass 

# -------------------- Функция для создания таблиц
async def create_tables():
    global db, cursor
    db = sq.connect("bot_database.db")
    cursor = db.cursor()    
    # Создание таблицы пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        buttle_win INTEGER,
        dual_win INTEGER,
        plays_buttle INTEGER,
        referals INTEGER,
        additional_voices INTEGER,
        role TEXT,
        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Создание таблицы батла
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS application (
        user_id INTEGER PRIMARY KEY,
        photo_id TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS battle (
        user_id INTEGER PRIMARY KEY,
        photo_id TEXT,
        points INTEGER,
        role TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin_photo (
        photo_id INTEGER PRIMARY KEY
    )
    ''')

    db.commit()
    db.close()
    print("База данных успешно создана!")



async def create_user(user_id, role):
    user = cursor.execute(f"SELECT 1 FROM users WHERE user_id == '{user_id}'").fetchone()
    if not user:
        cursor.execute("INSERT INTO users VALUES(?, ?, ?, ?, ?, ?, ?, ?)", (user_id,0,0,0,0,0,role,0))
        db.commit()
    
    
    
    
async def edit_user(user_id: int, parameter: str, value):
    allowed_parameters = ['user_id','buttle_win','dual_win',
                          'plays_buttle' ,'referals','additional_voices',
                          'registration_date']
    
    if parameter in allowed_parameters:
        async with sq.connect("bot_database.db") as db:
        # Проверяем, существует ли пользователь
            cursor = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            existing_user = await cursor.fetchone()
            
            if existing_user:
                # Формируем SQL-запрос динамически
                query = f"UPDATE users SET {parameter} = ? WHERE user_id = ?"
                
                await db.execute(query, (value, user_id))
                await db.commit()



async def delete_user(user_id: int):
    """
    Удаляет пользователя из базы данных.

    :param user_id: ID пользователя для удаления
    """
    async with sq.connect("bot_database.db") as db:
        # Проверяем, существует ли пользователь
        cursor = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        existing_user = await cursor.fetchone()
        
        if existing_user:
        
        # Удаляем пользователя
            await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            await db.commit()


# -------------------- запросы к таблице текущего баттла
async def create_user_in_batl(user_id, photo_id, role):
    user = cursor.execute(f"SELECT 1 FROM battle WHERE user_id == '{user_id}'").fetchone()
    if not user:
        cursor.execute("INSERT INTO battle VALUES(?, ?, ?, ?)", (user_id,photo_id,0,role))
        db.commit()
    
    
async def edite_photo_in_batl(user_id):
    async with sq.connect("bot_database.db") as db:
        # Проверяем, существует ли пользователь
            cursor = await db.execute("SELECT user_id FROM battle WHERE user_id = ?", (user_id,))
            existing_user = await cursor.fetchone()
            
            if existing_user:
                # Формируем SQL-запрос динамически
                query = f"UPDATE battle SET photo_id = ? WHERE user_id = ?"
                
                await db.execute(query, (user_id,))
                await db.commit()
                
                
async def delete_user_in_batl(user_id):
    async with sq.connect("bot_database.db") as db:
        # Проверяем, существует ли пользователь
        cursor = await db.execute("SELECT user_id FROM battle WHERE user_id = ?", (user_id,))
        existing_user = await cursor.fetchone()
        
        if existing_user:
        
        # Удаляем пользователя
            await db.execute("DELETE FROM battle WHERE user_id = ?", (user_id,))
            await db.commit()
         
         
# ---------------- запросы к таблице заявок на текущий батл
async def create_application(user_id, photo_id):
    user = cursor.execute(f"SELECT 1 FROM application WHERE user_id == '{user_id}'").fetchone()
    if not user:
        cursor.execute("INSERT INTO application VALUES(?, ?)", (user_id,photo_id))
        db.commit()


async def edite_application(user_id):
    async with sq.connect("bot_database.db") as db:
        # Проверяем, существует ли пользователь
            cursor = await db.execute("SELECT user_id FROM application WHERE user_id = ?", (user_id,))
            existing_user = await cursor.fetchone()
            
            if existing_user:
                # Формируем SQL-запрос динамически
                query = f"UPDATE application SET photo_id = ? WHERE user_id = ?"
                
                await db.execute(query, (user_id,))
                await db.commit()


async def delete_application(user_id):
    async with sq.connect("bot_database.db") as db:
        # Проверяем, существует ли пользователь
        cursor = await db.execute("SELECT user_id FROM application WHERE user_id = ?", (user_id,))
        existing_user = await cursor.fetchone()
        
        if existing_user:
        
        # Удаляем пользователя
            await db.execute("DELETE FROM application WHERE user_id = ?", (user_id,))
            await db.commit()

# -------------- Selects