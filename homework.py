import logging
import os
import sys
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

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(
    'my_logger.log', maxBytes=50000000, backupCount=5, encoding='utf-8',
)
stream_handler = logging.StreamHandler(sys.stdout)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

logger.debug('Конфигурация журналирования настроена правильно.')


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(tokens)


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
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )
        if response.status_code != 200:
            error_message = (
                f'Эндпоинт {ENDPOINT} недоступен. '
                f'Код ответа: {response.status_code}'
            )
            logger.error(error_message)
            raise APIException(error_message)

        return response.json()
    except requests.RequestException as e:
        error_message = f'Сбой при запросе к эндпоинту: {e}'
        logger.error(error_message)
        raise APIException(error_message)


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        error_message = 'Ответ API не является словарем.'
        logger.error(error_message)
        raise TypeError(error_message)
    if 'homeworks' not in response:
        error_message = 'Ключ "homeworks" отсутствует в ответе API.'
        logger.error(error_message)
        raise KeyError(error_message)
    if not isinstance(response['homeworks'], list):
        error_message = 'Тип данных по ключу "homeworks" не является списком.'
        logger.error(error_message)
        raise TypeError(error_message)
    return response['homeworks']


def parse_status(homework):
    """Извлекает статус домашней работы."""
    if 'homework_name' not in homework:
        error_message = 'В ответе API отсутствует ключ `homework_name`.'
        logger.error(error_message)
        raise KeyError(error_message)
    if 'status' not in homework:
        error_message = 'В ответе API отсутствует ключ `status`.'
        logger.error(error_message)
        raise KeyError(error_message)

    homework_name = homework.get('homework_name')
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
        error_message = (
            'Отсутствуют необходимые переменные окружения. '
            'Программа принудительно остановлена.'
        )
        logger.critical(error_message)
        sys.exit(error_message)

    bot = TeleBot(TELEGRAM_TOKEN)
    timestamp = int(time.time())

    last_message = None

    # # код для отладки бота:
    # current_unix_time = int(time.time())
    # timestamp = current_unix_time - 30 * 24 * 60 * 60

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
                    send_message(bot, message)

                    # if message:
                    #     send_message(bot, message)
                    # else:
                    #     logger.error(
                    #         'Ошибка при извлечении статуса домашней работы.'
                    #     )
            # обновление метки времени
            timestamp = response.get('current_date', timestamp)

        except Exception as error:
            message = f'Неизвестный сбой: {error}'
            logger.error(message)
            if message != last_message:
                send_message(bot, message)
                last_message = message

        finally:
            time.sleep(RETRY_PERIOD)
            logger.debug('Программа завершила работу.')


if __name__ == '__main__':
    main()
