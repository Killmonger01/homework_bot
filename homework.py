from http import HTTPStatus

import os
import telegram
import logging
import time
import requests
from dotenv import load_dotenv


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
ENDPOINT = os.getenv('ENDPOINT')

RETRY_PERIOD = 600
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


class TheAnswerIsNot200Error(Exception):
    """Ответ сервера не равен 200."""


def check_tokens():
    """Проверяем наличие токенов."""
    if all([PRACTICUM_TOKEN is None,
            TELEGRAM_TOKEN is None,
            TELEGRAM_CHAT_ID is None]):
        logging.critical('Нет важной константы!')
        return False
    else:
        return True


def send_message(bot, message):
    """Отправка сообщения в Телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(
            f'начали отправку сообщения в Telegram: {message}')
    except telegram.TelegramError as telegram_error:
        logging.error(f'сообщение не отправилось {telegram_error}')


def get_api_answer(timestamp):
    """Получение данных с API Яндекса."""
    try:
        api = requests.get(ENDPOINT, headers=HEADERS, params=timestamp)
        if api.status_code != HTTPStatus.OK:
            logging.error('API не равен 200')
            raise TheAnswerIsNot200Error
        ((f'код ответа {api.status_code}'))
        return requests.get(ENDPOINT, headers=HEADERS, params=timestamp).json()
    except requests.exceptions.RequestException as request_error:
        logging.error(f'Код ответа API {request_error}')


def check_response(response):
    """Проверяем данные у response."""
    if not isinstance(response, dict):
        logging.error('API ответ это не словарь')
        raise TypeError('response это не словарь')
    if 'homeworks' and 'current_date' not in response:
        logging.error('ключа homeworks нет в response')
        raise KeyError('ключа homeworks нет в response')
    if not isinstance(response.get('homeworks'), list):
        logging.error('ключа homeworks нет в response')
        raise TypeError('ключа homeworks нет в response')
    return response.get('homeworks')[0]


def parse_status(homework):
    """Сообщение в телеграмм."""
    if 'status' and 'homework_name' not in homework:
        logging.error(
            'Ошибка пустое значение status или homework_name')
        raise KeyError('нет ключа status или homework_name')
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        logging.error(
            'status не в HOMEWORK_VERDICTS')
        raise ValueError('status не в HOMEWORK_VERDICTS')
    verdict = HOMEWORK_VERDICTS.get(status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        SystemExit.exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    tmp_status = 'reviewing'
    while True:
        try:
            check_tokens()
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework and tmp_status != homework['status']:
                message = parse_status(homework)
                send_message(bot, message)
                tmp_status = homework['status']
                time.sleep(RETRY_PERIOD)
            logging.info(
                'Изменений нет, ждем 10 минут и проверяем API')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logging.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(format=('%(asctime)s - %(name)s'
                                '- %(levelname)s - %(message)s'),
                        level=logging.INFO,
                        filename='main.log')
    main()
