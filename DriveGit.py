import os
import tempfile
import pickle
import re
import cachetools
import json
import redis
from io import BytesIO
from telegram import InputMediaPhoto
from telegram import ReplyKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

TELEGRAM_API_TOKEN = '6072271437:AAHcFO46gQAF2yEouLhHZIChaqDNYPW0wSc'
SCOPES = ['https://www.googleapis.com/auth/drive']

REDIS_URL = os.environ.get('REDISCLOUD_URL')
cache = redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)

def get_google_drive_service():
    token_json = os.environ.get('TOKEN_JSON', None)
    if token_json:
        creds = Credentials.from_authorized_user_info(info=json.loads(token_json))
    else:
        # Your original code to load the token.pickle
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_console()
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

    try:
        service = build('drive', 'v3', credentials=creds)
        return service
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None
    
def get_table_content_from_google_sheets(sheets_service, spreadsheet_id):
    range_name = 'A2:B'
    result = sheets_service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    rows = result.get('values', [])
    return rows

def find_file(drive_service, file_name, folder_id=None):
    query = f"mimeType='application/vnd.google-apps.spreadsheet' and trashed = false and name='{file_name}'"
    if folder_id:
        query += f" and '{folder_id}' in parents"
    results = drive_service.files().list(q=query).execute()
    items = results.get('files', [])

    if not items:
        return None
    return items[0]['id']

def get_google_sheets_service():
    creds = None
    token_json = os.environ.get('TOKEN_JSON', None)
    if token_json:
        creds = Credentials.from_authorized_user_info(info=json.loads(token_json))
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_console()

    try:
        service = build('sheets', 'v4', credentials=creds)
        return service
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def create_subjects_keyboard():
    keyboard = [
        ["Алгебра", "Англійська мова", "Біологія", "Всесвітня історія"],
        ["Географія", "Геометрія", "Громадянська освіта", "Зарубіжна література"],
        ["Захист України", "Інформатика", "Історія України", "Польська мова"],
        ["Мистецство", "Українська література", "Українська мова", "Фізика"],
        ["Фізкультура", "Фінансова грамотність", "Хімія"],
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def create_tasks_keyboard(subject):
    if subject == "Алгебра":
        keyboard = [
            ["3", "9", "14", "16", "18"],
            ["22", "24", "28", "34", "36"],
            ["38", "40", "43", "47", "50"],
            ["Предмети"],
        ]
    elif subject == "Англійська мова":
        keyboard = [
            ["3", "8", "12", "17", "23"],
            ["25", "27", "29", "31", "36"],
            ["40", "41", "42", "43", "51"],
            ["54", "59", "63", "66", "71", "76"],
            ["Предмети"],
        ]
    elif subject == "Біологія":
        keyboard = [
            ["6", "13", "15", "21"],
            ["27", "34", "45"],
            ["Предмети"],
        ]
    elif subject == "Всесвітня історія":
        keyboard = [
            ["5", "10", "13"],
            ["16", "19", "27"],
            ["32", "35", "38"],
            ["Предмети"],
        ]
    elif subject == "Географія":
        keyboard = [
            ["7", "8", "13"],
            ["16", "18", "27"],
            ["28", "32", "34"],
            ["39", "41", "45"],
            ["Предмети"],
        ]
    elif subject == "Геометрія":
        keyboard = [
            ["3", "11", "15"],
            ["16", "18", "21"],
            ["24", "28", "34"],
            ["39", "41", "42"],
            ["44", "50"],
            ["Предмети"],
        ]
    elif subject == "Громадська освіта":
        keyboard = [
            ["7", "8", "16"],
            ["17", "35", "36"],
            ["44", "45", "57"],
            ["58", "64"],
            ["Предмети"],
        ]
    elif subject == "Зарубіжна література":
        keyboard = [
            ["3", "6", "8"],
            ["10", "18", "20"],
            ["22", "28", "30"],
            ["Предмети"],
        ]
    elif subject == "Захист України":
        keyboard = [
            ["14", "27", "31"],
            ["36"],
            ["Предмети"],
        ]
    elif subject == "Інформатика":
        keyboard = [
            ["5", "10", "19"],
            ["24", "49", "51"],
            ["56", "61", "66"],
            ["68"],
            ["Предмети"],
        ]
    elif subject == "Історія України":
        keyboard = [
            ["4", "7", "11"],
            ["15", "20", "31", "36"],
            ["40", "44", "47", "50"],
            ["Предмети"],
        ]
    elif subject == "Мистецтво":
        keyboard = [
            ["8", "65"],
            ["Предмети"],
        ]
    elif subject == "Польська мова":
        keyboard = [
            ["50", "56", "60"],
            ["Предмети"],
        ]
    elif subject == "Українська література":
        keyboard = [
            ["6", "12", "17", "18"],
            ["34", "39", "41", "43", "48"],
            ["Предмети"],
        ]
    elif subject == "Українська мова":
        keyboard = [
            ["3", "10", "17",],
            ["18", "20", "31", "53"],
            ["58", "65", "70", "75"],
            ["Предмети"],
        ]
    elif subject == "Фізика":
        keyboard = [
            ["4", "12", "22", "27", "33"],
            ["36", "41", "48", "53", "55"],
            ["56", "62", "72", "74"],
            ["Предмети"],
        ]
    elif subject == "Фізкультура":
        keyboard = [
            ["6", "11", "17", "21", "27"],
            ["Предмети"],
        ]
    elif subject == "Фінансова грамотність":
        keyboard = [
            ["49", "53", "63", "67", "71"],
            ["Предмети"],
        ]
    elif subject == "Хімія":
        keyboard = [
            ["4", "9", "15"],
            ["20", "31", "32"],
            ["Предмети"],
        ]
    else:
        return None

    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def create_return_keyboard():
    keyboard = [["Знайти іншу відповідь"]]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

def find_images(drive_service, subject, task_number, folder_id=None):
    query = f"mimeType='image/png' and trashed = false and name contains '{subject} {task_number}'"
    if folder_id:
        query += f" and '{folder_id}' in parents"
    results = drive_service.files().list(q=query).execute()
    items = results.get('files', [])
    return items

def get_or_cache_data(subject, task_number, data_type, data=None):
    key = f"{subject}-{task_number}-{data_type}"
    if data is not None:
        cache.set(key, pickle.dumps(data))
    cached_data = pickle.loads(cache.get(key))
    return pickle.loads(cached_data) if cached_data is not None else None

def handle_subject_and_task(update, context, subject, task_number):
    cached_data = get_or_cache_data(subject, task_number, "answer")
    cached_images_data = get_or_cache_data(subject, task_number, "images")

    if cached_images_data:
        media_group = [InputMediaPhoto(BytesIO(image_data)) for image_data in cached_images_data]
        update.message.reply_media_group(media=media_group)
    if cached_data:
        update.message.reply_text(cached_data, parse_mode='Markdown', reply_markup=create_return_keyboard())
        return

    drive_service = get_google_drive_service()
    sheets_service = get_google_sheets_service()

    if not drive_service or not sheets_service:
        update.message.reply_text("Виникла проблема при з'єднанні з Google Диск.")
        return

    if not cached_images_data:
        images = find_images(drive_service, subject, task_number)
        images_data = []
        for image in images:
            image_file = drive_service.files().get_media(fileId=image['id']).execute()
            image_data = BytesIO(image_file)
            images_data.append(image_data.getvalue())
            context.bot.send_photo(chat_id=update.effective_chat.id, photo=image_data)
        get_or_cache_data(subject, task_number, "images", images_data)

    if not cached_data:
        file_id = find_file(drive_service, f'{subject} {task_number}', None)
        if not file_id:
            update.message.reply_text("Вибач, цю відповідь ще не додали.", reply_markup=create_subjects_keyboard())
            return

        table_content = get_table_content_from_google_sheets(sheets_service, file_id)

    response = []
    for i, row in enumerate(table_content):
        question, answer = row
        if "Правильна відповідь:" in answer:
            answer = answer.replace("Правильна відповідь:", "")
        response.append(f"*Питання:* {question}\n*Відповідь:* {answer}\n")

    response_text = f"Ось відповідь на завдання {subject} {task_number}:\n\n" + "\n".join(response)

    if len(response_text) > 4096:
        messages = []
        current_message = ""
        for line in response:
            if len(current_message + line) > 4096:
                messages.append(current_message)
                current_message = ""
            current_message += line
        messages.append(current_message)

        for message in messages:
            update.message.reply_text(message, parse_mode='Markdown')
    else:
        update.message.reply_text(response_text, parse_mode='Markdown', reply_markup=create_return_keyboard())
        get_or_cache_data(subject, task_number, "answer", response_text)

def handle_message(update: Update, context: CallbackContext):
    message = update.message
    text = message.text

    if text in ["Алгебра", "Англійська мова", "Біологія", "Всесвітня історія", "Географія", "Геометрія", "Громадянська освіта", "Зарубіжна література", "Захист України", "Інформатика", "Історія України", "Польська мова", "Мистецство", "Українська література", "Українська мова", "Фізика", "Фізкультура", "Фінансова грамотність", "Хімія"]:
        context.user_data['selected_subject'] = text
        tasks_keyboard = create_tasks_keyboard(text)
        if tasks_keyboard:
            message.reply_text(f"Обери номер завдання:", reply_markup=tasks_keyboard)
        else:
            message.reply_text("Цей предмет поки не доданий, але дуже скоро буде", reply_markup=create_subjects_keyboard())
        return

    if text == "Предмети":
        message.reply_text("Обери предмет:", reply_markup=create_subjects_keyboard())
        return

    if text.isdigit():
        subject = context.user_data.get('selected_subject')
        if subject:
            handle_subject_and_task(update, context, subject, text)
            context.user_data.pop('selected_subject', None)
        else:
            message.reply_text("Будь ласка, спочатку оберіть предмет.")
        return

    if text == "Знайти іншу відповідь":
        message.reply_text("Обери предмет", reply_markup=create_subjects_keyboard())
        return

    match = re.match(r'(.+?)\s+(\d+)$', text)
    if match:
        handle_subject_and_task(update, context, match.group(1), match.group(2))
    else:
        update.message.reply_text("Не вдалося розпізнати текст.", reply_markup=create_subjects_keyboard())

def cache_initial_answers():
    # Тут ви можете додати відповіді для предметів і завдань, які ви хочете закешувати
    initial_answers = [
        ("Алгебра", "34"),
        ("Біологія", "27")
    ]

    for subject, task_number in initial_answers:
        print(f"Caching {subject} {task_number}...")
        handle_subject_and_task(None, None, subject, task_number)

def start(update: Update, context: CallbackContext):
    welcome_message = "Привіт! Я створений, щоб допомогати учням Оптіми 10 класу знаходити відповіді на завдання.\n\nВибери предмет і завдання на яке шукаєш відповідь:"
    update.message.reply_text(welcome_message, parse_mode='Markdown', reply_markup=create_subjects_keyboard())

def main():
    # Видаліть глобальний кеш і завантаження кешу з файлу

    updater = Updater(TELEGRAM_API_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Додати обробник команди start
    dispatcher.add_handler(CommandHandler("start", start))

    # Додати обробник для повідомлень
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()

    print("Bot started. Press Ctrl+C to stop...")

    # Закешуйте відповіді при запуску
    cache_initial_answers()

    # Чекаємо, поки бот не буде зупинений
    updater.idle()

    # Видаліть збереження кешу перед виходом з програми
    print("Bot stopped.")

if __name__ == '__main__':
    main()