import imaplib
import email
from datetime import datetime
from email.header import decode_header
import base64
from bs4 import BeautifulSoup
import re
from login import mail_pass, username


imap_server = "imap.mail.ru"
imap = imaplib.IMAP4_SSL(imap_server)
imap.login(username, mail_pass)

sender = 'istudentsendmail@urfu.email'
start_date = datetime(2023, 8, 1).strftime('%d-%b-%Y')
search_criteria = f'(FROM "{sender}" SINCE "{start_date}")'

imap.select()

status, message_ids = imap.uid('search', None, search_criteria)
print(str(message_ids[0]))
message_ids = str(message_ids[0])[2:-1].split()
print(message_ids)
res, msg = imap.uid('fetch', message_ids[0], '(RFC822)')
msg = email.message_from_bytes(msg[0][1])

print(decode_header(msg["Subject"])[0][0].decode())

print(type(msg))

for part in msg.walk():
    print(part.get_content_type())

for part in msg.walk():
    if part.get_content_maintype() == 'text' and part.get_content_subtype() == 'html':
        soup = BeautifulSoup(base64.b64decode(part.get_payload()).decode(), 'html.parser')
        print(soup.get_text())







# res, msg = imap.uid('fetch', message_ids[0], '(RFC822)')
# print(msg)
# if status == 'OK':
#     # Получение списка идентификаторов найденных сообщений
#     message_id_list = message_ids[0].split()
#     for message_id in message_id_list:
#         # Получение текста сообщения
#         status, message_data = imap.fetch(message_id, '(RFC822)')
#         if status == 'OK':
#             # Обработка текста сообщения
#             raw_message = message_data[0][1]
#             message_text = raw_message.decode('windows-1251')
#             print(message_text)
# imap.logout()