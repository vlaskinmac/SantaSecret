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


@dp.message_handler(commands='start')
@dp.message_handler(text='Отмена')
@dp.message_handler(Text(equals="Отмена"), state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    if message.text == 'Отмена':
        await state.finish()
    if not message.text == '/start reg' or message.text == 'Отмена':
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton('Создать игру'))
        await bot.delete_message(message.from_user.id, message.message_id)
        trud = await message.answer("Здравствуйте!", reply_markup=keyboard)
        await asyncio.sleep(10)
        await message.bot.delete_message(chat_id=trud.chat.id, message_id=trud.message_id)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton(text='Регистрация'))
        await message.answer(

            fmt.text(
                fmt.text("Замечательно!\n\nТы собираешься участвовать в игре:\n\n"),
                fmt.text(f"Название игры:   {game_data['name_game'].upper()}\n"),
                fmt.text(f"\nЦеновой диапазон подарка:   {game_data['limit_price']}\n"),
                fmt.text(f"\nПериод регистрации участников:   {game_data['date_reg']}\n"),
                fmt.text(f"\nДата отправки подарков:   {game_data['date_send']}\n")
            ), reply_markup=keyboard

        )


@dp.message_handler(text='Создать игру')
async def create_game(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(' '))
    trud = await message.answer("Введите название игры", reply_markup=types.ReplyKeyboardRemove())
    await bot.delete_message(message.from_user.id, message.message_id)
    await asyncio.sleep(5)
    await message.bot.delete_message(chat_id=trud.chat.id, message_id=trud.message_id)


@dp.callback_query_handler(text='yes')
async def yes_limit(call: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
    buttons = [
        types.InlineKeyboardButton(text='500 р', callback_data='500 p'),
        types.InlineKeyboardButton(text='500-1000 р', callback_data='500-1000 p'),
        types.InlineKeyboardButton(text='500-2000 р', callback_data='500-2000 p'),
    ]
    keyboard.row(*buttons)
    await bot.delete_message(call.from_user.id, call.message.message_id)
    await call.message.answer("Выберите ценовой диапазон:", reply_markup=keyboard)
    await call.answer()


@dp.callback_query_handler(text_contains='p')
async def period_reg(call: types.CallbackQuery):
    if re.search(r'\d+', call.data):
        game_data['limit_price'] = call.data
    else:
        game_data['limit_price'] = "Нет ограничений!"
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons = [
        types.InlineKeyboardButton(text='до 25.12.2021', callback_data='25.12.2021'),
        types.InlineKeyboardButton(text='до 31.12.2021', callback_data='31.12.2021'),
    ]
    keyboard.row(*buttons)
    await bot.delete_message(call.from_user.id, call.message.message_id)
    await call.message.answer("Выберите период регистрации участников до 12.00 МСК:", reply_markup=keyboard)
    await call.answer()


@dp.callback_query_handler(text_contains='2021')
async def date_send(call: types.CallbackQuery):
    game_data['date_reg'] = call.data
    user_date = datetime.datetime(2021, 12, 31)
    date_today = datetime.datetime.today()
    count_date = date_today - user_date
    days = int(count_date.days * -1)
    keyboard = types.InlineKeyboardMarkup(row_width=4, resize_keyboard=True, one_time_keyboard=True)
    col = []
    for i in range(days + 1):
        date_calendar = date_today + timedelta(days=i)
        col.append(date_calendar.day)
    buttons = [
        types.InlineKeyboardButton(
            text=f'{day}',
            callback_data=f'{day}w') for day in col]
    keyboard.add(*buttons)
    await call.message.answer("Выберите дату отправки подарка:", reply_markup=keyboard)
    await call.answer()
    await bot.delete_message(call.from_user.id, call.message.message_id)


@dp.callback_query_handler(text_contains='w')
async def logging_user(call: types.CallbackQuery):
    choice_day = re.search(r'\d+', call.data).group()
    date_today = datetime.date.today()
    bot_name = await bot.get_me()
    game_data['date_send'] = f'{choice_day}.{date_today.month}.{date_today.year}'
    await bot.delete_message(call.from_user.id, call.message.message_id)
    await call.message.answer("Отлично! Тайный Санта уже готовится к раздаче подарков!",
                              reply_markup=types.ReplyKeyboardRemove())
    await call.message.answer(
        fmt.text(
            fmt.text("Перешлите ссылку новому участнику игры для регистрации:\n\n"),
            fmt.text(f'https://t.me/{bot_name.username}?start=reg'),
        )
    )


def validate_email(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return bool(re.fullmatch(regex, email))


def init_db():
    if not os.path.isfile('users.json'):
        users_db = {
            'users': []
        }
        with open('users.json', 'w') as users:
            json.dump(users_db, users)


def add_user(user):
    with open('users.json', 'r') as users:
        users_db = json.load(users)
        print(users_db)
        users_db['users'].append(user)
        print(users_db)


@dp.message_handler(Text(equals="Изменить имя"), state="*")
@dp.message_handler(text='Регистрация')
async def cmd_register(message: types.Message, state: FSMContext):
    try:
        game_id = game_data['game_id']
        user_id = message['from']['id']
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton(text='Отмена'))
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
@dp.message_handler(state=RegisterOrder.user_name)
async def get_user_name(message: types.Message, state: FSMContext):
    user_name = message.text
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(text='Изменить имя'), KeyboardButton(text='Отмена'))
    await state.update_data(user_name=user_name)
    await RegisterOrder.next()
    await message.answer('Теперь укажите email:', reply_markup=keyboard)


@dp.message_handler(Text(equals="Изменить список желаний"), state="*")
@dp.message_handler(state=RegisterOrder.user_email)
async def get_user_email(message: types.Message, state: FSMContext):
    user_email = message.text
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(text='Изменить email'), KeyboardButton(text='Отмена'))
    if not validate_email(user_email.strip()):
        await message.answer('Введите корректный email')
        return
    await state.update_data(user_email=user_email)
    await RegisterOrder.next()
    await message.answer(
        'Теперь укажите ваш список желаний (введите стоп, что бы продолжить дальше):', reply_markup=keyboard)


@dp.message_handler(Text(equals="Изменить письмо санте"), state="*")
@dp.message_handler(state=RegisterOrder.user_wishlist)
async def get_user_wishlist(message: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(text='Изменить список желаний'), KeyboardButton(text='Отмена'))
    user_wishlist = message.text
    await state.update_data(user_wishlist=user_wishlist)
    await RegisterOrder.next()
    await message.answer('Напишите письмо санте:', reply_markup=keyboard)


@dp.message_handler(state=RegisterOrder.letter_to_santa)
async def write_letter_to_santa(message: types.Message, state: FSMContext):
    letter = message.text
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(text='Отправить письмо санте!'), KeyboardButton(text='Отмена'))
    await state.update_data(letter_to_santa=letter)
    user_data = await state.get_data()
    add_user(user_data)
    await state.finish()
    await message.answer('🎅', reply_markup=keyboard)


@dp.message_handler(text='Отправить письмо санте!')
async def wish_sheet(message: types.Message):
    await message.answer('Вы зарегистрированы на игру. Ожидайте сообщения о начале игры!')
    # for wish in data["wish"]:
    #     await call.message.answer(
    #         fmt.text(
    #             fmt.text(wish["user"]),
    #             fmt.text(wish["user"]),
    #             fmt.text(wish["user"]),
    #         ), reply_markup=types.ReplyKeyboardRemove()
    #     )

# !! it`s final handler____________________________________________________________


@dp.message_handler()
async def name_game(message: types.Message):
    game_data['name_game'] = message.text
    game_data['game_id'] = random.randint(0, 200)

    await bot.delete_message(message.from_user.id, message.message_id)
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
    button_yes = types.InlineKeyboardButton(text='ДА', callback_data='yes')
    button_no = types.InlineKeyboardButton(text='НЕТ', callback_data='pp')
    keyboard.add(button_yes, button_no)
    await message.answer(f"Для игры - {game_data['name_game'].upper()}\n\nТребуется ограничение стоимости подарка?",
                         reply_markup=keyboard)


if __name__ == '__main__':
    init_db()
    executor.start_polling(dp, skip_updates=True)
