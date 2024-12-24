# database/database.py
import sqlite3

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('users.db')
        self.cur = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """Создание таблицы для хранения данных пользователей"""
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER,
            gender TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.conn.commit()

    def save_user_data(self, user_id: int, data: dict):
        """Сохранение данных пользователя"""
        self.cur.execute(
            "INSERT OR REPLACE INTO users (user_id, name, age, gender) VALUES (?, ?, ?, ?)",
            (user_id, data['name'], data['age'], data['gender'])
        )
        self.conn.commit()