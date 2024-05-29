import logging
import os
import time
from logging.handlers import RotatingFileHandler

import requests
from dotenv import load_dotenv
from telebot import TeleBot

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TEST_TOKEN')
TELEGRAM_TOKEN = os.getenv('MY_TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('MY_TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

status_homework = None

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'my_logger.log', maxBytes=50000000, backupCount=5, encoding='utf-8',
)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    missing_tokens = []
    if not PRACTICUM_TOKEN:
        missing_tokens.append('PRACTICUM_TEST_TOKEN')
    if not TELEGRAM_TOKEN:
        missing_tokens.append('MY_TELEGRAM_TOKEN')
    if not TELEGRAM_CHAT_ID:
        missing_tokens.append('MY_TELEGRAM_CHAT_ID')
    if missing_tokens:
        logger.critical(
            f'Отсутствуют переменные окружения: {", ".join(missing_tokens)}')
        return False

    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram-чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Сообщение "{message}" успешно отправлено в Telegram.')
    except Exception as e:
        logger.error(f'Ошибка при отправке сообщения в Telegram: {e}')


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса."""

    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=timestamp
        )
        response.raise_for_status()
        response_json = response.json()

        if response_json.get('error', {}).get('need_cookie_update'):
            logger.error(
                'Недоступность эндпоинта: требуется обновление cookie.'
            )

        return response_json

    except requests.exceptions.RequestException as e:
        logger.error(f'Сбой при запросе к эндпоинту: {e}')
        return None

    except Exception as e:
        logger.error(f'Неизвестная ошибка: {e}')
        return None


def check_response(response):
    """Проверяет ответ API."""
    for key, homework in response.items():
        if key == "homeworks" and homework == []:
            return None
        else:
            return homework

        # if not isinstance(response, dict):
        #     raise TypeError('Ответ API не является словарем.')
        # if 'homeworks' not in response:
        #     raise KeyError('Ключ "homeworks" отсутствует в ответе API.')
        # if not isinstance(response['homeworks'], list):
        #     raise TypeError('Тип данных по ключу "homeworks" не является списком.')
        # return response['homeworks']


def parse_status(homework):
    """Извлекает статус домашней работы."""
    if not homework:
        logger.debug('Нет новых статусов домашних работ.')
        return None

    homework_name = homework.get('homework_name', 'Неизвестная работа')
    status = homework.get('status')

    if status not in HOMEWORK_VERDICTS:
        error_message = f'Обнаружен неожиданный статус: {status}'
        logger.error(error_message)
        return None

    global status_homework
    if status_homework == status:
        logger.debug('Статус домашней работы не изменился.')
        return None

    status_homework = status
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют необходимые переменные окружения.')
        return

    bot = TeleBot(TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            if response:
                homeworks = check_response(response)
                if homeworks:
                    for homework in homeworks:
                        message = parse_status(homework)
                        if message:
                            send_message(bot, message)
            time.sleep(RETRY_PERIOD)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, f'Сбой в работе программы: {error}')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
