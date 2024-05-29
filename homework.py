import logging
import os
import requests

from dotenv import load_dotenv
from telebot import TeleBot, types

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


def check_tokens():
    pass


def send_message(bot, message):
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(timestamp):
    response = requests.get(
        ENDPOINT, headers=HEADERS, params=timestamp
    )
    return response.json()


def check_response(response):
    for key, homework in response.items():
        if key == "homeworks" and homework == []:
            pass
        else:
            return homework


def parse_status(homework):
    last_work = homework[-1]
    for key, homework in last_work.items():
        if key == "approved" and homework == []:
            pass
        else:

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""

    ...

    # Создаем объект класса бота
    bot = TeleBot(token='TELEGRAM_TOKEN')
    timestamp = int(time.time())

    ...

    while True:
        try:

            ...

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            ...
        ...


if __name__ == '__main__':
    main()
