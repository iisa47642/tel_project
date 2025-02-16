# user_bot.py
import logging
import time
from telethon import TelegramClient
import user_bot_conf as config
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import InputPeerChannel

class UserBot:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UserBot, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not UserBot._initialized:
            self.client = None
            self.account = config.ACCOUNT  # Получаем данные аккаунта из конфига
            self.requests_count = 0
            self.start_time = time.time()
            self.error_count = 0
            
            # Настройки производительности
            self.min_delay = 0.8
            self.max_requests_per_minute = 50
            self.max_requests_per_hour = 2000
            self.error_threshold = 5
            
            self.requests_history = []
            self.is_throttled = False
            
            # Настройка логгера
            self.logger = logging.getLogger(f"UserBot_{self.account['phone']}")
            UserBot._initialized = True

    async def start(self):
        if not self.client:
            try:
                self.client = TelegramClient(
                    f'sessions/{self.account["phone"]}',
                    self.account['api_id'],
                    self.account['api_hash']
                )
                await self.client.start()
                self.logger.info(f"UserBot initialized for {self.account['phone']}")
            except Exception as e:
                self.logger.error(f"Failed to start UserBot: {e}")
                self.client = None
                raise

    async def stop(self):
        if self.client:
            await self.client.disconnect()
            self.client = None
            self.logger.info("UserBot stopped")

    async def send_channel_message(self, channel_id, message, entities=None):
        if not self.client:
            await self.start()
            
        try:
            current_time = time.time()
            self.requests_history = [t for t in self.requests_history if current_time - t < 3600]
            
            if len(self.requests_history) >= self.max_requests_per_hour:
                self.logger.warning("Hourly request limit reached")
                raise Exception("Rate limit exceeded")
            
            # Добавляем текущий запрос
            self.requests_history.append(current_time)
            
            try:
                # Получаем entity канала
                channel_entity = await self.client.get_entity(int(channel_id))
                
                # Отправляем сообщение
                await self.client.send_message(
                    entity=channel_entity,
                    message=message,
                    formatting_entities=entities
                    )
                
                self.logger.info(f"Message sent to channel {channel_id}")
                return True
                
            except ValueError as e:
                self.logger.error(f"Could not find channel: {e}")
                raise
                
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Failed to send message: {e}")
            if self.error_count >= self.error_threshold:
                self.logger.error("Error threshold reached")
                self.is_throttled = True
            raise



user_bot = UserBot()
