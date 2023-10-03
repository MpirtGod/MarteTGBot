import imaplib
import email
import time
import base64
from bs4 import BeautifulSoup
import re
from config import mail_pass, username, imap_server, search_folder
from datetime import datetime, timedelta
import quopri
from collections import Counter


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
    else:
        return ''


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
    delivery_parts = []
    free_delivery = 0
    for message in all_messages:
        total = float(re.search('Sub total: (.+?) RUB', message).group(1))
        if 'Екатеринбург' not in message:
            delivery = re.search('Delivery: (.+?) Payment', message).group(1)
            try:
                delivery = re.findall("[+-]?\d+\.\d+", delivery)
                delivery = delivery[0]
            except (Exception) as exp:
                delivery = 0
            delivery = float(delivery)
            total += delivery
            if delivery != 0:
                delivery_total.append(delivery)
                if 'Долями' in message:
                    delivery_parts.append(delivery)
            else: free_delivery += 1
        all_mess_total.append(total)
        if 'Долями' in message:
            parts.append(total)

    start_date = start_date.strftime('%d.%m.%Y')
    end_date = end_date.strftime('%d.%m.%Y')
    total = '{0:,}'.format(round(sum(all_mess_total))).replace(',', ' ')
    total_sdek = '{0:,}'.format(round(sum(delivery_total))).replace(',', ' ')
    total_parts = '{0:,}'.format(round(sum(parts))).replace(',', ' ')
    total_full = '{0:,}'.format(round(sum(all_mess_total) - sum(parts))).replace(',', ' ')
    delivery_parts_sum = '{0:,}'.format(round(sum(delivery_parts))).replace(',', ' ')
    delivery_full_sum = '{0:,}'.format(round(sum(delivery_total)-sum(delivery_parts))).replace(',', ' ')

    return f"Диапазон поиска:\n" \
           f"{start_date} - {end_date}\n\n" \
           f"Найдено заказов: {len(all_messages)}\n" \
           f"Сумма за все заказы: {total}₽\n\n" \
           f"Сумма чеков долями: {total_parts}₽\n" \
           f"Количество чеков долями: {len(parts)}\n\n" \
           f"Сумма полной оплаты: {total_full}₽\n" \
           f"Количество полной оплаты: {len(all_messages) - len(parts)}\n\n" \
           f"Количество доставок всего: {len(all_messages)}\n" \
           f"Количество доставок по Екатеринбургу: {len(all_messages) - len(delivery_total) - free_delivery}\n" \
           f"Количество бесплатных доставок: {free_delivery}\n" \
           f"Количество доставок в другие города: {len(delivery_total)}\n\n" \
           f"Сумма СДЕК: {total_sdek}₽\n" \
           f"Сумма СДЕК долями: {delivery_parts_sum}₽\n" \
           f"Количество СДЕК долями: {len(delivery_parts)}\n" \
           f"Сумма СДЕК полной оплаты: {delivery_full_sum}₽\n" \
           f"Количество СДЕК полной оплаты: {len(delivery_total) - len(delivery_parts)}"


def get_cities(all_messages):
    cities = []
    for message in all_messages:
        address = re.search('RU: (.+?) Purchaser', message).group(1)
        address = re.sub(r' Amount:.*', '', address)
        address = re.sub(r' Comments:.*', '', address)
        address = address.replace('Point: ', '').split(', ')
        address = [s for s in address if not re.search(r'[0-9,:.]', s) and not "ул " in s and not "проспект" in s and
                   not "шоссе" in s and not "пр-т" in s and not "Рокоссовского" in s]
        cities += address
    counter = Counter(cities).most_common(5)
    result = 'Статистика по городам, в которые чаще всего заказывают (Топ-5):\n'
    for city, count in counter:
        result += f'{city}: {count}\n'
    return result


def make_statistic(start_date, end_date=datetime.now(), by_cities=False):
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
    # print(message_uids)
    # print(len(message_uids))

    start = time.time()
    all_messages = []
    for i, message_uid in enumerate(message_uids):
        res, msg = imap.uid('fetch', message_uid, '(RFC822)')
        msg = email.message_from_bytes(msg[0][1])

        letter_date = datetime(*email.utils.parsedate_tz(msg["Date"])[0:6])
        if (end_date.strftime("%d-%b-%Y") == letter_date.strftime("%d-%b-%Y") and letter_date.hour >= 22) or \
           (check_date.strftime("%d-%b-%Y") == letter_date.strftime("%d-%b-%Y") and letter_date.hour < 22):
            continue
        # print(decode_header(msg["Subject"])[0][0].decode())

        # print(type(msg))

        # for part in msg.walk():
        #     print(part.get_content_type())
        all_messages.append(get_letter_text(msg))

    # print('\n'.join(all_messages))
    print("-------------Done in {:4}-------------\n".format(time.time() - start))
    imap.logout()
    if not by_cities:
        return convert_statistic(all_messages, start_date, end_date)
    else:
        return get_cities(all_messages)

if __name__ == '__main__':
    print(make_statistic(datetime(2022, 7, 1), by_cities=True))
