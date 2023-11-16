import requests
import telebot
from telebot import types
from googletrans import Translator


API_TOKEN = '6982326902:AAGvDA_BrxQAR2gA0izYRrj4PQWfhO-5bsU'
BUTTONS_ARRAY = ["Asos", "Farfetch", "FakeShop"]
ASOS_URL = "https://asos-com1.p.rapidapi.com/products/search"

bot = telebot.TeleBot(API_TOKEN)
translator = Translator()

user_brand_choices = {}
asos_parsed_response = {}

def get_asos_response(text):
    params = {'q': text}
    headers = {
        "X-RapidAPI-Key": "fa4b73644dmsh36518558185918cp130294jsnf1e2df226d96",
        "X-RapidAPI-Host": "asos-com1.p.rapidapi.com"
    }

    return requests.get(ASOS_URL, headers=headers, params=params).json()

def make_keyboard(buttons, row_width):
    keyboard = types.InlineKeyboardMarkup(row_width=row_width)
    keyboard.add(*[types.InlineKeyboardButton(text=btn, callback_data=btn) for btn in buttons])
    return keyboard

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_brand_choices[user_id] = []
    
    welcome_text = (
        "Привет. Это бот по подобру одежды с зарубежных маркетплейсов. "
        "Для начала выбери бренды, чьи товары ты бы хотел поискать"
    )
    keyboard = make_keyboard(BUTTONS_ARRAY, row_width=len(BUTTONS_ARRAY))
    bot.send_message(message.chat.id, welcome_text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data in BUTTONS_ARRAY)
def handle_callback(call):
    user_id = call.from_user.id
    user_choice = call.data
    
    if user_id not in user_brand_choices:
        user_brand_choices[user_id] = []

    user_brand_choices[user_id].append(user_choice)
    remaining_buttons = [brand for brand in BUTTONS_ARRAY if brand not in user_brand_choices[user_id]]
    
    new_text = f"Вы уже выбрали следующие бренды: {', '.join(user_brand_choices[user_id])}\n"
    if remaining_buttons:
        new_text += 'Вы можете также выбрать еще бренды или введите товар, который вы хотите найти'
    else:
        new_text += 'Вы выбрали все возможные бренды. Теперь введите товар, который вы хотите найти'
    
    if remaining_buttons:
        keyboard = make_keyboard(remaining_buttons, row_width=len(remaining_buttons))
        bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    else:
        bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id)

    bot.answer_callback_query(call.id)


def make_second_keyboard(current_index, photo_index):
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    images_sz = len(asos_parsed_response['id'][current_index]['additional_images']) + 1
    if current_index > 0:
        keyboard.add(types.InlineKeyboardButton(text='⬅️', callback_data=f'previous_image|{current_index}|{photo_index % images_sz}'))
    keyboard.add(types.InlineKeyboardButton(text='Показать еще фото', callback_data=f'next_photo|{current_index}|{photo_index % images_sz}'))
    if current_index < len(asos_parsed_response['id']) - 1:
        keyboard.add(types.InlineKeyboardButton(text='➡️', callback_data=f'next_image|{current_index}|{photo_index % images_sz}'))
    return keyboard


@bot.message_handler(content_types=['text'])
def handle_text(message):
    if 'Asos' in user_brand_choices[message.from_user.id]:
        translated_text = translator.translate(message.text, src='ru', dest='en').text
        print(translated_text)
        asos_response = get_asos_response(translated_text)
        asos_parsed_response['id'] = [
            {
                'id': item['id'],
                'image': item['imageUrl'],
                'price': item['price']['current']['text'],
                'name': item['name'],
                'additional_images': item['additionalImageUrls'],
                'url': 'asos.com/' + item['url'],
            }
            for item in asos_response['data']['products']
        ]
        keyboard = make_second_keyboard(0, 0)
        price = asos_parsed_response['id'][0]['price']
        name = asos_parsed_response['id'][0]['name']
        caption = f'{name}\nPrice is {price}'
        bot.send_photo(message.chat.id, asos_parsed_response['id'][0]['image'], caption=caption, reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, 'Пока доступен только Asos')


@bot.callback_query_handler(func=lambda call: call.data.split("|")[0] in ['next_image', 'previous_image', 'next_photo'])
def handle_callback(call):
    action, current_index, photo_index = call.data.split('|')
    current_index = int(current_index)
    photo_index = int(photo_index)
    additional_images = asos_parsed_response['id'][current_index]['additional_images']
    
    if action == 'next_image' and current_index < len(asos_parsed_response['id']) - 1:
        current_index += 1
        photo_index = 0
    elif action == 'previous_image' and current_index > 0:
        current_index -= 1
        photo_index = 0
    elif action == 'next_photo':
        photo_index = (photo_index + 1) % (len(additional_images) + 1)

    price = asos_parsed_response['id'][current_index]['price']
    name = asos_parsed_response['id'][current_index]['name']
    caption = f'{name}\nPrice is {price}'
    if photo_index == 0:
        media = asos_parsed_response['id'][current_index]['image']
    else:
        media = additional_images[photo_index - 1]
    keyboard = make_second_keyboard(current_index, photo_index)
    bot.edit_message_media(media=types.InputMedia(type='photo', media=media, caption=caption),
                           chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)
    bot.answer_callback_query(call.id)



bot.polling()


