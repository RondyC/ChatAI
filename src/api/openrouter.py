import requests
import os
from utils.logger import AppLogger

# Дефолтные параметры (вместо .env)
DEFAULT_API_KEY    = 'your-api-key-here'
DEFAULT_BASE_URL   = 'https://openrouter.ai/api/v1'
DEFAULT_DEBUG      = False
DEFAULT_LOG_LEVEL  = 'INFO'
DEFAULT_MAX_TOKENS = 1000
DEFAULT_TEMPERATURE= 0.7

class OpenRouterClient:
    """
    Клиент для взаимодействия с OpenRouter API.
    """

    def __init__(self):
        """
        Инициализация клиента OpenRouter.
        """
        self.logger = AppLogger()

        # Получаем переменные из окружения, если они есть, или используем дефолтные значения
        self.api_key     = os.getenv("OPENROUTER_API_KEY", DEFAULT_API_KEY)
        self.base_url    = os.getenv("BASE_URL", DEFAULT_BASE_URL)
        self.debug       = os.getenv("DEBUG", str(DEFAULT_DEBUG)).lower() in ("1", "true", "yes")
        self.log_level   = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL)
        self.max_tokens  = int(os.getenv("MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))
        self.temperature = float(os.getenv("TEMPERATURE", str(DEFAULT_TEMPERATURE)))

        # Проверка наличия API ключа
        if not self.api_key:
            self.logger.error("OpenRouter API key not found in environment or defaults")
            raise ValueError("OpenRouter API key not found")

        # Заголовки для запросов
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        # Логирование параметров
        self.logger.info(f"OpenRouterClient initialized (debug={self.debug}, "
                         f"max_tokens={self.max_tokens}, temperature={self.temperature})")

        # Доступные модели
        self.available_models = self.get_models()

    def get_models(self):
        """
        Получение списка доступных моделей.
        """
        self.logger.debug("Fetching available models")
        try:
            resp = requests.get(f"{self.base_url}/models", headers=self.headers)
            resp.raise_for_status()
            data = resp.json().get('data', [])
            models = [{'id': m['id'], 'name': m['name']} for m in data]
            self.logger.info(f"Retrieved {len(models)} models")
            return models
        except Exception as e:
            self.logger.error(f"Error fetching models: {e}", exc_info=True)
            return [
                {'id': 'deepseek-coder', 'name': 'DeepSeek'},
                {'id': 'claude-3-sonnet', 'name': 'Claude 3.5 Sonnet'},
                {'id': 'gpt-3.5-turbo', 'name': 'GPT-3.5 Turbo'}
            ]

    def send_message(self, message: str, model: str):
        self.logger.debug(f"Sending message to {model} (max_tokens={self.max_tokens}, "
                          f"temperature={self.temperature})")
        payload = {
            'model': model,
            'messages': [{'role': 'user', 'content': message}],
            'max_tokens': self.max_tokens,
            'temperature': self.temperature
        }
        try:
            resp = requests.post(f"{self.base_url}/chat/completions", headers=self.headers, json=payload)
            resp.raise_for_status()
            self.logger.info("Received response from API")
            return resp.json()
        except Exception as e:
            self.logger.error(f"API request failed: {e}", exc_info=True)
            return {'error': str(e)}

    def get_balance(self):
        try:
            resp = requests.get(f"{self.base_url}/credits", headers=self.headers)
            resp.raise_for_status()
            data = resp.json().get('data', {})
            balance = data.get('total_credits', 0) - data.get('total_usage', 0)
            return f"${balance:.2f}"
        except Exception as e:
            self.logger.error(f"Balance request failed: {e}", exc_info=True)
            return 'Ошибка'
