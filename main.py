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
from googletrans import Translator

global all_messages
global rus_cities


def get_letter_text_from_html(body):
    """
    Извлекает текст из HTML-тела письма.

    Parameters
    ----------
    body : str
        HTML-текст тела письма.

    Returns
    -------
    str
        Текст письма, извлеченный из HTML.
    bool
        False в случае ошибки при извлечении текста из HTML.
    """
    try:
        body = re.sub(re.compile(r'<a.*?a>', re.DOTALL), '', body) #Удаляет название вещи, убрать если нужна вещь, переписать статистику по вещам
        soup = BeautifulSoup(body, "html.parser")
        text = soup.get_text()

        return text.replace("\xa0", "")
    except Exception as exp:
        print("text from html err ", exp)
        return False


def letter_type(part):
    """
    Определяет тип части (attachment) письма и возвращает соответствующее содержимое.

    Parameters
    ----------
    part : email.message.Message
        Часть письма.

    Returns
    -------
    str
        Содержимое части письма в текстовом формате.
    """
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
    """
    Извлекает текст из части письма.

    Parameters
    ----------
    msg : email.message.Message
        Часть письма.

    Returns
    -------
    str
        Извлеченный текст из части письма.
    """
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
    """
    Извлекает текст из всего письма, включая все его части.

    Parameters
    ----------
    msg : email.message.Message
        Письмо.

    Returns
    -------
    str
        Извлеченный текст из всего письма.
    """
    if msg.is_multipart():
        str = ''
        for part in msg.walk():
            str += extract_text(part)
        msg = str
    else:
        msg = extract_text(msg)
    return msg


def get_sales_statistic(all_messages, start_date, end_date):
    """
    Высчитывает и преобразует статистику по заказам в удобочитаемый текст.

    Parameters
    ----------
    all_messages : list of str
        Список сообщений с информацией о заказах.
    start_date : datetime
        Начальная дата периода статистики.
    end_date : datetime
        Конечная дата периода статистики.

    Returns
    -------
    str
        Текстовое представление статистики по заказам.
    """

    all_mess_total = []
    parts = []
    products_count = []
    products_parts_count = []
    for message in all_messages:
        #----------------- Подсчет суммы ----------------
        total = float(re.search('Sub total: (.+?) RUB', message).group(1))
        if 'Екатеринбург' not in message:
            delivery = re.search('Delivery: (.+?) Payment', message).group(1)
            try:
                delivery = re.findall(r"\d*\.?\d+", delivery) #\.\d+
                delivery = delivery[0]
            except (Exception) as exp: #Обработка бесплатной доставки
                delivery = 0
            delivery = float(delivery)
            total += delivery
        all_mess_total.append(total)
        if 'Долями' in message:
            parts.append(total)
        #------------------------------------------------
        #-------- Подсчет статистики по товарам ---------
        products_list = re.search('Amount (.+?) RUB Subtotal', message).group(1)
        products_list = [float(match.group()) for match in re.finditer(r'\b\d+\.\d+|\b\d+\b', products_list)][2::4]
        products_count += products_list
        if 'Долями' in message:
            products_parts_count += products_list
        # -----------------------------------------------

    start_date = start_date.strftime('%d.%m.%Y')
    end_date = end_date.strftime('%d.%m.%Y')
    all_mess_total = round(sum(all_mess_total))
    len_parts = len(parts)
    parts = round(sum(parts))
    products_total = int(sum(products_count))
    products_parts_total = int(sum(products_parts_count))
    products_full_total = products_total - products_parts_total

    #Преобразование чисел в нужный формат

    total = '{0:,}'.format(all_mess_total).replace(',', ' ')
    total_parts = '{0:,}'.format(parts).replace(',', ' ')
    total_full = '{0:,}'.format(round(all_mess_total - parts)).replace(',', ' ')

    #Переменные по чекам
    mean_receipt = '0' if all_mess_total == 0 else '{0:,}'.format(round(all_mess_total/len(all_messages))).replace(',', ' ')
    mean_product_count = '0' if products_total == 0 else '{0:,}'.format(round(products_total/len(all_messages), 2)).replace(',', ' ')
    mean_product_price = '0' if all_mess_total == 0 else '{0:,}'.format(round(all_mess_total/products_total)).replace(',', ' ')

    mean_receipt_parts = '0' if parts == 0 else '{0:,}'.format(round(parts / len_parts)).replace(',', ' ')
    mean_product_count_parts = '0' if products_parts_total == 0 else '{0:,}'.format(round(products_parts_total / len_parts, 2)).replace(',', ' ')
    mean_product_price_parts = '0' if parts == 0 else '{0:,}'.format(round(parts / products_parts_total)).replace(',', ' ')

    mean_receipt_full = '0' if (all_mess_total - parts) == 0 else '{0:,}'.format(round((all_mess_total - parts) / (len(all_messages) - len_parts))).replace(',', ' ')
    mean_product_count_full = '0' if products_full_total == 0 else '{0:,}'.format(round(products_full_total / (len(all_messages) - len_parts), 2)).replace(',', ' ')
    mean_product_price_full = '0' if (all_mess_total - parts) == 0 else '{0:,}'.format(round((all_mess_total - parts) / products_full_total)).replace(',', ' ')

    if all_mess_total != 0:
        return f"<b>Диапазон поиска:</b>\n" \
               f"<b>{start_date} - {end_date}</b>\n\n" \
               f"Найдено заказов: {len(all_messages)}\n" \
               f"Количество товаров: {products_total}\n" \
               f"Сумма за все заказы: {total}₽\n" \
               f"Средний чек: {mean_receipt}₽\n" \
               f"Среднее количество товаров в чеке: {mean_product_count} шт\n" \
               f"Средняя стоимость товара: {mean_product_price}₽\n\n" \
               f"<b><u>Оплата долями:</u></b>\n" \
               f"Сумма заказов: {total_parts}₽ - {round(parts/all_mess_total*100, 2)}%\n" \
               f"Количество чеков: {len_parts} - {round(len_parts/len(all_messages)*100, 2)}%\n" \
               f"Средний чек: {mean_receipt_parts}₽\n" \
               f"Среднее количество товаров в чеке: {mean_product_count_parts} шт\n" \
               f"Средняя стоимость товара: {mean_product_price_parts}₽\n\n" \
               f"<b><u>Полная оплата:</u></b>\n" \
               f"Сумма заказов: {total_full}₽ - {round(100 - parts/all_mess_total*100, 2)}%\n" \
               f"Количество чеков: {len(all_messages) - len_parts} - {round(100 - len_parts/len(all_messages)*100,2)}%\n" \
               f"Средний чек: {mean_receipt_full}₽\n" \
               f"Среднее количество товаров в чеке: {mean_product_count_full} шт\n" \
               f"Средняя стоимость товара: {mean_product_price_full}₽"
    else:
        return f"Диапазон поиска:\n" \
               f"{start_date} - {end_date}\n\n" \
               f"Найдено заказов: 0\n"


def find_city(message):
    translator = Translator()
    if "Address" not in message:
        return "Не найден"
    address = re.search('RU: (.+?) Purchaser', message).group(1)
    address = re.sub(r' Amount:.*', '', address)
    address = re.sub(r' Comments:.*', '', address)
    address = address.split(', ')
    for location in address:
        if location.lower().strip() in rus_cities:
            return location
    for location in address:
        location = translator.translate(location, src='en', dest='ru').text
        if location.lower().strip() in rus_cities:
            return location


def get_cities_statistic(all_messages, start_date, end_date):
    """
    Высчитывает и преобразует статистику по городам в удобочитаемый текст.

    Parameters
    ----------
    all_messages : list of str
        Список сообщений с информацией о заказах.
    start_date : datetime
        Начальная дата периода статистики.
    end_date : datetime
        Конечная дата периода статистики.

    Returns
    -------
    str
        Текстовое представление статистики по городам.
    """
    cities = []
    all_cities_total = 0
    all_cities_delivery = 0
    total_by_cities = {}
    delivery_by_cities = {}
    products_count = {}
    all_cities_products = []
    for message in all_messages:
        city = find_city(message)
        cities.append(city)

        total = float(re.search('Sub total: (.+?) RUB', message).group(1))
        if 'Екатеринбург' not in message:
            delivery = re.search('Delivery: (.+?) Payment', message).group(1)
            try:
                delivery = re.findall(r"\d*\.?\d+", delivery) #\.\d+
                delivery = delivery[0]
            except (Exception) as exp:
                delivery = 0
            delivery = float(delivery)
            total += delivery
        else: delivery = 0
        delivery_by_cities.setdefault(city, 0)
        delivery_by_cities[city] += delivery
        all_cities_delivery += delivery

        total_by_cities.setdefault(city, 0)
        total_by_cities[city] += total - delivery
        all_cities_total += total

        products_count.setdefault(city, [])
        products_list = re.search('Amount (.+?) RUB Subtotal', message).group(1)
        products_list = [float(match.group()) for match in re.finditer(r'\b\d+\.\d+|\b\d+\b', products_list)][2::4]
        products_count[city] += products_list
        all_cities_products += products_list

    start_date = start_date.strftime('%d.%m.%Y')
    end_date = end_date.strftime('%d.%m.%Y')
    all_cities_products_sum = int(sum(all_cities_products))
    counter = Counter(cities).most_common()
    city_statistic = []
    for city, count in counter:
        city_total = round(total_by_cities[city])
        city_delivery = round(delivery_by_cities[city])
        city_products_count = int(sum(products_count[city]))
        city_statistic.append((city, count, city_total, city_delivery, city_products_count))

    sorted_city_statistic = sorted(city_statistic, key=lambda x: (-x[1], -x[2])) #Сортировка по количеству заказов, второстепенно по процентам

    #Преобразование чисел в нужный формат

    cities_total = '{0:,}'.format(round(all_cities_total)).replace(',', ' ')
    city_delivery = '{0:,}'.format(round(all_cities_delivery)).replace(',', ' ')

    result = f"<b>Диапазон поиска:</b>\n" \
             f"<b>{start_date} - {end_date}</b>\n\n" \
             f'Найдено заказов: {len(cities)}\n' \
             f'Сумма за все заказы: {cities_total}₽ (С учетом доставки)\n' \
             f'Сумма доставки за все заказы: {city_delivery}₽\n' \
             f'Количество товаров: {all_cities_products_sum}\n\n' \
             f'<b><u>Статистика по городам, в которые чаще всего заказывают (Топ-10):</u></b>\n\n'
    i = 0
    for city in sorted_city_statistic:
        if i == 10:
            break
        city_percent = round(total_by_cities[city[0]]/all_cities_total*100, 2)
        city_delivery_percent = round(delivery_by_cities[city[0]]/all_cities_delivery * 100, 2) if all_cities_delivery != 0 else 0
        city_sales = "{0:,}".format(round(city[2])).replace(",", " ")
        city_delivery = "{0:,}".format(round(city[3])).replace(",", " ")
        city_mean_recipe = "{0:,}".format(round(city[2]/city[1])).replace(",", " ")

        result += f'<b>{city[0]}</b>: {city[1]} ({city_sales}₽) - {city_percent}%\n' \
                  f'Средний чек: {city_mean_recipe}₽\n' \
                  f'Среднее количество товаров: {round(city[4]/city[1],2)} шт\n' \
                  f'Сумма доставки: {city_delivery}₽ - {city_delivery_percent}%\n\n'
        i+=1
    return result


def get_sdek_statistic(all_messages, start_date, end_date):
    """
    Высчитывает и преобразует статистику по доставкам в удобочитаемый текст.

    Parameters
    ----------
    all_messages : list of str
        Список сообщений с информацией о заказах.
    start_date : datetime
        Начальная дата периода статистики.
    end_date : datetime
        Конечная дата периода статистики.

    Returns
    -------
    str
        Текстовое представление статистики по доставке.
    """

    all_mess_total = []
    delivery_total = []
    delivery_parts = []
    free_delivery = 0
    for message in all_messages:
        total = float(re.search('Sub total: (.+?) RUB', message).group(1))
        if 'Екатеринбург' not in message:
            delivery = re.search('Delivery: (.+?) Payment', message).group(1)
            try:
                delivery = re.findall(r"\d*\.?\d+", delivery) #\.\d+
                delivery = delivery[0]
            except (Exception) as exp: #Обработка бесплатной доставки
                delivery = 0
            delivery = float(delivery)
            total += delivery
            if delivery != 0:
                delivery_total.append(delivery)
                if 'Долями' in message:
                    delivery_parts.append(delivery)
            else: free_delivery += 1
        all_mess_total.append(total)

    start_date = start_date.strftime('%d.%m.%Y')
    end_date = end_date.strftime('%d.%m.%Y')
    all_mess_total = round(sum(all_mess_total))
    len_delivery_total = len(delivery_total)
    delivery_total = round(sum(delivery_total))
    len_delivery_parts = len(delivery_parts)
    delivery_parts = round(sum(delivery_parts))
    ekb_delivery = len(all_messages) - len_delivery_total - free_delivery

    #Преобразование чисел в нужный формат

    total = '{0:,}'.format(all_mess_total).replace(',', ' ')
    total_sdek = '{0:,}'.format(delivery_total).replace(',', ' ')
    delivery_parts_sum = '{0:,}'.format(delivery_parts).replace(',', ' ')
    delivery_full_sum = '{0:,}'.format(round(delivery_total-delivery_parts)).replace(',', ' ')

    if all_mess_total != 0:
        result = f"<b>Диапазон поиска:</b>\n" \
                 f"<b>{start_date} - {end_date}</b>\n\n" \
                 f"Найдено заказов: {len(all_messages)}\n" \
                 f"Сумма за все заказы: {total}₽\n\n" \
                 f"Количество доставок всего: {len(all_messages)}\n" \
                 f"Количество доставок по Екатеринбургу: {ekb_delivery} - {round(ekb_delivery/len(all_messages)*100,2)}%\n" \
                 f"Количество бесплатных доставок: {free_delivery} - {round(free_delivery/len(all_messages)*100,2)}%\n" \
                 f"Количество доставок в другие города: {len_delivery_total} - {round(len_delivery_total/len(all_messages)*100,2)}%\n\n"
    else: return f"<b>Диапазон поиска:</b>\n" \
                 f"<b>{start_date} - {end_date}</b>\n\n" \
                 f"Найдено заказов: 0\n"

    if delivery_total != 0:
        result += f"Сумма СДЭК: {total_sdek}₽ - {round(delivery_total/all_mess_total*100,2)}%\n" \
                  f"Сумма СДЭК долями: {delivery_parts_sum}₽ - {round(delivery_parts/delivery_total*100,2)}%\n" \
                  f"Количество СДЭК долями: {len_delivery_parts} - {round(len_delivery_parts/len_delivery_total*100,2)}%\n" \
                  f"Сумма СДЭК полной оплаты: {delivery_full_sum}₽ - {round(100 - delivery_parts/delivery_total*100,2)}%\n" \
                  f"Количество СДЭК полной оплаты: {len_delivery_total - len_delivery_parts} - {round((len_delivery_total - len_delivery_parts)/len_delivery_total*100,2)}%"
    else: result += 'Сумма СДЭК: 0₽ - 0%'
    return result


def pull_message(message_uid, check_date, end_date):
    """
    Получает текст сообщения по его UID из почтового ящика.

    Parameters
    ----------
    message_uid : str
        Уникальный идентификатор сообщения.
    check_date : datetime
        Дата начала периода для фильтрации сообщений.
    end_date : datetime
        Дата конца периода для фильтрации сообщений.

    Returns
    -------
    None
        Сообщение добавлено в глобальный список all_messages, если соответствует условиям фильтрации.
    """
    imap = imaplib.IMAP4_SSL(imap_server)
    imap.login(username, mail_pass)
    imap.select(search_folder)

    res, msg = imap.uid('fetch', message_uid, '(RFC822)')
    msg = email.message_from_bytes(msg[0][1])

    letter_date = datetime(*email.utils.parsedate_tz(msg["Date"])[0:6])
    if not (end_date.strftime("%d-%b-%Y") == letter_date.strftime("%d-%b-%Y") and letter_date.hour >= 22) and \
       not (check_date.strftime("%d-%b-%Y") == letter_date.strftime("%d-%b-%Y") and letter_date.hour < 22):  # Корректировка даты с учетом часового поиса. Изначально - МСК
        all_messages.append(get_letter_text(msg))
    # print(decode_header(msg["Subject"])[0][0].decode())

    # print(type(msg))

    # for part in msg.walk():
    #     print(part.get_content_type())
    imap.logout()


def make_statistic(start_date, end_date, kind_of_statistic):
    """
    Создает статистику по заказам за указанный период.

    Parameters
    ----------
    start_date : datetime
        Начальная дата периода статистики.
    end_date : datetime
        Конечная дата периода статистики.
    by_cities : bool
        Флаг, указывающий на необходимость создания статистики по городам.
        По умолчанию False.

    Returns
    -------
    str
        Текстовое представление статистики по заказам или по городам.
    """
    global all_messages
    global rus_cities

    with open('rus_cities.txt', encoding='UTF-8') as file:
        rus_cities = file.read().lower()

    check_date = start_date - timedelta(days=1)
    # resp_code, directories = imap.list(directory="[Mail]")
    # for directory in directories:
    #     print(directory.decode())

    sender = 'noreply@tilda.ws'
    imap = imaplib.IMAP4_SSL(imap_server)
    imap.login(username, mail_pass)
    imap.select(search_folder)

    # Почему-то в один момент imaplib перестал искать письма при совместном поиске по дате и отправителю, пришлось разбить на два отдельных
    search_criteria_by_date = f'(SINCE "{check_date.strftime("%d-%b-%Y")}" BEFORE "{(end_date + timedelta(days=1)).strftime("%d-%b-%Y")}")'
    status, message_uids_by_date = imap.uid('search', None, search_criteria_by_date)
    message_uids_by_date = str(message_uids_by_date[0])[2:-1].split()

    search_criteria_by_sender = f'(FROM "{sender}")'
    status, message_uids_by_sender = imap.uid('search', None, search_criteria_by_sender)
    message_uids_by_sender = str(message_uids_by_sender[0])[2:-1].split()
    message_uids = list(set(message_uids_by_date).intersection(message_uids_by_sender))
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
    if kind_of_statistic == 'статистика по продажам':
        return get_sales_statistic(all_messages, start_date, end_date)
    elif kind_of_statistic == 'статистика по городам':
        return get_cities_statistic(all_messages, start_date, end_date)
    elif kind_of_statistic == 'статистика по доставкам':
        return get_sdek_statistic(all_messages, start_date, end_date)
    else: return "Ошибка"