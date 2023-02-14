from tinkoff.invest import Client, CandleInterval
from tinkoff.invest.utils import now, datetime, timezone, timedelta
import telebot
import requests
import json
import os
import re

if not os.path.exists("./followers_id.json"):
    with open("followers_id.json", "w") as file:
        followers_id = {}
        file.write("{}")
else:
    with open("followers_id.json", "r") as file:
        followers_id = json.loads(file.read())

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'}

with open('tokens.json', 'r') as file:
    tokens = json.loads(file.read())


def get_page(url: str) -> tuple:
    s = requests.Session()
    response = s.get(url=url, headers=headers)
    return response.status_code, response.json()


def get_usd_tinkoff(token: str, figi: str ='BBG0013HGFT4') -> str:
    if now() < datetime(now().year, now().month, now().day, 15, 59, tzinfo=timezone.utc):
        try:
            with Client(token) as client:

                candleusd = client.get_all_candles(figi=figi, from_=now() - timedelta(minutes=1),
                                                   interval=CandleInterval.CANDLE_INTERVAL_1_MIN)
                candlusd = next(candleusd)

                return str(candlusd.close.units) + '.' + str(candlusd.close.nano)[:4]
        except Exception as e:
            print(e)
            return 'Error'

    else:
        with Client(token) as client:

            candleusd = client.get_all_candles(figi=figi, from_=datetime(now().year, now().month, now().day, 15, 59,
                                                                         tzinfo=timezone.utc),
                                               interval=CandleInterval.CANDLE_INTERVAL_1_MIN)
            candlusd = next(candleusd)
        return str(candlusd.close.units) + '.' + str(candlusd.close.nano)[:4] + " (Биржа закрыта)"


def get_rate() -> tuple[str, str, str]:
    korona_gel = get_page(
        'https://koronapay.com/transfers/online/api/transfers/tariffs?sendingCountryId=RUS&sendingCurrencyId=810&receivingCountryId=GEO&receivingCurrencyId=981&paymentMethod=debitCard&receivingAmount=100&receivingMethod=cash&paidNotificationEnabled=true')
    korona_usd = get_page(
        'https://koronapay.com/transfers/online/api/transfers/tariffs?sendingCountryId=RUS&sendingCurrencyId=810&receivingCountryId=GEO&receivingCurrencyId=840&paymentMethod=debitCard&receivingAmount=100&receivingMethod=cash&paidNotificationEnabled=true')
    unistream_usd = get_page(
        'https://online.unistream.ru/card2cash/calculate?destination=GEO&amount=1&currency=USD&accepted_currency=RUB&profile=unistream')
    unistream_gel = get_page(
        'https://online.unistream.ru/card2cash/calculate?destination=GEO&amount=10&currency=GEL&accepted_currency=RUB&profile=unistream')

    korona_list = ["koronapay:", "GEL", " ", "USD", " "]
    unistream_list = ["unistream:", "GEL", " ", "USD", " "]

    korona_list[2] = str(korona_gel[1][0]["exchangeRate"]) if korona_gel[0] == 200 else "Error"
    korona_list[4] = str(korona_usd[1][0]["exchangeRate"]) if korona_usd[0] == 200 else "Error"
    unistream_list[2] = str(round(1 / unistream_gel[1]["fees"][0]["rate"], 4)) if unistream_gel[0] == 200 else "Error"
    unistream_list[4] = str(round(1 / unistream_usd[1]["fees"][0]["rate"], 4)) if unistream_usd[0] == 200 else "Error"

    korona = ' '.join(korona_list)
    unistream = ' '.join(unistream_list)
    tinkoff_usd = "tinkoff: " + "USD " + get_usd_tinkoff(tokens["token_ivest"])
    return korona, unistream, tinkoff_usd


bot = telebot.TeleBot(tokens["token_bot"])


@bot.message_handler(commands=['start'])
def start(message):
    if str(message.chat.id) not in followers_id:
        followers_id[str(message.chat.id)] = {"username": message.chat.username, "status": 1}
        with open("followers_id.json", "w") as file:
            json.dump(followers_id, file, indent=4, ensure_ascii=False)

        korona, unistream, tinkoff_usd = get_rate()
        bot.send_message(message.chat.id, f"{korona}\n{unistream}\n{tinkoff_usd}", parse_mode='html')
        mess = 'Вы подписались на рассылку курса валют. Отправьте /stop, чтобы отписаться.'
        bot.send_message(message.chat.id, mess, parse_mode='html')
        print("@" + message.chat.username, "ID:", message.chat.id, 'following')
        print("Followers:", len(followers_id))
    else:
        followers_id[str(message.chat.id)]["status"] = 1
        with open("followers_id.json", "w") as file:
            json.dump(followers_id, file, indent=4, ensure_ascii=False)
        mess = 'С возвращением! Вы подписались на рассылку курса валют. Отправьте /stop, чтобы отписаться.'
        bot.send_message(message.chat.id, mess, parse_mode='html')
        print("@" + message.chat.username, "ID:", message.chat.id, 'refollowing')

@bot.message_handler(commands=['stop'])
def stop(message):
    followers_id[str(message.chat.id)]["status"] = 0
    with open("followers_id.json", "w") as file:
        json.dump(followers_id, file, indent=4, ensure_ascii=False)
    mess = 'Вы отписались от рассылки курса валют.'
    bot.send_message(message.chat.id, mess, parse_mode='html')
    print("@" + message.chat.username, "ID:", message.chat.id, 'unfollowing')


@bot.message_handler()
def send_rate(message):
    print("@" + message.chat.username, "ID:", message.chat.id, message.text)
    if message.text.lower() == "rate" and message.chat.id in (447391757, 143274204, 472662916):
        korona, unistream, tinkoff_usd = get_rate()
        deluser = []
        for id in followers_id:
            if followers_id[id]["status"] == 1:
                try:
                    bot.send_message(id, f"{korona}\n{unistream}\n{tinkoff_usd}", parse_mode='html')
                except Exception as e:
                    err = re.search(r"(Error code: )(\d+)", str(e)).group(2)
                    print(e)
                    if err == "403":
                        print("bot was blocked by the user:", followers_id[id]["username"], "ID:", id)
                        deluser.append(id)
                        print("User:", followers_id[id]["username"], "ID:", id, "was deleted")
        for id in deluser:
            try:
                del followers_id[id]
            except KeyError:
                print("KeyError in followers_id")
        with open("followers_id.json", "w") as file:
            json.dump(followers_id, file, indent=4, ensure_ascii=False)
    else:
        mess = 'Бот находится на стадии разработки. Курс приходит автоматически в случайное время с пн-пт по запросу админа, в дальнейшем можно будет настроить частоту присылаемых сообщений. Пожалуйста ожидайте новое сообщение с курсом. Спасибо)'
        bot.send_message(message.chat.id, mess)


bot.polling(non_stop=True)
