# database/database.py
import aiosqlite as sq


# -------------------- Функция для создания таблиц
async def create_tables():
    async with sq.connect("bot_database.db") as db:
        # Создание таблицы пользователей
        await db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            buttle_win INTEGER,
            dual_win INTEGER,
            plays_buttle INTEGER,
            referals INTEGER,
            additional_voices INTEGER,
            role TEXT,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ref_owner INTEGER,
            is_ban INTEGER
        )
        ''')

        # Создание таблицы батла
        await db.execute('''
        CREATE TABLE IF NOT EXISTS application (
            user_id INTEGER PRIMARY KEY,
            photo_id TEXT
        )
        ''')
        
        await db.execute('''
        CREATE TABLE IF NOT EXISTS battle (
            user_id INTEGER PRIMARY KEY,
            photo_id TEXT,
            is_participant,
            points INTEGER,
            role TEXT,
            is_kick INTEGER
        )
        ''')
        
        await db.execute('''
        CREATE TABLE IF NOT EXISTS admin_photo (
            photo_id TEXT PRIMARY KEY
        )
        ''')
        
        await db.execute('''
        CREATE TABLE IF NOT EXISTS battle_settings (
            round_duration INTEGER,
            prize_amount INTEGER,
            min_vote_total INTEGER,
            round_interval INTEGER,
            time_of_run INTEGER,
            is_autowin INTEGER 
        )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS channel_messages (
                message_id INTEGER PRIMARY KEY
            )
        ''')

        await db.execute('''
            CREATE TABLE IF NOT EXISTS admin_autowin_const (
                mark INTEGER PRIMARY KEY,
                message_id INTEGER,
                admin_id INTEGER,
                admin_position TEXT,
                user_id INTEGER
            )
        ''')

        await db.commit()
        print("База данных успешно создана!")



async def create_user(user_id, role):
    async with sq.connect("bot_database.db") as db:
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                await cursor.execute("INSERT INTO users VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (user_id,0,0,0,0,0,role,0,0,0))
                await db.commit()
    
    
    
    
async def edit_user(user_id: int, parameter: str, value):
    allowed_parameters = ['user_id','buttle_win','dual_win',
                          'plays_buttle' ,'referals','additional_voices',
                          'registration_date','role','ref_owner','is_ban']
    
    if parameter in allowed_parameters:
        async with sq.connect("bot_database.db") as db:
        # Проверяем, существует ли пользователь
            async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
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
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            existing_user = await cursor.fetchone()
            
            if existing_user:
            
            # Удаляем пользователя
                await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
                await db.commit()


# -------------------- запросы к таблице текущего баттла

# посм
async def create_user_in_batl(user_id, photo_id, role):
     async with sq.connect("bot_database.db") as db:
        async with db.execute(f"SELECT 1 FROM battle WHERE user_id == '{user_id}'") as cursor:
            user = await cursor.fetchone()
            if not user:
                await cursor.execute("INSERT INTO battle VALUES(?, ?, ?, ?, ?, ?)", (user_id,photo_id,1,0,role,0))
                await db.commit()
    
    
async def edite_photo_in_batl(user_id):
    async with sq.connect("bot_database.db") as db:
        # Проверяем, существует ли пользователь
            async with db.execute("SELECT user_id FROM battle WHERE user_id = ?", (user_id,)) as cursor:
                existing_user = await cursor.fetchone()
                if existing_user:
                    # Формируем SQL-запрос динамически
                    query = f"UPDATE battle SET photo_id = ? WHERE user_id = ?"
                    await db.execute(query, (user_id,))
                    await db.commit()
                
async def kick_user_battle(user_id):
    async with sq.connect("bot_database.db") as db:
        # Проверяем, существует ли пользователь
            async with db.execute("SELECT user_id FROM battle WHERE user_id = ?", (user_id,)) as cursor:
                existing_user = await cursor.fetchone()
                if existing_user:
                    # Формируем SQL-запрос динамически
                    query = f"UPDATE battle SET is_kick = 1 WHERE user_id = ?"
                    await db.execute(query, (user_id,))
                    await db.commit()
    

async def delete_user_in_batl(user_id):
    async with sq.connect("bot_database.db") as db:
        # Проверяем, существует ли пользователь
        async with db.execute("SELECT user_id FROM battle WHERE user_id = ?", (user_id,)) as cursor:
            existing_user = await cursor.fetchone()
            
            if existing_user:
            
            # Удаляем пользователя
                await db.execute("DELETE FROM battle WHERE user_id = ?", (user_id,))
                await db.commit()
         
async def delete_users_in_batl():
    async with sq.connect("bot_database.db") as db:
        # Проверяем, существует ли пользователь
            
            # Удаляем пользователей
        await db.execute("DELETE FROM battle", )
        await db.commit()
         
# ---------------- запросы к таблице заявок на текущий батл
async def create_application(user_id, photo_id):
    async with sq.connect("bot_database.db") as db:
        async with db.execute(f"SELECT 1 FROM application WHERE user_id == '{user_id}'") as cursor:
            user = await cursor.fetchone()
            if not user:
                await cursor.execute("INSERT INTO application VALUES(?, ?)", (user_id,photo_id))
                await db.commit()


async def edite_application(user_id):
    async with sq.connect("bot_database.db") as db:
        # Проверяем, существует ли пользователь
            async with db.execute("SELECT user_id FROM application WHERE user_id = ?", (user_id,)) as cursor:
                existing_user = await cursor.fetchone()
                
                if existing_user:
                    # Формируем SQL-запрос динамически
                    query = f"UPDATE application SET photo_id = ? WHERE user_id = ?"
                    
                    await db.execute(query, (user_id,))
                    await db.commit()


async def delete_application(user_id: int):
    async with sq.connect("bot_database.db") as db:
        # Проверяем, существует ли пользователь
        async with db.execute("SELECT user_id FROM application WHERE user_id = ?", (user_id,)) as cursor:
            existing_user = await cursor.fetchone()
            
            if existing_user:
            
            # Удаляем пользователя
                await db.execute("DELETE FROM application WHERE user_id = ?", (user_id,))
                await db.commit()


async def delete_applications():
    async with sq.connect("bot_database.db") as db:
        # Проверяем, существует ли пользователь
            
            # Удаляем пользователей
        await db.execute("DELETE FROM application", )
        await db.commit()
        
# изменение настроек
async def edit_battle_settings(parameter: str, value):
    allowed_parameters = ['round_duration','prize_amount',
            'min_vote_total','round_interval', 'time_of_run','is_autowin']
    
    if parameter in allowed_parameters:
        async with sq.connect("bot_database.db") as db:
                    # Формируем SQL-запрос динамически
                async with db.execute("SELECT * FROM battle_settings") as cursor:
                    existing = await cursor.fetchall()
                    if not existing:
                        await db.execute("INSERT INTO battle_settings VALUES(?, ?, ?, ?, ?, ?)", (7200,1000,5,1800,50400, 1))
                        await db.commit()
                            
                    query = f"UPDATE battle_settings SET {parameter} = ?"
                    await db.execute(query, (value,))
                    await db.commit()
                        
# messages

async def save_message_ids(message_ids: list):
    async with sq.connect("bot_database.db") as db:
        await db.executemany("INSERT INTO channel_messages (message_id) VALUES (?)", 
                             [(msg_id,) for msg_id in message_ids])
        await db.commit()

async def get_message_ids():
    async with sq.connect("bot_database.db") as db:
        cursor = await db.execute("SELECT message_id FROM channel_messages")
        return [row[0] for row in await cursor.fetchall()]

async def clear_message_ids():
    async with sq.connect("bot_database.db") as db:
        await db.execute("DELETE FROM channel_messages")
        await db.commit()



# -------------- Selects

# возвращает все данные пользователя по id

async def get_user(user_id: int):
    async with sq.connect("bot_database.db") as db:
        async with db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)) as cursor:
            existing_user = await cursor.fetchone()
            if existing_user:
                return existing_user
            return False
            

async def get_all_users():
    async with sq.connect("bot_database.db") as db:
        async with db.execute('SELECT * FROM users') as cursor:
            return await cursor.fetchall()

# -----------------
# возвращает список заявок

async def select_all_applications():
    async with sq.connect("bot_database.db") as db:
        async with db.execute('SELECT * FROM application') as cursor:
            return await cursor.fetchall()
        
        
# возвращает конкретную заявку
async def select_application(user_id: int):
    async with sq.connect("bot_database.db") as db:
        async with db.execute('SELECT * FROM application WHERE user_id = ?', (user_id,)) as cursor:
            existing_user = await cursor.fetchone()
            if existing_user:
                return existing_user
            return False
        
        
# возвращает всех участников баттла
async def select_all_battle():
    async with sq.connect("bot_database.db") as db:
        async with db.execute('SELECT * FROM battle') as cursor:
            return await cursor.fetchall()

#returns max numbers of votes, that aren't admin's
async def select_max_number_of_users_voices(admin_id):
    async with sq.connect("bot_database.db") as db:
        async with db.execute('SELECT max(points) FROM battle where user_id<>?', (admin_id,)) as cursor:
            return await cursor.fetchone()


# возвращает одного участника баттла   
async def select_user_on_battle(user_id):
    async with sq.connect("bot_database.db") as db:
        async with db.execute('SELECT * FROM battle WHERE user_id = ?', (user_id,)) as cursor:
            existing_user = await cursor.fetchone()
            if existing_user:
                return existing_user
            return False
        
# настройки баттла
async def select_battle_settings():
    async with sq.connect("bot_database.db") as db:
        async with db.execute('SELECT * FROM battle_settings') as cursor:
            flag = await cursor.fetchall()
            if not flag:
                await db.execute("INSERT INTO battle_settings VALUES(?, ?, ?, ?, ?, ?)", (7200,1000,5,1800,50400,1))
                await db.commit()
                # Делаем новый SELECT после вставки
                async with db.execute('SELECT * FROM battle_settings') as new_cursor:
                    return (await new_cursor.fetchall())[0]
            return flag[0]
# -------- для баттла

async def set_user_as_participant(user_id: int):
    async with sq.connect("bot_database.db") as db:
        await db.execute("UPDATE battle SET is_participant = 1 WHERE user_id = ?", (user_id,))
        await db.commit()
# 
async def get_participants():
    async with sq.connect("bot_database.db") as db:
        cursor = await db.execute("SELECT user_id, photo_id FROM battle WHERE is_participant = 1")
        participants = await cursor.fetchall()
        return [{'user_id': p[0], 'photo_id': p[1]} for p in participants]
# 
async def update_points(user_id: int):
    async with sq.connect("bot_database.db") as db:
        await db.execute("UPDATE battle SET points = points + 1 WHERE user_id = ?", (user_id,))
        await db.commit()
# 
async def get_round_results(min_votes_for_single: int):
    async with sq.connect("bot_database.db") as db:
        cursor = await db.execute("SELECT * FROM battle WHERE is_participant = 1")
        participants = await cursor.fetchall()
        
        results = []
        for i in range(0, len(participants), 2):
            if i + 1 < len(participants):
                results.append([
                    {'user_id': participants[i][0], 'votes': participants[i][3], 'is_kick': participants[i][5]},
                    {'user_id': participants[i+1][0], 'votes': participants[i+1][3], 'is_kick': participants[i+1][5]}
                ])
            else:
                results.append([
                    {'user_id': participants[i][0], 'votes': participants[i][3], 'is_kick': participants[i][5]}
                ])
        
        return results
# 

async def remove_losers(losers: list):
    print(losers)
    async with sq.connect("bot_database.db") as db:
        cursor = await db.cursor()
        for user_id in losers:
            await cursor.execute("DELETE FROM battle WHERE user_id = ?", (user_id,))
        await db.commit()


async def delete_users_points():
    async with sq.connect("bot_database.db") as db:
        await db.execute("UPDATE battle SET points = 0")
        await db.commit()

#admin_autowin_const

async def edit_admin_autowin_const(parameter: str, value):
    allowed_parameters = ['message_id', 'admin_id', 'admin_position',
                          'user_id']
    if parameter in allowed_parameters:
        async with sq.connect("bot_database.db") as db:
            async with db.execute("SELECT * FROM admin_autowin_const") as cursor:
                existing = await cursor.fetchall()
                if not existing:
                    await db.execute("INSERT INTO admin_autowin_const VALUES(?, ?, ?, ?, ?)",
                                     (1, 0, 0, '0', 0))
                    await db.commit()
                query = f"UPDATE admin_autowin_const SET {parameter} = ? WHERE mark=1"
                await db.execute(query, (value,))
                await db.commit()

async def insert_admin_autowin_const(parameter: str, value):
    allowed_parameters = ['message_id', 'admin_id', 'admin_position',
                          'user_id']
    if parameter in allowed_parameters:
        async with sq.connect("bot_database.db") as db:
            query = f"INSERT INTO admin_autowin_const ({parameter}) VALUES (?) "
            await db.execute(query, (value,))
            await db.commit()

async def select_admin_autowin_const(parameter: str):
    allowed_parameters = ['message_id', 'admin_id', 'admin_position',
                          'user_id']
    if parameter in allowed_parameters:
        async with sq.connect("bot_database.db") as db:
            async with db.execute(f" SELECT {parameter} FROM admin_autowin_const where mark=1") as cursor:
                return await cursor.fetchone()

async def select_user_from_battle(user_id):
    async with sq.connect("bot_database.db") as db:
        async with db.execute('SELECT * FROM battle WHERE user_id = ?', (user_id,)) as cursor:
            existing_user = await cursor.fetchone()
            if existing_user:
                return existing_user
            return False

async def select_admin_photo():
    async with sq.connect("bot_database.db") as db:
        async with db.execute('SELECT max(photo_id) FROM admin_photo') as cursor:
            photo_id = await cursor.fetchone()
            await delete_admin_photo(photo_id[0])
            return photo_id

async def delete_admin_photo(photo_id):
    async with sq.connect("bot_database.db") as db:
        query = f"DELETE FROM admin_photo WHERE photo_id = ?"
        await db.execute(query, (photo_id,))
        await db.commit()


# async def select_admins()