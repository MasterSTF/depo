from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
import requests

app = Flask(__name__)

# Замените <TOKEN> на токен вашего бота Telegram
TOKEN = '6123526807:AAEYYUx4czpb1cmrf_szddd1S96lNf_wVb8'

# Замените <API_URL> на фактический URL вашего API для отправки данных
API_URL = 'https://sheet.best/api/sheets/dc3418d7-4986-4fee-aba6-b7824fb84ce6'

# Замените <GET_URL> на фактический URL для GET-запроса
GET_URL = 'https://sheet.best/api/sheets/dc3418d7-4986-4fee-aba6-b7824fb84ce6'

# Состояния разговора
STATE_SUBMIT = 1
STATE_VIEW = 2
STATE_WAITING = 3

# Обработчик команды /start
def start(update: Update, context):
    buttons = [['/submit', '/view'], ['/cancel']]  # Добавляем кнопку /cancel
    reply_markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True)
    update.message.reply_text('Привет! Я чат-бот. Выберите одну из команд:', reply_markup=reply_markup)

# Функция для получения значения первого столбца
def get_last_number():
    # Отправляем GET-запрос для получения данных
    get_response = requests.get(GET_URL)

    if get_response.status_code == 200:
        data = get_response.json()
        # Получаем последнее значение в первом столбце
        last_row = data[-1] if data else {}
        last_number = last_row.get('Номер', 0)
        return int(last_number) + 1
    else:
        print('Ошибка при получении данных')
        return None

# Обработчик команды /submit
def submit_data(update: Update, context):
    user = update.message.from_user

    context.user_data['submit_data'] = {}  # Инициализируем словарь для хранения ответов пользователя

    # Задаем первый вопрос
    update.message.reply_text('Введите марку авто:')
    context.user_data['current_question'] = 'Марка'
    return STATE_SUBMIT

# Функция для обработки ввода данных после команды /submit
def handle_submit(update: Update, context):
    user = update.message.from_user
    message = update.message.text

    # Проверяем, была ли команда отмены
    if message.lower() == '/cancel':
        return cancel(update, context)

    # Получаем текущий вопрос и ответы пользователя
    current_question = context.user_data.get('current_question')
    submit_data = context.user_data.get('submit_data')

    # Проверяем наличие словаря submit_data
    if submit_data is None:
        update.message.reply_text('Пожалуйста, начните процесс заполнения данных командой /submit.')
        return ConversationHandler.END

    # Сохраняем ответ пользователя
    submit_data[current_question] = message

    # Задаем следующий вопрос или завершаем разговор
    if current_question == 'Марка':
        update.message.reply_text('Введите город:')
        context.user_data['current_question'] = 'Город'
    elif current_question == 'Город':
        update.message.reply_text('Введите телефон:')
        context.user_data['current_question'] = 'Телефон'
    elif current_question == 'Телефон':
        update.message.reply_text('Введите время:')
        context.user_data['current_question'] = 'Время'
    elif current_question == 'Время':
        update.message.reply_text('Введите комментарий:')
        context.user_data['current_question'] = 'Коммент'
    elif current_question == 'Коммент':
        # Получаем значение первого столбца
        Номер = get_last_number()
        if Номер is None:
            update.message.reply_text('Ошибка при получении данных')
            return STATE_SUBMIT

        # Отправляем POST-запрос с данными и присвоенным значением первого столбца
        response = requests.post(API_URL, json={
            'Номер': Номер,
            'Марка': submit_data['Марка'],
            'Город': submit_data['Город'],
            'Телефон': submit_data['Телефон'],
            'Время': submit_data['Время'],
            'Коммент': submit_data['Коммент'],
            'Статус': 'Новый'
        })

        if response.status_code == 200:
            data = response.json()
            message = f'Данные отправлены!\nНомер: {Номер}\nМарка: {submit_data["Марка"]}\nГород: {submit_data["Город"]}\nТелефон: {submit_data["Телефон"]}\nВремя: {submit_data["Время"]}\nКоммент: {submit_data["Коммент"]}'
            update.message.reply_text(message)
        else:
            update.message.reply_text('Ошибка.')

        # Завершаем разговор
        del context.user_data['submit_data']
        del context.user_data['current_question']
        return ConversationHandler.END

    return STATE_SUBMIT

# Функция для обработки ввода номера строки после команды /view
def handle_view(update: Update, context):
    user = update.message.from_user
    message = update.message.text

    # Проверяем, была ли команда отмены
    if message.lower() == '/cancel':
        return cancel(update, context)

    try:
        row_number = int(message)
    except ValueError:
        update.message.reply_text('Пожалуйста, введите корректный номер строки.')
        return STATE_VIEW

    # Отправляем GET-запрос для получения данных
    get_response = requests.get(GET_URL)

    if get_response.status_code == 200:
        data = get_response.json()
        if 0 <= row_number - 1 < len(data):
            row_data = data[row_number - 1]
            message = f'\n'
            for key, value in row_data.items():
                message += f'{key}: {value}\n'
            update.message.reply_text(message)
        else:
            update.message.reply_text('Указанная строка не найдена.')
    else:
        update.message.reply_text('Ошибка при получении данных.')

    return ConversationHandler.END

# Функция для обработки неизвестных команд
def unknown_command(update: Update, context):
    update.message.reply_text('Неизвестная команда. Пожалуйста, выберите команду с помощью кнопок.')

# Функция для отмены и возврата в главное меню
def cancel(update: Update, context):
    user = update.effective_user
    buttons = [['/submit', '/view'], ['/cancel']]  # Добавляем кнопку /cancel
    reply_markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True)
    update.message.reply_text('Отменено. Возврат в главное меню.', reply_markup=reply_markup)

    # Удаляем данные пользователя
    if 'submit_data' in context.user_data:
        del context.user_data['submit_data']
    if 'current_question' in context.user_data:
        del context.user_data['current_question']

    return start(update, context)


def main():
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Создаем ConversationHandler для обработки состояний разговора
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('submit', submit_data), CommandHandler('view', handle_view)],
        states={
            STATE_SUBMIT: [MessageHandler(Filters.text, handle_submit)],
            STATE_VIEW: [MessageHandler(Filters.text, handle_view)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Регистрируем обработчики команд и сообщений
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(MessageHandler(Filters.command, unknown_command))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
