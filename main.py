import imaplib
import email
import time
import base64
from bs4 import BeautifulSoup
import re
from config import mail_pass, username, imap_server, search_folder
from datetime import datetime, timedelta
import quopri


def get_letter_text_from_html(body):
    try:
        soup = BeautifulSoup(body, "html.parser")
        text = soup.get_text()

        return text.replace("\xa0", "")
    except (Exception) as exp:
        print("text ftom html err ", exp)
        return False


def letter_type(part):
    if part["Content-Transfer-Encoding"] in (None, "7bit", "8bit", "binary"):
        return part.get_payload()
    elif part["Content-Transfer-Encoding"] == "base64":
        encoding = part.get_content_charset()
        return base64.b64decode(part.get_payload()).decode(encoding)
    elif part["Content-Transfer-Encoding"] == "quoted-printable":
        encoding = part.get_content_charset()
        return quopri.decodestring(part.get_payload()).decode(encoding)
    else:  # all possible types: quoted-printable, base64, 7bit, 8bit, and binary
        return part.get_payload()


def extract_text(msg):
    count = 0
    if msg.get_content_maintype() == "text" and count == 0:
        extract_part = letter_type(msg)
        if msg.get_content_subtype() == "html":
            letter_text = get_letter_text_from_html(extract_part)
            _RE_COMBINE_WHITESPACE = re.compile(r"\s+")
            letter_text = _RE_COMBINE_WHITESPACE.sub(" ", letter_text).strip()
        else:
            _RE_COMBINE_WHITESPACE = re.compile(r"\s+")
            letter_text = _RE_COMBINE_WHITESPACE.sub(" ", extract_part).strip()
        count += 1
        return letter_text
    else: return ''


def get_letter_text(msg):
    if msg.is_multipart():
        str = ''
        for part in msg.walk():
            str += extract_text(part)
        msg = str
    else:
        msg = extract_text(msg)
    return msg


def convert_statistic(all_messages, start_date, end_date):
    all_mess_total = []
    delivery_total = []
    parts = []
    for message in all_messages:
        total = float(re.search('Sub total: (.+?) RUB', message).group(1))

        if 'Екатеринбург' not in message and float(total)<20000:
            delivery = re.search('Delivery: (.+?) RUB Payment', message).group(1)
            delivery = float(re.findall("[+-]?\d+\.\d+", delivery)[0])
            total += delivery
            delivery_total.append(delivery)
        all_mess_total.append(total)
        if 'Долями' in message:
            parts.append(total)

    start_date = start_date.strftime('%d.%m.%Y')
    end_date = end_date.strftime('%d.%m.%Y')
    total = '{0:,}'.format(round(sum(all_mess_total))).replace(',', ' ')
    total_sdek = '{0:,}'.format(round(sum(delivery_total))).replace(',', ' ')
    total_parts = '{0:,}'.format(round(sum(parts))).replace(',', ' ')
    total_full = '{0:,}'.format(round(sum(all_mess_total)-sum(parts))).replace(',', ' ')

    return f"Диапазон поиска: {start_date} - {end_date}\nНайдено заказов: {len(all_messages)}\nСумма за все заказы: {total}₽\n" \
           f"Сумма СДЕК: {total_sdek}₽. Количество доставок: {len(delivery_total)}\n" \
           f"Сумма долями: {total_parts}₽. Количество долями: {len(parts)}\nСумма полной оплатой: {total_full}₽"

def make_statistic(start_date, end_date=datetime.now()):
    check_date = start_date - timedelta(days=1)
    imap = imaplib.IMAP4_SSL(imap_server)
    imap.login(username, mail_pass)

    # resp_code, directories = imap.list(directory="[Mail]")
    # for directory in directories:
    #     print(directory.decode())

    imap.select(search_folder)
    sender = 'noreply@tilda.ws'
    search_criteria = f'(FROM "{sender}" SINCE "{check_date.strftime("%d-%b-%Y")}" BEFORE "{(end_date + timedelta(days=1)).strftime("%d-%b-%Y")}")'
    status, message_uids = imap.uid('search', None, search_criteria)
    message_uids = str(message_uids[0])[2:-1].split()
    print(message_uids)
    # print(len(message_uids))

    start = time.time()
    all_messages = []
    while True:
        res, msg = imap.uid('fetch', message_uids[-1], '(RFC822)')
        msg = email.message_from_bytes(msg[0][1])
        letter_date = datetime(*email.utils.parsedate_tz(msg["Date"])[0:6])
        if end_date.day == letter_date.day and letter_date.hour>=22:
            message_uids.pop()
        else: break
    while True:
        res, msg = imap.uid('fetch', message_uids[0], '(RFC822)')
        msg = email.message_from_bytes(msg[0][1])
        letter_date = datetime(*email.utils.parsedate_tz(msg["Date"])[0:6])
        if check_date.day == letter_date.day and letter_date.hour<22:
            message_uids.pop(0)
        else: break
    for message_uid in message_uids:
        res, msg = imap.uid('fetch', message_uid, '(RFC822)')
        msg = email.message_from_bytes(msg[0][1])

        # print(decode_header(msg["Subject"])[0][0].decode())

        # print(type(msg))

        # for part in msg.walk():
        #     print(part.get_content_type())
        all_messages.append(get_letter_text(msg))

    # print('\n'.join(all_messages))
    print("-------------Done in {:4}-------------\n".format(time.time() - start))
    imap.logout()
    return convert_statistic(all_messages, start_date, end_date)


# if __name__ == '__main__':
#     print(make_statistic(search_criteria))