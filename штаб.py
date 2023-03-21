import os
import pickle
import re
import openpyxl
from io import BytesIO
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

TELEGRAM_API_TOKEN = '6072271437:AAHcFO46gQAF2yEouLhHZIChaqDNYPW0wSc'
SCOPES = ['https://www.googleapis.com/auth/drive']


def get_google_drive_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('C:/Програми/Сука/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    try:
        service = build('drive', 'v3', credentials=creds)
        return service
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def get_table_content_from_google_sheets(sheets_service, spreadsheet_id):
    range_name = 'A1:B'
    result = sheets_service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    rows = result.get('values', [])
    return rows

def process_excel_file(drive_service, file_id):
    file = drive_service.files().get(fileId=file_id, fields="id, name, mimeType, createdTime").execute()
    file_name = file.get("name")

    file_data = drive_service.files().export(fileId=file_id,
                                             mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet").execute()

    with open(f"{file_name}", "wb") as f:
        f.write(file_data)

    wb = openpyxl.load_workbook(file_name)
    ws = wb.active

    content = []
    for row in ws.iter_rows(min_row=3, values_only=True):
        if not row or not row[0]:
            break
        content.append((row[0], row[1]))

    os.remove(file_name)

    return content


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
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('C:/Програми/Сука/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    try:
        service = build('sheets', 'v4', credentials=creds)
        return service
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def find_images(drive_service, subject, task_number, folder_id=None):
    query = f"mimeType='image/png' and trashed = false and name contains '{subject} {task_number}'"
    if folder_id:
        query += f" and '{folder_id}' in parents"
    results = drive_service.files().list(q=query).execute()
    items = results.get('files', [])
    return items

def handle_message(update: Update, context: CallbackContext):
    message = update.message.text
    if not message:
        return

    drive_service = get_google_drive_service()
    sheets_service = get_google_sheets_service()

    if not drive_service or not sheets_service:
        update.message.reply_text("Виникла проблема при з'єднанні з Google Диск.")
        return

    match = re.match(r'(.+?)\s+(\d+)$', message)
    if match:
        subject = match.group(1)
        task_number = match.group(2)
    else:
        update.message.reply_text("Неправильний формат введення. Будь ласка, введіть предмет та номер завдання.")
        return

    file_id = find_file(drive_service, f'{subject} {task_number}', None)
    if not file_id:
        update.message.reply_text("Вибач, цю відповідь ще не додали.")
        return

    table_content = get_table_content_from_google_sheets(sheets_service, file_id)

    images = find_images(drive_service, subject, task_number)
    for image in images:
        image_file = drive_service.files().get_media(fileId=image['id']).execute()
        update.message.reply_photo(photo=BytesIO(image_file))
        
    response = []
    for i, row in enumerate(table_content):
        question, answer = row
        if "Правильна відповідь:" in answer:
            answer = answer.replace("Правильна відповідь:", "")
        response.append(f"*Питання:* {question}\n*Відповідь:* {answer}\n")

    # Видалити перші два рядки та порожній рядок після них
    response = response[2:]
    if response and not response[0].strip():
        response = response[1:]

    # Перевірити чи повідомлення не занадто довге
    if len("\n".join(response)) > 4096:
        # Розбити повідомлення на частини
        messages = []
        current_message = ""
        for line in response:
            if len(current_message + line) > 4096:
                messages.append(current_message)
                current_message = ""
            current_message += line
        messages.append(current_message)

        # Відправити кожну частину окремо
        for message in messages:
            update.message.reply_text(message, parse_mode='Markdown')
    else:
        update.message.reply_text(f"Ось відповідь на завдання {subject} {task_number}:\n\n" + "\n".join(response), parse_mode='Markdown')

def start(update: Update, context: CallbackContext):
    welcome_message = "Привіт! Я допоможу тобі швидко знаходити відповіді на завдання. Наразі я маю доступ до відповідей за 10 клас з:\n*- Інформатики*\n*- Географії*\n*- Біології*\n\nЩоб отримати відповідь надішли назву предмету і номер завдання, наприклад Біологія 45"
    update.message.reply_text(welcome_message, parse_mode='Markdown')

def main():
    updater = Updater(TELEGRAM_API_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Додати обробник команди start
    dispatcher.add_handler(CommandHandler("start", start))

    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
