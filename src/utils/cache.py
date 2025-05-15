# Импорт необходимых библиотек
import sqlite3      # Работа с SQLite базой данных
import threading   # Потокобезопасность
import os          # Работа с окружением и путями
from pathlib import Path  # Удобная работа с путями

class ChatCache:
    """
    Класс для кэширования истории чата в SQLite базе данных.
    Поддерживает:
    - Потокобезопасное соединение для каждого потока
    - Android-специфичный путь к базе
    - Формирование и очистку истории
    """
    def __init__(self):
        # Определяем путь к файлу БД
        self.db_path = self._get_db_path()
        # Thread-local для хранения соединения на поток
        self.local = threading.local()
        # Создаем таблицы
        self.create_tables()

    def _get_db_path(self) -> str:
        """
        Возвращает абсолютный путь к файлу базы данных.
        На Android сохраняет в Android/data/<package>/files,
        иначе — в папке cache рядом с проектом.
        """
        # Проверка Android окружения
        if hasattr(os, 'Android'):  # альтернативно: hasattr(sys, 'getandroidapilevel')
            pkg = os.environ.get('ANDROID_APP_PACKAGE', 'com.example.mychatapp')
            ext = os.environ.get('EXTERNAL_STORAGE', '/storage/emulated/0')
            db_dir = Path(ext) / 'Android' / 'data' / pkg / 'files'
        else:
            # десктопная среда
            project_root = Path(__file__).resolve().parent.parent
            db_dir = project_root / 'cache'
        db_dir.mkdir(parents=True, exist_ok=True)
        return str(db_dir / 'chat_cache.db')

    def get_connection(self) -> sqlite3.Connection:
        """
        Возвращает sqlite3.Connection для текущего потока.
        Создает соединение при первом запросе.
        """
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        return self.local.conn

    def create_tables(self) -> None:
        """
        Создание необходимых таблиц в базе данных.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT,
                user_message TEXT,
                ai_response TEXT,
                timestamp TEXT,
                tokens_used INTEGER
            )
            '''
        )
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS analytics_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                model TEXT,
                message_length INTEGER,
                response_time REAL,
                tokens_used INTEGER
            )
            '''
        )
        conn.commit()
        conn.close()

    def save_message(self, model: str, user_message: str, ai_response: str, tokens_used: int) -> None:
        """
        Сохраняет сообщение в таблицу messages.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO messages (model, user_message, ai_response, timestamp, tokens_used)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
            ''', (model, user_message, ai_response, tokens_used)
        )
        conn.commit()

    def get_chat_history(self, limit: int = 50):
        """
        Возвращает последние `limit` сообщений (новые первыми).
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM messages ORDER BY timestamp DESC LIMIT ?', (limit,)
        )
        return cursor.fetchall()

    def save_analytics(self, timestamp: str, model: str, message_length: int, response_time: float, tokens_used: int) -> None:
        """
        Сохраняет запись аналитики.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO analytics_messages (timestamp, model, message_length, response_time, tokens_used)
            VALUES (?, ?, ?, ?, ?)
            ''', (timestamp, model, message_length, response_time, tokens_used)
        )
        conn.commit()

    def get_analytics_history(self):
        """
        Возвращает всю историю аналитики.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT timestamp, model, message_length, response_time, tokens_used
            FROM analytics_messages ORDER BY timestamp ASC
            '''
        )
        return cursor.fetchall()

    def clear_history(self) -> None:
        """
        Очищает всю историю сообщений.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM messages')
        conn.commit()

    def __del__(self):
        """
        Закрывает соединение при уничтожении объекта.
        """
        if hasattr(self.local, 'conn'):
            self.local.conn.close()