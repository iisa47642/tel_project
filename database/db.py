# database/database.py
import random
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
            is_kick INTEGER,
            is_single INTEGER,
            position INTEGER
        )
        ''')
        
        await db.execute('''
        CREATE TABLE IF NOT EXISTS admin_photo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            photo_id TEXT
        )
        ''')
        
        await db.execute('''
        CREATE TABLE IF NOT EXISTS battle_settings (
            round_duration INTEGER,
            prize_amount TEXT,
            min_vote_total INTEGER,
            round_interval INTEGER,
            time_of_run INTEGER,
            is_autowin INTEGER,
            info_message TEXT
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
       
        await db.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                link TEXT NOT NULL
            )
        ''')
        
        await db.execute('''
        CREATE TABLE IF NOT EXISTS buffer_battle (
            user_id INTEGER PRIMARY KEY,
            photo_id TEXT,
            is_participant,
            points INTEGER,
            role TEXT,
            is_kick INTEGER,
            is_single INTEGER
        )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                message TEXT NOT NULL,
                time TEXT NOT NULL
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


async def edit_user_role(user_id: int, value):
    async with sq.connect("bot_database.db") as db:
        # Проверяем, существует ли пользователь
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            existing_user = await cursor.fetchone()

            if existing_user:
                # Формируем SQL-запрос динамически
                query = f"UPDATE users SET role = ? WHERE user_id = ?"
                await db.execute(query, (value, user_id))
                await db.commit()
                return True
            else:
                return False

async def select_all_admins():
    async with sq.connect("bot_database.db") as db:
        async with db.execute('SELECT * FROM users WHERE role=?',('admin',)) as cursor:
            return await cursor.fetchall()

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
                # Находим максимальное значение position
                async with db.execute("SELECT COALESCE(MAX(position), 0) FROM battle") as cursor:
                    max_position = (await cursor.fetchone())[0]
                
                # Добавляем пользователя с position = max_position + 1
                await db.execute(
                    "INSERT INTO battle (user_id, photo_id, is_participant, points, role, is_kick, is_single, position) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", 
                    (user_id, photo_id, 1, 0, role, 0, 0, max_position + 1)
                )
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
            'min_vote_total','round_interval', 'time_of_run','is_autowin', 'info_message']
    
    if parameter in allowed_parameters:
        async with sq.connect("bot_database.db") as db:
                    # Формируем SQL-запрос динамически
                async with db.execute("SELECT * FROM battle_settings") as cursor:
                    existing = await cursor.fetchall()
                    if not existing:
                        await db.execute("INSERT INTO battle_settings VALUES(?, ?, ?, ?, ?, ?, ?)", (7200,1000,5,1800,50400, 1,None))
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
                await db.execute("INSERT INTO battle_settings VALUES(?, ?, ?, ?, ?, ?,?)", (7200,1000,5,1800,50400,1,None))
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
        cursor = await db.execute("""
            SELECT user_id, photo_id, points 
            FROM battle 
            WHERE is_participant = 1 
            ORDER BY position ASC
        """)
        participants = await cursor.fetchall()
        return [{'user_id': p[0], 'photo_id': p[1], 'points': p[2]} for p in participants]

# 
async def update_points(user_id: int):
    async with sq.connect("bot_database.db") as db:
        await db.execute("UPDATE battle SET points = points + 1 WHERE user_id = ?", (user_id,))
        await db.commit()
# 
# async def get_round_results(min_votes_for_single: int):
#     async with sq.connect("bot_database.db") as db:
#         cursor = await db.execute("SELECT * FROM battle WHERE is_participant = 1")
#         participants = await cursor.fetchall()
        
#         results = []
#         for i in range(0, len(participants), 2):
#             if i + 1 < len(participants):
#                 results.append([
#                     {'user_id': participants[i][0], 'votes': participants[i][3], 'is_kick': participants[i][5]},
#                     {'user_id': participants[i+1][0], 'votes': participants[i+1][3], 'is_kick': participants[i+1][5]}
#                 ])
#             else:
#                 results.append([
#                     {'user_id': participants[i][0], 'votes': participants[i][3], 'is_kick': participants[i][5]}
#                 ])
        
#         return results
# 

async def get_round_results(min_votes_for_single: int):
    """
    Формирует результаты текущего раунда, гарантируя, что одиночные участники остаются одиночными.
    """
    async with sq.connect("bot_database.db") as db:
        # Получаем всех участников, сортируем сначала по is_single (по убыванию), затем по position (по возрастанию)
        cursor = await db.execute("""
            SELECT * FROM battle 
            WHERE is_participant = 1 
            ORDER BY is_single DESC, position ASC
        """)
        participants = await cursor.fetchall()

        # Разделяем участников на одиночных и обычных
        single_participants = []  # Участники с is_single=1
        paired_participants = []  # Участники с is_single=0

        for participant in participants:
            user = {
                'user_id': participant[0],
                'votes': participant[3],
                'is_kick': participant[5],
                'is_single': participant[6],
            }
            if user['is_single'] == 1:
                single_participants.append(user)
            else:
                paired_participants.append(user)

        results = []

        # Формируем пары из обычных участников
        for i in range(0, len(paired_participants), 2):
            if i + 1 < len(paired_participants):
                # Добавляем пару
                results.append([
                    paired_participants[i],
                    paired_participants[i + 1]
                ])
            else:
                # Если остался один участник без пары, добавляем его отдельно
                results.append([paired_participants[i]])

        # Добавляем одиночных участников в конец результатов
        for single in single_participants:
            results.append([single])

        return results



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

# async def select_admin_photo():
#     async with sq.connect("bot_database.db") as db:
#         async with db.execute('SELECT id,max(photo_id) FROM admin_photo') as cursor:
#             photo_id = await cursor.fetchone()
#             await delete_admin_photo(photo_id[0],photo_id[1])
#             return photo_id

async def select_admin_photo():
    async with sq.connect("bot_database.db") as db:
        # Получаем запись с минимальным id
        async with db.execute('SELECT id, photo_id FROM admin_photo ORDER BY id ASC LIMIT 1') as cursor:
            photo = await cursor.fetchone()

            # Если запись найдена, удаляем её
            if photo:
                await delete_admin_photo(photo[0])  # Удаляем по id
                return photo[1]  # Возвращаем photo_id
            return None  # Если таблица пуста


async def delete_admin_photo(id: int):
    async with sq.connect("bot_database.db") as db:
        await db.execute("DELETE FROM admin_photo WHERE id = ?", (id,))
        await db.commit()



# async def select_admins()
# ------ обновление статистики

async def users_plays_buttle_update():
    async with sq.connect("bot_database.db") as db:
        async with db.execute("SELECT user_id FROM battle") as cursor:
            existing_users = await cursor.fetchall()
            if existing_users:
                await db.execute("UPDATE users SET plays_buttle = plays_buttle + 1")
                await db.commit()

async def users_buttle_win_update(user_id):
    async with sq.connect("bot_database.db") as db:
        async with db.execute("SELECT user_id FROM battle WHERE user_id = ?", (user_id,)) as cursor:
            existing_user = await cursor.fetchone()
            if existing_user:
                await db.execute("UPDATE users SET buttle_win = buttle_win + 1 WHERE user_id = ?", (user_id,))
                await db.commit()


async def users_dual_win_update(user_id):
    async with sq.connect("bot_database.db") as db:
        async with db.execute("SELECT user_id FROM battle WHERE user_id = ?", (user_id,)) as cursor:
            existing_user = await cursor.fetchone()
            if existing_user:
                await db.execute("UPDATE users SET dual_win = dual_win + 1 WHERE user_id = ?", (user_id,))
                await db.commit()
                

async def get_current_votes(user_id):
    async with sq.connect("bot_database.db") as db:
        async with db.execute("SELECT user_id FROM battle WHERE user_id = ?", (user_id,)) as cursor:
            existing_user = await cursor.fetchone()
            if existing_user:
                async with db.execute("SELECT points FROM battle WHERE user_id = ?", (user_id,)) as points_cursor:
                    result = await points_cursor.fetchone()
                    return result[0] if result else 0  # Возвращаем число из кортежа или 0, если результат пустой
            return 0  # Возвращаем 0, если пользователь не найден

            
            
async def update_admin_battle_points():
    async with sq.connect("bot_database.db") as db:
        async with db.execute("SELECT user_id FROM battle WHERE user_id = ?", (0,)) as cursor:
            existing_user = await cursor.fetchone()
            if existing_user:
                await db.execute("UPDATE battle SET points = 100000 WHERE user_id = ?", (0,))
                await db.commit()




async def get_channels_from_db():
    async with sq.connect("bot_database.db") as db:
        query = "SELECT name, link FROM channels"
        cursor = await db.execute(query)
        rows = await cursor.fetchall()
        await cursor.close()
        
        # Преобразуем результат в список словарей
        channels = [{"name": row[0], "link": row[1]} for row in rows]
        return channels


async def add_channel_to_db(name: str, link: str):
    async with sq.connect("bot_database.db") as db:
        query = "INSERT INTO channels (name, link) VALUES (?, ?)"
        await db.execute(query, (name, link))
        await db.commit()



async def delete_channel_from_db(name: str):
    async with sq.connect("bot_database.db") as db:
        query = "DELETE FROM channels WHERE name = ?"
        cursor = await db.execute(query, (name,))
        await db.commit()
        return cursor.rowcount > 0  # True, если канал был удален

async def clear_users_in_batl():
    async with sq.connect("bot_database.db") as db:
        await db.execute("DELETE FROM battle WHERE user_id != 0")
        await db.commit()

async def select_participants_no_id_null():
    async with sq.connect("bot_database.db") as db:
        cursor = await db.execute("SELECT user_id, photo_id, points FROM battle WHERE is_participant = 1 AND user_id != 0")
        participants = await cursor.fetchall()
        return [{'user_id': p[0], 'photo_id': p[1]} for p in participants]


async def delete_users_add_voices():
    async with sq.connect("bot_database.db") as db:
        await db.execute("UPDATE users SET additional_voices = 0")
        await db.commit()
        
        
        
async def update_info_message(message_txt):
    async with sq.connect("bot_database.db") as db:
            await db.execute('UPDATE battle_settings SET info_message = ?', (message_txt,))
            await db.commit()


async def delete_info_message():
    async with sq.connect("bot_database.db") as db:
            await db.execute('UPDATE battle_settings SET info_message = NULL')
            await db.commit()
            
            
async def select_info_message():
    async with sq.connect("bot_database.db") as db:
            cursor = await db.execute('SELECT info_message FROM battle_settings')
            result = await cursor.fetchone()
            return result
        
        
# Добавление нескольких фотографий в базу данных
async def add_photos(photo_ids: list[str]):
    async with sq.connect("bot_database.db") as db:
        await db.executemany(
            "INSERT INTO admin_photo (photo_id) VALUES (?)",
            [(photo_id,) for photo_id in photo_ids]
        )
        await db.commit()




# Выбор последней фотографии из базы данных
async def get_first_photo():
    async with sq.connect("bot_database.db") as db:
        # Получаем запись с минимальным id
        async with db.execute("SELECT photo_id FROM admin_photo ORDER BY id ASC LIMIT 1") as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None  # Возвращаем photo_id или None, если таблица пуста


# Удаление последней фотографии из базы данных
async def delete_last_photo():
    async with sq.connect("bot_database.db") as db:
        # Получаем ID последней фотографии
        async with db.execute("SELECT id FROM admin_photo ORDER BY id DESC LIMIT 1") as cursor:
            last_photo = await cursor.fetchone()

        if last_photo:
            # Удаляем последнюю фотографию
            await db.execute("DELETE FROM admin_photo WHERE id = ?", (last_photo[0],))
            await db.commit()
            return True
        return False


# Подсчет количества фотографий в базе данных
# async def count_photos():
#     async with sq.connect("bot_database.db") as db:
#         async with db.execute("SELECT COUNT(*) FROM admin_photo") as cursor:
#             result = await cursor.fetchone()
#             return result[0]


# Функции для работы с БД
async def save_admin_photo(photo_id: str):
    async with sq.connect("bot_database.db") as db:
        await db.execute('INSERT INTO admin_photo (photo_id) VALUES (?)', (photo_id,))
        await db.commit()
        
async def save_admin_photo_two(valid_photos):
    async with sq.connect("bot_database.db") as db:
        for photo_id in valid_photos:
            await db.execute('INSERT INTO admin_photo (photo_id) VALUES (?)', (photo_id,))
        await db.commit()



async def create_user_in_buffer(user_id, photo_id, role):
     async with sq.connect("bot_database.db") as db:
        async with db.execute(f"SELECT 1 FROM buffer_battle WHERE user_id == '{user_id}'") as cursor:
            user = await cursor.fetchone()
            if not user:
                await cursor.execute("INSERT INTO buffer_battle VALUES(?, ?, ?, ?, ?, ?, ?)", (user_id,photo_id,1,0,role,0,0))
                await db.commit()
                
                
                
async def get_users_in_buffer():
    async with sq.connect("bot_database.db") as db:
        cursor = await db.execute("SELECT user_id, photo_id, points FROM buffer_battle WHERE is_participant = 1")
        participants = await cursor.fetchall()
        return [{'user_id': p[0], 'photo_id': p[1]} for p in participants]
    
    
async def delete_users_in_buffer():
    async with sq.connect("bot_database.db") as db:
        # Проверяем, существует ли пользователь
            
            # Удаляем пользователей
        await db.execute("DELETE FROM buffer_battle", )
        await db.commit()
        
        
async def set_single_user(user_id: int):
    async with sq.connect("bot_database.db") as db:
        await db.execute("UPDATE battle SET is_single = 1 WHERE user_id = ?", (user_id,))
        await db.commit()
        
        
async def delete_users_single():
    async with sq.connect("bot_database.db") as db:
        await db.execute("UPDATE battle SET is_single = 0")
        await db.commit()
        
        
async def swap_user_position():
    async with sq.connect("bot_database.db") as db:
        # Получаем все позиции, кроме последней
        cursor = await db.execute("SELECT position FROM battle ORDER BY position ASC")
        positions = [row[0] for row in await cursor.fetchall()]

        if len(positions) < 2:
            print("Not enough participants to swap positions.")
            return

        # Исключаем последнюю позицию
        available_positions = positions[:-1]

        # Выбираем случайную позицию
        random_position = random.choice(available_positions)

        # Получаем текущую позицию пользователя с user_id = 0
        cursor = await db.execute("SELECT position FROM battle WHERE user_id = 0")
        user_position = await cursor.fetchone()
        if not user_position:
            print("User with user_id = 0 not found.")
            return
        user_position = user_position[0]

        # Находим пользователя, который занимает случайную позицию
        cursor = await db.execute("SELECT user_id FROM battle WHERE position = ?", (random_position,))
        other_user = await cursor.fetchone()
        if not other_user:
            print(f"No user found at position {random_position}.")
            return
        other_user_id = other_user[0]

        # Обновляем позиции
        await db.execute(
            "UPDATE battle SET position = ? WHERE user_id = 0",
            (random_position,)
        )
        await db.execute(
            "UPDATE battle SET position = ? WHERE user_id = ?",
            (user_position, other_user_id)
        )

        # Сохраняем изменения
        await db.commit()
        print(f"User with user_id = 0 swapped position with user_id = {other_user_id}.")
        
        

async def swap_user_position_first():
    async with sq.connect("bot_database.db") as db:
        cursor = await db.execute("SELECT position FROM battle WHERE user_id = 0")
        user_position = await cursor.fetchone()
        if not user_position:
            print("User with user_id = 0 not found.")
            return
        await db.execute("UPDATE battle SET position = 1 WHERE user_id = 0")
        await db.commit()
        
        
async def update_admin_photo_in_battle(photo_id):
    async with sq.connect('bot_database.db') as db:
        # Проверяем существование записи
        cursor = await db.execute('SELECT 1 FROM battle WHERE user_id = 0')
        exists = await cursor.fetchone()
        
        if exists:
            # Если запись существует, обновляем photo_id
            await db.execute('''
                UPDATE battle 
                SET photo_id = ? 
                WHERE user_id = 0
            ''', (photo_id,))
            await db.commit()
            return True
        return False



async def add_notification(code: str, message: str, notification_time: str):
    async with sq.connect('bot_database.db') as db:
        await db.execute(
            'INSERT INTO notifications (code, message, time) VALUES (?, ?, ?)',
            (code, message, notification_time)
        )
        await db.commit()

async def get_all_notifications():
    async with sq.connect('bot_database.db') as db:
        async with db.execute('SELECT * FROM notifications') as cursor:
            return await cursor.fetchall()

async def delete_notification(code: str):
    async with sq.connect('bot_database.db') as db:
        await db.execute('DELETE FROM notifications WHERE code = ?', (code,))
        await db.commit()

async def get_notification_by_code(code: str):
    async with sq.connect('bot_database.db') as db:
        async with db.execute(
            'SELECT * FROM notifications WHERE code = ?', 
            (code,)
        ) as cursor:
            return await cursor.fetchone()

async def check_notification_code_exists(code: str) -> bool:
    async with sq.connect('bot_database.db') as db:
        async with db.execute(
            'SELECT 1 FROM notifications WHERE code = ?', 
            (code,)
        ) as cursor:
            return bool(await cursor.fetchone())