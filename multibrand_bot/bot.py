import random
import requests
import telebot
from telebot import types
from pycbrf import ExchangeRates
from googletrans import Translator


API_TOKEN = "6982326902:AAGvDA_BrxQAR2gA0izYRrj4PQWfhO-5bsU"
BUTTONS_ARRAY = ["Asos", "Forever 21"]
BASKET_BUTTON = "Перейти в корзину"
ASOS_URL = "https://asos-com1.p.rapidapi.com/products/search"
FOREVER21_URL = "https://apidojo-forever21-v1.p.rapidapi.com/products/search"

bot = telebot.TeleBot(API_TOKEN)
translator = Translator()
currency_rate = ExchangeRates()

BASKET_LIST = dict()

user_brand_choices = {}
parsed_response = {}


def request_to_asos(text):
    params = {"q": text}
    headers = {
        "X-RapidAPI-Key": "fa4b73644dmsh36518558185918cp130294jsnf1e2df226d96",
        "X-RapidAPI-Host": "asos-com1.p.rapidapi.com",
    }
    try:
        asos_response = requests.get(ASOS_URL, headers=headers, params=params).json()

        if "id" not in parsed_response:
            parsed_response["id"] = []

        for item in asos_response["data"]["products"]:
            parsed_response["id"].append(
                {
                    "id": item["id"],
                    "shop": "asos",
                    "image": item["imageUrl"],
                    "price": item["price"]["current"]["text"],
                    "name": item["name"],
                    "additional_images": item["additionalImageUrls"],
                    "url": "asos.com/" + item["url"],
                }
            )
    except Exception:
        print("asos error")
        pass


def request_to_forever(text):
    params = {"query": text, "rows": 50, "start": 0}
    headers = {
        "X-RapidAPI-Key": "fa4b73644dmsh36518558185918cp130294jsnf1e2df226d96",
        "X-RapidAPI-Host": "apidojo-forever21-v1.p.rapidapi.com",
    }
    try:
        forever_response = requests.get(
            FOREVER21_URL, headers=headers, params=params
        ).json()

        if "id" not in parsed_response:
            parsed_response["id"] = []

        for item in forever_response["response"]["docs"]:
            parsed_response["id"].append(
                {
                    "id": item["pid"],
                    "shop": "forever 21",
                    "image": item["thumb_image"],
                    "price": item["sale_price"]
                    if "sale_price" in item
                    else item["price"],
                    "name": item["title"],
                    "additional_images": [],
                    "url": item["url"],
                }
            )
    except Exception:
        pass


def make_keyboard(groups_of_buttons):
    keyboard = types.InlineKeyboardMarkup(
        row_width=max(list(map(lambda x: len(x), groups_of_buttons)))
    )
    for group_of_buttons in groups_of_buttons:
        keyboard.add(
            *[
                types.InlineKeyboardButton(text=btn, callback_data=btn)
                for btn in group_of_buttons
            ]
        )
    keyboard.add(
        types.InlineKeyboardButton(text=BASKET_BUTTON, callback_data="go_to_cart")
    )
    return keyboard


@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_id = message.from_user.id
    user_brand_choices[user_id] = []

    welcome_text = (
        "Привет. Это бот по подобру одежды с зарубежных маркетплейсов. "
        "Для начала выбери маркетплейсы, где ты хотел бы поискать товары"
    )
    keyboard = make_keyboard([BUTTONS_ARRAY])
    bot.send_message(message.chat.id, welcome_text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data in BUTTONS_ARRAY)
def handle_callback(call):
    user_id = call.from_user.id
    user_choice = call.data

    if user_id not in user_brand_choices:
        user_brand_choices[user_id] = []

    user_brand_choices[user_id].append(user_choice)
    remaining_buttons = [
        brand for brand in BUTTONS_ARRAY if brand not in user_brand_choices[user_id]
    ]

    new_text = f"Вы уже выбрали следующие маркетплейсы: {', '.join(user_brand_choices[user_id])}\n"
    if remaining_buttons:
        new_text += "Вы можете также выбрать еще маркетплейсы или введите товар, который вы хотите найти"
    else:
        new_text += "Вы выбрали все возможные маркетплейсы. Теперь введите товар, который вы хотите найти"

    if remaining_buttons:
        keyboard = make_keyboard([remaining_buttons])
        bot.edit_message_text(
            new_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
        )
    else:
        bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id)

    bot.answer_callback_query(call.id)


def make_second_keyboard(current_index, photo_index):
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    images_sz = len(parsed_response["id"][current_index]["additional_images"]) + 1
    if current_index > 0:
        keyboard.add(
            types.InlineKeyboardButton(
                text="⬅️",
                callback_data=f"previous_image|{current_index}|{photo_index % images_sz}",
            )
        )
    if images_sz > 1:
        keyboard.add(
            types.InlineKeyboardButton(
                text="Показать еще фото",
                callback_data=f"next_photo|{current_index}|{photo_index % images_sz}",
            )
        )
    if current_index < len(parsed_response["id"]) - 1:
        keyboard.add(
            types.InlineKeyboardButton(
                text="➡️",
                callback_data=f"next_image|{current_index}|{photo_index % images_sz}",
            )
        )
    if parsed_response["id"][current_index]["name"] in BASKET_LIST.keys():
        keyboard.add(
            types.InlineKeyboardButton(
                text="Удалить из корзины",
                callback_data=f"drop_from_cart|{current_index}|{photo_index % images_sz}",
            )
        )
    else:
        keyboard.add(
            types.InlineKeyboardButton(
                text="Добавить в корзину",
                callback_data=f"add_to_cart|{current_index}|{photo_index % images_sz}",
            )
        )
    keyboard.add(
        types.InlineKeyboardButton(
            text=BASKET_BUTTON,
            callback_data=f"go_to_cart|{current_index}|{photo_index % images_sz}",
        )
    )
    return keyboard


@bot.message_handler(content_types=["text"])
def handle_text(message):
    print(message.text)
    translated_text = translator.translate(message.text, src="ru", dest="en").text
    print(translated_text)
    if "Asos" in user_brand_choices[message.from_user.id]:
        request_to_asos(translated_text)
    if "Forever 21" in user_brand_choices[message.from_user.id]:
        request_to_forever(translated_text)
    random.shuffle(parsed_response["id"])
    keyboard = make_second_keyboard(0, 0)
    price = parsed_response["id"][0]["price"]
    name = parsed_response["id"][0]["name"]
    shop = parsed_response["id"][0]["shop"]
    caption = f"{name}\nPrice is {price}\nShop is {shop}"
    bot.send_photo(
        message.chat.id,
        parsed_response["id"][0]["image"],
        caption=caption,
        reply_markup=keyboard,
    )


@bot.callback_query_handler(
    func=lambda call: call.data.split("|")[0]
    in ["next_image", "previous_image", "next_photo"]
)
def handle_callback(call):
    action, current_index, photo_index = call.data.split("|")
    current_index = int(current_index)
    photo_index = int(photo_index)
    additional_images = parsed_response["id"][current_index]["additional_images"]

    if action == "next_image" and current_index < len(parsed_response["id"]) - 1:
        current_index += 1
        photo_index = 0
    elif action == "previous_image" and current_index > 0:
        current_index -= 1
        photo_index = 0
    elif action == "next_photo":
        photo_index = (photo_index + 1) % (len(additional_images) + 1)

    price = parsed_response["id"][current_index]["price"]
    name = parsed_response["id"][current_index]["name"]
    shop = parsed_response["id"][current_index]["shop"]
    caption = f"{name}\nPrice is {price}\nShop is {shop}"
    if photo_index == 0:
        media = parsed_response["id"][current_index]["image"]
    else:
        media = additional_images[photo_index - 1]
    keyboard = make_second_keyboard(current_index, photo_index)
    bot.edit_message_media(
        media=types.InputMedia(type="photo", media=media, caption=caption),
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard,
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.split("|")[0] == "add_to_cart")
def handle_callback(call):
    current_index = int(call.data.split("|")[1])
    photo_index = int(call.data.split("|")[2])
    additional_images = parsed_response["id"][current_index]["additional_images"]
    if photo_index == 0:
        media = parsed_response["id"][current_index]["image"]
    else:
        media = additional_images[photo_index - 1]
    product_card = dict()
    price = parsed_response["id"][current_index]["price"]
    name = parsed_response["id"][current_index]["name"]
    shop = parsed_response["id"][current_index]["shop"]
    caption = f"{name}\nPrice is {price}\nShop is {shop}"
    product_card["price"] = price
    product_card["name"] = name
    product_card["shop"] = shop
    product_card["caption"] = caption
    product_card["media"] = media
    BASKET_LIST[name] = product_card
    keyboard = make_second_keyboard(current_index, photo_index)
    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard,
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(
    func=lambda call: call.data.split("|")[0] == "drop_from_cart"
)
def handle_callback(call):
    current_index = int(call.data.split("|")[1])
    photo_index = int(call.data.split("|")[2])
    BASKET_LIST.pop(parsed_response["id"][current_index]["name"])
    keyboard = make_second_keyboard(current_index, photo_index)
    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard,
    )
    bot.answer_callback_query(call.id)


def calc_final_price():
    final_price = 0
    for _, value in BASKET_LIST.items():
        final_price += float(value["price"][1:])
    final_price_in_rub = int(float(currency_rate["USD"].value) * final_price)
    return final_price_in_rub


@bot.callback_query_handler(func=lambda call: call.data.split("|")[0] == "go_to_cart")
def handle_callback(call):
    print("go_to_cart callback")
    if len(BASKET_LIST.items()) == 0:
        remaining_buttons = [
            brand
            for brand in BUTTONS_ARRAY
            if brand not in user_brand_choices[call.from_user.id]
        ]
        keyboard = make_keyboard([remaining_buttons])
        bot.send_message(
            call.message.chat.id,
            "Ваша корзина пуста. Выберите интересующие вас маркетплейсы для поиска товаров.",
            reply_markup=keyboard,
        )
        return

    final_price_in_rub = calc_final_price()
    items_size = len(BASKET_LIST.items())

    current_index = int(call.data.split("|")[1])
    photo_index = int(call.data.split("|")[2])
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    images_sz = len(parsed_response["id"][current_index]["additional_images"]) + 1
    keyboard.add(
        types.InlineKeyboardButton(
            text="Вернуться к товарам",
            callback_data=f"back_to_items|{current_index}|{photo_index % images_sz}",
        )
    )
    keyboard.add(
        types.InlineKeyboardButton(
            text="Оплатить заказ", callback_data=f"pay|{final_price_in_rub}"
        )
    )
    msg = bot.send_message(
        call.message.chat.id,
        f"Вы выбрали {items_size} товаров на общую сумму {final_price_in_rub} рублей",
        reply_markup=keyboard,
    )

    i = 0
    for key, value in BASKET_LIST.items():
        print(key)
        print(len(key.encode('utf-8')))
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton(
                text="Удалить из корзины",
                callback_data=f"drop_from_cart_in_cart|{i}|{msg.message_id}",
            )
        )
        bot.send_photo(call.message.chat.id, value["media"], caption=value["caption"], reply_markup=keyboard)
        i += 1

@bot.callback_query_handler(
    func=lambda call: call.data.split("|")[0] == "drop_from_cart_in_cart"
)
def handle_callback(call):
    BASKET_LIST.pop(list(BASKET_LIST.keys())[int(call.data.split("|")[1])])
    bot.delete_message(
    chat_id=call.message.chat.id,
    message_id=call.message.message_id,
    )
    if len(BASKET_LIST.items()) != 0:
        bot.edit_message_text(f"Вы выбрали {len(BASKET_LIST.items())} товаров на общую сумму {calc_final_price()} рублей", call.message.chat.id, int(call.data.split("|")[2]))
    else:
        bot.edit_message_text(f"Ваша корзина пуста. Выберите интересующие вас маркетплейсы для поиска товаров.", call.message.chat.id, int(call.data.split("|")[2]))
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(
    func=lambda call: call.data.split("|")[0] == "back_to_items"
)
def handle_callback(call):
    current_index = int(call.data.split("|")[1])
    photo_index = int(call.data.split("|")[2])
    keyboard = make_second_keyboard(current_index, photo_index)

    price = parsed_response["id"][current_index]["price"]
    name = parsed_response["id"][current_index]["name"]
    shop = parsed_response["id"][current_index]["shop"]
    caption = f"{name}\nPrice is {price}\nShop is {shop}"
    additional_images = parsed_response["id"][current_index]["additional_images"]
    if photo_index == 0:
        media = parsed_response["id"][current_index]["image"]
    else:
        media = additional_images[photo_index - 1]

    bot.send_photo(call.message.chat.id, media, caption=caption, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.split("|")[0] == "pay")
def handle_callback(call):
    price = int(call.data.split("|")[1])

    # bot.send_invoice(
    #    chat_id=call.message.chat.id,
    #    title='Товар',
    #    description='Выбранные товары MULTIBRAND',
    #    invoice_payload='TEST_PAYLOAD',
    #    provider_token='TEST_TOKEN',
    #    currency='USD',
    #    photo_url=None,
    #    photo_size=None,
    #    photo_width=None,
    #    photo_height=None,
    #    is_flexible=False,
    #    prices=[types.LabeledPrice(label='Товар', amount=int(price * 100))]
    # )
    bot.send_message(call.message.chat.id, "Спасибо за оплату!")
    BASKET_LIST.clear()


@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout_query(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@bot.message_handler(content_types=["successful_payment"])
def process_successful_payment(message):
    bot.send_message(message.chat_id, "Спасибо за оплату!")


bot.polling()
