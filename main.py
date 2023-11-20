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
import multiprocessing
from multiprocessing.pool import ThreadPool

global all_messages

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
    all_mess_total = round(sum(all_mess_total))
    len_delivery_total = len(delivery_total)
    delivery_total = round(sum(delivery_total))
    len_parts = len(parts)
    parts = round(sum(parts))
    len_delivery_parts = len(delivery_parts)
    delivery_parts = round(sum(delivery_parts))
    ekb_delivery = len(all_messages) - len_delivery_total - free_delivery

    total = '{0:,}'.format(all_mess_total).replace(',', ' ')
    total_sdek = '{0:,}'.format(delivery_total).replace(',', ' ')
    total_parts = '{0:,}'.format(parts).replace(',', ' ')
    total_full = '{0:,}'.format(round(all_mess_total - parts)).replace(',', ' ')
    delivery_parts_sum = '{0:,}'.format(delivery_parts).replace(',', ' ')
    delivery_full_sum = '{0:,}'.format(round(delivery_total-delivery_parts)).replace(',', ' ')

    return f"Диапазон поиска:\n" \
           f"{start_date} - {end_date}\n\n" \
           f"Найдено заказов: {len(all_messages)}\n" \
           f"Сумма за все заказы: {total}₽\n\n" \
           f"Сумма чеков долями: {total_parts}₽ - {round(parts/all_mess_total*100,2)}%\n" \
           f"Количество чеков долями: {len_parts} - {round(len_parts/len(all_messages)*100,2)}%\n\n" \
           f"Сумма полной оплаты: {total_full}₽ - {round(100 - parts/all_mess_total*100,2)}%\n" \
           f"Количество полной оплаты: {len(all_messages) - len_parts} - {round(100 - len_parts/len(all_messages)*100,2)}%\n\n" \
           f"Количество доставок всего: {len(all_messages)}\n" \
           f"Количество доставок по Екатеринбургу: {ekb_delivery} - {round(ekb_delivery/len(all_messages)*100,2)}%\n" \
           f"Количество бесплатных доставок: {free_delivery} - {round(free_delivery/len(all_messages)*100,2)}%\n" \
           f"Количество доставок в другие города: {len_delivery_total} - {round(len_delivery_total/len(all_messages)*100,2)}%\n\n" \
           f"Сумма СДЕК: {total_sdek}₽ - {round(delivery_total/all_mess_total*100,2)}%\n" \
           f"Сумма СДЕК долями: {delivery_parts_sum}₽ - {round(delivery_parts/delivery_total*100,2)}%\n" \
           f"Количество СДЕК долями: {len_delivery_parts} - {round(len_delivery_parts/len_delivery_total*100,2)}%\n" \
           f"Сумма СДЕК полной оплаты: {delivery_full_sum}₽ - {round(100 - delivery_parts/delivery_total*100,2)}%\n" \
           f"Количество СДЕК полной оплаты: {len_delivery_total - len_delivery_parts} - {round((len_delivery_total - len_delivery_parts)/len_delivery_total*100,2)}%"


def get_cities_statistic(all_messages, start_date, end_date):
    cities = []
    all_city_total = 0
    total_by_cities = {}
    eng_to_rus = {'Pervouralsk': 'Первоуральск', 'Saint Petersburg': 'Санкт-Петербург'}
    for message in all_messages:
        address = re.search('RU: (.+?) Purchaser', message).group(1)
        address = re.sub(r' Amount:.*', '', address)
        address = re.sub(r' Comments:.*', '', address)
        address = address.split(', ')
        if "Point" in address[0]:
            city = address[-1]
        else:
            city = address[1]
        if re.search('[a-zA-Z]', city):
            city = eng_to_rus[city]
        cities.append(city)

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

        total_by_cities.setdefault(city, 0)
        total_by_cities[city] += total
        all_city_total += total

    start_date = start_date.strftime('%d.%m.%Y')
    end_date = end_date.strftime('%d.%m.%Y')
    counter = Counter(cities).most_common()
    city_statistic = []
    for city, count in counter:
        city_total = round(total_by_cities[city])
        city_statistic.append((city, count, city_total))

    sorted_city_statistic = sorted(city_statistic, key=lambda x: (-x[1], -x[2]))

    cities_total = '{0:,}'.format(round(all_city_total)).replace(',', ' ')

    result = f"Диапазон поиска:\n" \
             f"{start_date} - {end_date}\n\n" \
             f'Сумма за заказы: {cities_total}₽\n' \
             f'Количество заказов: {len(cities)}\n\n' \
             f'<b>Статистика по городам, в которые чаще всего заказывают (Топ-10):</b>\n\n'
    i = 0
    for city in sorted_city_statistic:
        if i == 10:
            break
        city_percent = round(total_by_cities[city[0]]/all_city_total*100, 2)
        city_sales = "{0:,}".format(round(city[2])).replace(",", " ")
        result += f'{city[0]}: {city[1]} ({city_sales}₽) - {city_percent}%\n'
        i+=1
    return result


def pull_message(message_uid, check_date, end_date):
    imap = imaplib.IMAP4_SSL(imap_server)
    imap.login(username, mail_pass)
    imap.select(search_folder)

    res, msg = imap.uid('fetch', message_uid, '(RFC822)')
    msg = email.message_from_bytes(msg[0][1])

    letter_date = datetime(*email.utils.parsedate_tz(msg["Date"])[0:6])
    if not (end_date.strftime("%d-%b-%Y") == letter_date.strftime("%d-%b-%Y") and letter_date.hour >= 22) and \
       not (check_date.strftime("%d-%b-%Y") == letter_date.strftime("%d-%b-%Y") and letter_date.hour < 22):
        all_messages.append(get_letter_text(msg))
    # print(decode_header(msg["Subject"])[0][0].decode())

    # print(type(msg))

    # for part in msg.walk():
    #     print(part.get_content_type())
    imap.logout()


def make_statistic(start_date, end_date, by_cities=False):
    global all_messages
    check_date = start_date - timedelta(days=1)

    # resp_code, directories = imap.list(directory="[Mail]")
    # for directory in directories:
    #     print(directory.decode())

    sender = 'noreply@tilda.ws'
    search_criteria = f'(FROM "{sender}" SINCE "{check_date.strftime("%d-%b-%Y")}" BEFORE "{(end_date + timedelta(days=1)).strftime("%d-%b-%Y")}")'
    imap = imaplib.IMAP4_SSL(imap_server)
    imap.login(username, mail_pass)
    imap.select(search_folder)
    status, message_uids = imap.uid('search', None, search_criteria)
    message_uids = str(message_uids[0])[2:-1].split()
    # print(message_uids)
    # print(len(message_uids))
    imap.logout()

    start = time.time()
    all_messages = []
    with ThreadPool(processes=multiprocessing.cpu_count() * 30) as pool:
        args = []
        for message_uid in message_uids:
            args.append((message_uid, check_date, end_date))
        pool.starmap(pull_message, args)

    # print('\n'.join(all_messages))
    print("-------------Done in {:4}-------------\n".format(time.time() - start))
    if not by_cities:
        return convert_statistic(all_messages, start_date, end_date)
    else:
        return get_cities_statistic(all_messages, start_date, end_date)
