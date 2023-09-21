import imaplib
import email
import time
import base64
from bs4 import BeautifulSoup
import re
from config import mail_pass, username, imap_server, search_criteria, search_folder
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


def convert_statistic(all_messages):
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

    return f"Найдено заказов: {len(all_messages)}\nТотал за все заказы: {round(sum(all_mess_total),2)}\nТотал СДЕК: {round(sum(delivery_total),2)}. Количество доставок: {len(delivery_total)}\n" \
           f"Тотал долями: {round(sum(parts),2)}. Количество долями: {len(parts)}\nТотал полной оплатой: {round(sum(all_mess_total)-sum(parts),2)}"

def make_statistic(search_criteria):
    imap = imaplib.IMAP4_SSL(imap_server)
    imap.login(username, mail_pass)

    # resp_code, directories = imap.list(directory="[Mail]")
    # for directory in directories:
    #     print(directory.decode())

    imap.select(search_folder)

    status, message_uids = imap.uid('search', None, search_criteria)
    message_uids = str(message_uids[0])[2:-1].split()
    # print(message_uids)
    # print(len(message_uids))

    start = time.time()
    all_messages = []
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
    return convert_statistic(all_messages)


# if __name__ == '__main__':
#     print(make_statistic(search_criteria))