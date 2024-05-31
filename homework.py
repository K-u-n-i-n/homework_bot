import logging
import os
import time
from logging.handlers import RotatingFileHandler

import requests
from dotenv import load_dotenv
from telebot import TeleBot

from exceptions import APIException


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
last_message = None

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

logger.debug('Конфигурация журналирования настроена правильно.')


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
        response = requests.get(ENDPOINT, headers=HEADERS, params={
                                'from_date': timestamp})
        if response.status_code != 200:
            error_message = (
                f'Эндпоинт {ENDPOINT} недоступен. '
                f'Код ответа: {response.status_code}'
            )
            logger.error(error_message)
            raise APIException(error_message)

        return response.json()
    except requests.RequestException as e:
        logger.error(f'Сбой при запросе к эндпоинту: {e}')
        raise APIException(f'Сбой при запросе к эндпоинту: {e}')


def log_and_notify_error(error_message):
    """Логирует и отправляет сообщение об ошибке в Telegram."""
    global last_message
    logger.error(error_message)
    # if last_message != error_message:
    send_message(error_message)
    last_message = error_message


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        error_message = 'Ответ API не является словарем.'
        log_and_notify_error(error_message)
        raise TypeError(error_message)
    if 'homeworks' not in response:
        error_message = 'Ключ "homeworks" отсутствует в ответе API.'
        log_and_notify_error(error_message)
        raise KeyError(error_message)
    if not isinstance(response['homeworks'], list):
        error_message = 'Тип данных по ключу "homeworks" не является списком.'
        log_and_notify_error(error_message)
        raise TypeError(error_message)
    return response['homeworks']


def parse_status(homework):
    """Извлекает статус домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError('В ответе API отсутствует ключ `homework_name`.')
    if 'status' not in homework:
        raise KeyError('В ответе API отсутствует ключ `status`.')

    homework_name = homework.get('homework_name', 'Неизвестная работа')
    status = homework.get('status')

    if status not in HOMEWORK_VERDICTS:
        error_message = f'Обнаружен неожиданный статус: {status}'
        logger.error(error_message)
        raise ValueError(error_message)

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
        logger.critical(
            'Отсутствуют необходимые переменные окружения. '
            'Программа принудительно остановлена.'
        )
        return

    bot = TeleBot(TELEGRAM_TOKEN)
    timestamp = int(time.time())

    global last_message

    while True:
        logger.debug('Запуск цикла.')
        try:
            response = get_api_answer(timestamp)
            if response:
                homeworks = check_response(response)
                if not homeworks:
                    logger.debug('Нет новых статусов домашних работ.')
                for homework in homeworks:
                    message = parse_status(homework)
                    if message:
                        send_message(bot, message)
            # обновление метки времени
            timestamp = response.get('current_date', timestamp)
            time.sleep(RETRY_PERIOD)

        except Exception as error:
            message = f'Неизвестный сбой: {error}'
            logger.error(message)
            if message != last_message:
                send_message(bot, message)
                last_message = message
            time.sleep(RETRY_PERIOD)

        finally:
            logger.debug('Программа завершила работу.')


if __name__ == '__main__':
    main()
