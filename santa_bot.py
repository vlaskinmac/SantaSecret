import asyncio
import datetime
import logging
import os
import re
import time
import json
import random

from datetime import date, timedelta

from aiogram import types
from aiogram.dispatcher.filters import BoundFilter
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Text
from aiogram.types.message import ContentType
from aiogram.utils.exceptions import TelegramAPIError
import aiogram.utils.markdown as fmt

from dotenv import load_dotenv

load_dotenv()
token = os.getenv("TG_BOT_TOKEN")
loop = asyncio.get_event_loop()
bot = Bot(token=token, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage, loop=loop)
game_data = {}


class RegisterOrder(StatesGroup):
    game_id = State()
    user_name = State()
    user_email = State()
    user_wishlist = State()
    letter_to_santa = State()
    register_finish = State()


@dp.message_handler(commands='start')
@dp.message_handler(text='Отмена')
@dp.message_handler(Text(equals="Отмена"), state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    if message.text == 'Отмена':
        await state.finish()
    # if not message.text == '/start reg' or message.text == 'Отмена':
        # check if it is registration link
    msg = message.text
    msg_text = re.sub(r'\d+', "", str(msg))
        # await message.answer("Здравствуйте!")
    if not str(msg_text) == '/start reg' or str(msg_text) == 'Отмена':
        game_id = re.search('\d+$', message.text)

        # if game_id is not None:
        #     game_data['game_id'] = game_id.group()
        #     user_id = message['from']['id']
        #     game_data['user_id'] = user_id
        #     game = get_game(int(game_data["game_id"]))
        #
        #     await message.answer(f'Вы регистрируетесь на игру {game["name_game"]}')
        #     await RegisterOrder.user_name.set()
        #     await message.answer('Теперь укажите имя:')
        #     return

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(KeyboardButton('Создать игру'))
        await message.answer("Здравствуйте!", reply_markup=keyboard)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton(text='Регистрация'))
        await message.answer(

            fmt.text(
                fmt.text("Замечательно!\n\nТы собираешься участвовать в игре:\n\n"),
                fmt.text(f"Название игры:   {game_data['name_game']}\n"),
                fmt.text(f"\nЦеновой диапазон подарка:   {game_data['limit_price']}\n"),
                fmt.text(f"\nПериод регистрации участников:   {game_data['date_reg']}\n"),
                fmt.text(f"\nДата отправки подарков:   {game_data['date_send']}\n")
            ), reply_markup=keyboard

        )


@dp.message_handler(text='Создать игру')
async def create_game(message: types.Message):
    game_data['name_game'] = None
    await message.answer("Введите название игры")


@dp.callback_query_handler(text='yes')
async def yes_limit(call: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
    buttons = [
        types.InlineKeyboardButton(text='500 р', callback_data='500 p'),
        types.InlineKeyboardButton(text='500-1000 р', callback_data='500-1000 p'),
        types.InlineKeyboardButton(text='500-2000 р', callback_data='500-2000 p'),
    ]
    keyboard.row(*buttons)
    await call.message.answer("Выберите ценовой диапазон:", reply_markup=keyboard)
    await call.answer()


@dp.callback_query_handler(text_contains='p')
async def period_reg(call: types.CallbackQuery):
    if re.search(r'\d+', call.data):
        game_data['limit_price'] = call.data
    else:
        # Заменил на None в связи с проблемой кодировки русских символов в json
        game_data['limit_price'] = 'Нет ограничений'
    # keyboard = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    # buttons = [
    #     types.InlineKeyboardButton(text='до 25.12.2021', callback_data='25.12.2021q'),
    #     types.InlineKeyboardButton(text='до 31.12.2021', callback_data='31.12.2021q'),
    # ]
    # keyboard.row(*buttons)

    user_date = datetime.datetime.today()
    das = user_date + timedelta(weeks=4)
    count_date = das - user_date
    days = user_date + timedelta(days=count_date.days)
    keyboard = types.InlineKeyboardMarkup(row_width=4, resize_keyboard=True, one_time_keyboard=True)
    col = []
    for i in range(int(days.day) + 1):
        date_calendar = user_date + timedelta(days=i)
        col.append(datetime.date.strftime(date_calendar.date(), '%d.%m.%Y'))
    buttons = [
        types.InlineKeyboardButton(
            text=f'{day}',
            callback_data=f'{day}q') for day in col]
    keyboard.add(*buttons)
    await call.message.answer("Выберите период регистрации участников:", reply_markup=keyboard)
    await call.answer()


@dp.message_handler(text='Регистрация')
@dp.message_handler(Text(equals="Изменить имя"), state="*")
async def cmd_register(message: types.Message, state: FSMContext):
    try:
        game_id = game_data['game_id']
        date_send = game_data['date_send']
        date_reg = game_data['date_reg']
        user_id = str(message.from_user.id)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton(text='Отмена'))
        await state.update_data(date_send=date_send)
        await state.update_data(date_reg=date_reg)
        await state.update_data(game_id=game_id)
        await state.update_data(user_id=user_id)
        await RegisterOrder.user_name.set()
        await message.answer('Теперь укажите имя:', reply_markup=keyboard)
    except IndexError:
        await message.reply('Введите id игры.')
        await RegisterOrder.game_id.set()
    except ValueError:
        await message.answer('id игры должен быть целым числом')
        return


@dp.callback_query_handler(text_contains='q')
async def date_send(call: types.CallbackQuery):
    choice_date = re.sub(r'q', "", call.data)
    game_data['date_reg'] = choice_date
    day, month, year = choice_date.split(".")
    user_date = datetime.datetime(int(year), int(month), int(day))
    das = user_date + timedelta(weeks=4)
    count_date = das - user_date
    days = user_date + timedelta(days=count_date.days)
    keyboard = types.InlineKeyboardMarkup(row_width=4, resize_keyboard=True, one_time_keyboard=True)
    col = []
    for i in range(int(days.day) + 1):
        date_calendar = user_date + timedelta(days=i)
        col.append(datetime.date.strftime(date_calendar.date(), '%d.%m.%Y'))
    buttons = [
        types.InlineKeyboardButton(
            text=f'{day}',
            callback_data=f'{day}w') for day in col]
    keyboard.add(*buttons)
    await call.message.answer("Выберите дату отправки подарка:", reply_markup=keyboard)
    await call.answer()


@dp.callback_query_handler(text_contains='w')
async def logging_user(call: types.CallbackQuery):
    choice_day = re.sub(r'w', "", call.data)
    bot_name = await bot.get_me()
    game_data['date_send'] = choice_day
    await call.message.answer("Отлично! Тайный Санта уже готовится к раздаче подарков!",
                              reply_markup=types.ReplyKeyboardRemove())
    await call.message.answer(
        fmt.text(
            fmt.text("Перешлите ссылку новому участнику игры для регистрации:\n\n"),
            fmt.text(f'https://t.me/{bot_name.username}?start=reg{game_data["game_id"]}'),
        )
    )


def validate_email(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return bool(re.fullmatch(regex, email))


# def init_db():
#     if not os.path.isfile('users.json'):
#         users_db = {
#             'users': []
#         }
#         with open('users.json', 'w') as users:
#             json.dump(users_db, users, ensure_ascii=False, indent=3)

    # if not os.path.isfile('games.json'):
    #     game_db = {
    #         'games': []
    #     }
    #     with open('games.json', 'w') as games:
    #         json.dump(game_db, games, ensure_ascii=False, indent=3)


# def add_user(user):
#     try:
#         with open('users.json', 'r') as users:
#             users_db = json.load(users)
#             users_db['users'].append(user)
#
#         with open('users.json', 'w') as users:
#             json.dump(users_db, users, ensure_ascii=False, indent=3)
#     except:
#         init_db()


# def add_game(game):
#     try:
#         with open('games.json', 'r') as games:
#             games_db = json.load(games)
#             games_db['games'].append(game)
#         with open('games.json', 'w') as games:
#             json.dump(games_db, games, ensure_ascii=False, indent=3)
#     except:
#         init_db()


# def get_game(game_id):
#     print(game_id)
#     with open('games.json', 'r') as games:
#         games_db = json.load(games)
#         print()
#         for game in games_db['games']:
#             if game['game_id'] == game_id:
#                 return game
#         return None


@dp.message_handler(state=RegisterOrder.game_id)
async def get_game_id(message: types.Message, state: FSMContext):
    try:
        game_id = int(message.text)
        await state.update_data(game_id=game_id)
        await RegisterOrder.next()
    except ValueError:
        await message.answer('id игры должен быть целым числом')
        return


@dp.message_handler(Text(equals="Изменить email"), state="*")
async def go_to_email(message: types.Message):
    await RegisterOrder.user_email.set()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(text='Изменить имя'), KeyboardButton(text='Отмена'))
    await message.answer('Теперь укажите email:', reply_markup=keyboard)


@dp.message_handler(Text(equals="Изменить список желаний"), state="*")
async def go_to_wishlist(message: types.Message):
    await RegisterOrder.user_wishlist.set()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(text='Изменить email'), KeyboardButton(text='Отмена'))
    await message.answer(
        'Теперь укажите ваш список желаний (введите стоп, что бы продолжить дальше):', reply_markup=keyboard)


@dp.message_handler(Text(equals="Изменить письмо санте"), state="*")
async def go_to_santa_letter(message: types.Message):
    await RegisterOrder.letter_to_santa.set()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(text='Изменить список желаний'), KeyboardButton(text='Отмена'))
    await message.answer('Напишите письмо санте:', reply_markup=keyboard)


@dp.message_handler(state=RegisterOrder.user_name)
async def get_user_name(message: types.Message, state: FSMContext):
    user_name = message.text
    await state.update_data(user_name=user_name)
    await RegisterOrder.next()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(text='Изменить имя'), KeyboardButton(text='Отмена'))
    await message.answer('Теперь укажите email:', reply_markup=keyboard)


@dp.message_handler(state=RegisterOrder.user_email)
async def get_user_email(message: types.Message, state: FSMContext):
    user_email = message.text
    if not validate_email(user_email.strip()):
        await message.answer('Введите корректный email')
        return
    await state.update_data(user_email=user_email)
    await RegisterOrder.next()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(text='Изменить email'), KeyboardButton(text='Отмена'))
    await message.answer(
        'Теперь укажите ваш список желаний:', reply_markup=keyboard)


@dp.message_handler(state=RegisterOrder.user_wishlist)
async def get_user_wishlist(message: types.Message, state: FSMContext):
    user_wishlist = message.text
    await state.update_data(user_wishlist=user_wishlist)
    await RegisterOrder.next()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(text='Изменить список желаний'), KeyboardButton(text='Отмена'))
    await message.answer('Напишите письмо санте:', reply_markup=keyboard)


@dp.message_handler(state=RegisterOrder.letter_to_santa)
async def write_letter_to_santa(message: types.Message, state: FSMContext):
    letter = message.text
    await state.update_data(letter_to_santa=letter)

    await RegisterOrder.next()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(
        KeyboardButton(text='Отправить письмо санте!', callback_data='register_finish'),
        KeyboardButton(text='Изменить письмо санте'),
        KeyboardButton(text='Отмена')
    )
    await message.answer('🎅', reply_markup=keyboard)


@dp.message_handler(state=RegisterOrder.register_finish)
async def register_finish(message: types.Message, state: FSMContext):
    # game_db = {
    #     'games': []
    # }
    # with open('games.json', 'a+') as file:
    #     json.dump(game_db, file, ensure_ascii=False, indent=3)

    try:
        with open('games.json') as f:
            file_data = json.load(f)
            file_data.append(game_data)
        with open('games.json', 'w') as file:
            json.dump(file_data, file, ensure_ascii=False, default=str, indent=3)
    except:
        games = []
        games.append(game_data)
        with open('games.json', 'a+') as file:
            json.dump(games, file, ensure_ascii=False, default=str, indent=3)
    if message.text == 'Отправить письмо санте!':
        user_data = await state.get_data()
        try:
            with open('users.json') as f:
                file_data = json.load(f)
                file_data.append(user_data)
            with open('users.json', 'w') as file:
                json.dump(file_data, file, ensure_ascii=False, default=str, indent=3)
        except:
            users = []
            users.append(user_data)
            with open('users.json', 'a+') as file:
                json.dump(users, file, ensure_ascii=False, default=str, indent=3)

        await state.finish()
        keyboard = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        buttons = [
            types.InlineKeyboardButton(text='Посмотреть список желаний:', callback_data='Посмотреть список желаний:'),
        ]
        keyboard.row(*buttons)
        await message.answer('Посмотрите список участников и желаемые подарки!', reply_markup=keyboard)


@dp.callback_query_handler(text='Посмотреть список желаний:')
async def random_choice(call: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons = [
        types.InlineKeyboardButton(text='Посмотреть список желаний участников!', callback_data='список')
    ]
    keyboard.row(*buttons)
    await call.message.answer(f'Превосходно, ты в игре! {game_data["date_reg"]} мы проведем жеребьевку'
                              f' и ты узнаешь имя и контакты своего тайного друга. Ему и нужно будет подарить подарок!')
    await call.answer()
    participants_of_game = []
    with open('games.json', 'r') as games:
        games_db = json.load(games)
    with open('users.json', 'r') as users:
        users_d = json.load(users)
    for user in users_d:
        for game in games_db:
            if user['game_id'] == game['game_id'] and user['date_reg'] == game['date_reg']:
                if user['date_reg'] == game_data['date_reg']:
                    participants_of_game.append([user['user_id'], user['user_name'], user['user_wishlist']])
    for wish in participants_of_game:
        await call.message.answer(f"Игрок: {wish[1]} желает получить:\n\n{wish[2]}")



    user_date_1 = datetime.datetime.today() + timedelta(minutes=1)


    flag_1 = 0
    stop_send_2 = 0
    stop_send_1 = 0
    while True:
        date_today = datetime.datetime.today()

        # if user_date_1.date() == date_today.date():
        time.sleep(10)
        if user_date_1 < date_today:
            # users_1 = [2021, 12, 31, 12, 00, 00]
            print(len(participants_of_game_1)-1)
            print(participants_of_game_1)

            # while flag_1 <= len(participants_of_game_1):
            #     flag_1 += 1

                # if stop_send < flag_1:
            for user_id in participants_of_game_1:
                stop_send_1 += 1
                if stop_send_1 > len(participants_of_game_1) - 1:
                    print('stop')
                    break
                await asyncio.sleep(1)
                await bot.send_message(user_id[0], 'Игра началась!')
                print(stop_send_1,'---')

            # if stop_send == len(participants_of_game_1):
            #     print(stop_send, len(participants_of_game_1))
            #     break

        print(1, date_today)
        # if user_date_2.date() == date_today.date():

        if user_date_2 < date_today:
            # users_1 = [2021, 12, 31, 12, 00, 00]
            print(len(participants_of_game_2) - 1)
            print(participants_of_game_2)

            # while flag_1 <= len(participants_of_game_2):
            #     flag_1 += 1

            # if stop_send < flag_1:
            for user_id in participants_of_game_2:
                stop_send_2 += 1
                if stop_send_2 > len(participants_of_game_2) - 1:
                    print('stop')
                    break
                await asyncio.sleep(1)
                await bot.send_message(user_id[0], 'Игра началась!')
                print(stop_send_2, '---')
        # await bot.send_message(user_id, 'end')





# !! it`s final handler____________________________________________________________


# @dp.message_handler()
# async def random_choice(message: types.Message):
#     await message.answer('Вы зарегистрированы на игру. Ожидайте сообщения о начале игры!')
#     user_date1 = datetime.datetime(2021, 12, 17, 14, 50, 30)
#     user_date2 = datetime.datetime(2021, 12, 17, 14, 50, 30)
#
#     while True:
#         date_today = datetime.datetime.today()
#         if user_date1 < date_today:
#             colleagues = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
#             random.shuffle(colleagues)
#             offset = [colleagues[-1]] + colleagues[:-1]
#             for santa, receiver in zip(colleagues, offset):
#                 print(santa, "Дарит подарок", receiver)
#             await bot.send_message(message.from_user.id, 'Начинаем!')
#             break
#         if user_date2 < date_today:
#             colleagues = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
#             random.shuffle(colleagues)
#             offset = [colleagues[-1]] + colleagues[:-1]
#             for santa, receiver in zip(colleagues, offset):
#                 print(santa, "Дарит подарок", receiver)
#             await bot.send_message(message.from_user.id, 'Начинаем!')
#             break


# @dp.message_handler(text='Начинаем!')
# async def random_choice(message: types.Message):
#     if message.text == 'Начинаем!':
#         for user in users:
#                 await message.answer(
#                     fmt.text(
#                     fmt.text("Жеребьевка в игре “Тайный Санта” проведена! Спешу сообщить кто тебе выпал:\n\n"),
#                     fmt.text(f'Имя:{bot_name.username}'),
#                     fmt.text(f'Email:{bot_name.username}'),
#                     fmt.text(f'Письмо Санте:{bot_name.username}'),
#                     fmt.text(f'Wish list:{bot_name.username}'),
#
#                 )
#                 )


@dp.message_handler()
async def name_game(message: types.Message):
    if not game_data['name_game']:
        game_data['name_game'] = message.text
        game_data['game_id'] = random.randint(0, 200)
        await bot.delete_message(message.from_user.id, message.message_id)
        keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
        button_yes = types.InlineKeyboardButton(text='ДА', callback_data='yes')
        button_no = types.InlineKeyboardButton(text='НЕТ', callback_data='pp')
        keyboard.add(button_yes, button_no)
        await message.answer(f"Для игры - {game_data['name_game']}\n\nТребуется ограничение стоимости подарка?",
                             reply_markup=keyboard)


# if __name__ == '__main__':
#     init_db()
#     executor.start_polling(dp, skip_updates=True)
#
#
# date_today = datetime.datetime.today() + timedelta(seconds=10)
# print(datetime.datetime.today())


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)


# x = '25.12.2021'
# day, month, year = x.split(".")
# user_date = datetime.datetime(int(year), int(month), int(day))
# datetime_object = datetime.datetime.strptime(x, '%d.%m.%Y')
# das = user_date + timedelta(weeks=4)
# count_date = das - user_date
# days = user_date + timedelta(days=count_date.days)
# date_test= user_date.date()
# date1 = datetime.date.strftime(date_test, '%Y-%m-%d')
# date2 = datetime.date.strftime(date_test, '%d.%m.%Y')







# with open('games.json', 'r') as games:
#     games_db = json.load(games)
# with open('users.json', 'r') as users:
#     users_d = json.load(users)
# g = None
# m = None
# for user in users_d:
#     for game in games_db:


            # if user['game_id'] == game['game_id'] and user['date_send'] == game['date_send']:
            #     if user['date_send'] == first_date:
            #         m = user['user_id']
            #         g = 1
            #         participants_of_game_1.append([user['user_id'], user['user_name'], user['user_wishlist']])
            #     if user['date_send'] == second_date:
            #         m = user['user_id']
            #         participants_of_game_2.append([user['user_id'], user['user_name'], user['user_wishlist']])




# for wishlist in users_db.values():
#     for wish in wishlist:
#         print(wish)
#         x.append([wish['user_name'], wish['user_wishlist']])
#     print(x)
# for i in x:
#     print(i[0])

#
# user_date = datetime.datetime(2021, 12, 31, 15, 39, 00)
# # user_date = datetime.datetime(2021, 12, 17, 14, 46, 00)
# print(user_date)
# date_today = datetime.datetime.today() + timedelta(seconds=10)
# print(date_today)
# count_date = date_today - user_date