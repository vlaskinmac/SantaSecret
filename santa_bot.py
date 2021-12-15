import asyncio
import datetime
import logging
import os
import re
import time
import json

from datetime import date, timedelta

from aiogram import types
from aiogram.dispatcher.filters import BoundFilter
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types.message import ContentType
from aiogram.utils.exceptions import TelegramAPIError
import aiogram.utils.markdown as fmt

from dotenv import load_dotenv


load_dotenv()
token = os.getenv("BOT_KEY")
loop = asyncio.get_event_loop()
bot = Bot(token=token, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage, loop=loop)
game_data = {}


class IsAdminFilter(BoundFilter):
    chat_id = 1015193447
    key = "is_admin"

    def __init__(self, is_admin):
        self.is_admin = is_admin

    async def check(self, call: types.CallbackQuery):
        member = await call.bot.get_chat_member(call.message.chat.id, call.from_user.id)
        return member.is_chat_admin()


dp.filters_factory.bind(IsAdminFilter)


@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton('Создать игру'))
    await message.answer("Здравствуйте!", reply_markup=keyboard)

    await bot.delete_message(message.from_user.id, message.message_id)


@dp.message_handler(text='Создать игру')
async def create_game(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(' '))
    await message.answer("Введите название игры", reply_markup=types.ReplyKeyboardRemove())
    await bot.delete_message(message.from_user.id, message.message_id)


@dp.message_handler()
async def name_game(message: types.Message):
    game_data['name_game'] = message.text
    await bot.delete_message(message.from_user.id, message.message_id)
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
    button_yes = types.InlineKeyboardButton(text='ДА', callback_data='yes')
    button_no = types.InlineKeyboardButton(text='НЕТ', callback_data='limit')
    keyboard.add(button_yes, button_no)
    await message.answer(f"Для игры - {game_data['name_game'].upper()}\n\nТребуется ограничение стоимости подарка?",
                         reply_markup=keyboard)


@dp.callback_query_handler(text='yes')
async def yes_limit(call: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
    buttons = [
        types.InlineKeyboardButton(text='500 р', callback_data='limit-1'),
        types.InlineKeyboardButton(text='500-1000 р', callback_data='limit-2'),
        types.InlineKeyboardButton(text='500-2000 р', callback_data='limit-3'),
    ]
    keyboard.row(*buttons)
    await bot.delete_message(call.from_user.id, call.message.message_id)
    await call.message.answer("Выберите ценовой диапазон:", reply_markup=keyboard)


@dp.callback_query_handler(text_contains='limit')
async def period_reg(call: types.CallbackQuery):
    game_data['limit_price'] = call.data

    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons = [
        types.InlineKeyboardButton(text='до 25.12.2021', callback_data='date-1'),
        types.InlineKeyboardButton(text='до 31.12.2021', callback_data='date-2'),
    ]
    keyboard.row(*buttons)
    await bot.delete_message(call.from_user.id, call.message.message_id)
    await call.message.answer("Выберите период регистрации участников до 12.00 МСК:", reply_markup=keyboard)
    await call.answer()


@dp.callback_query_handler(text_contains='date')
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
            callback_data=f'{day}w')for day in col]
    keyboard.add(*buttons)
    await call.message.answer("Выберите дату отправки подарка:", reply_markup=keyboard)
    await call.answer()
    await bot.delete_message(call.from_user.id, call.message.message_id)


# @dp.callback_query_handler(is_admin=True,text_contains='w')
# @dp.callback_query_handler(text_contains='w')
# async def link(call: types.CallbackQuery):
    # chat_id = 1015193447
    # expire_date = datetime.datetime.today() + timedelta(days=1)
    # link = await bot.create_chat_invite_link(chat_id)
    # await bot.delete_message(call.from_user.id, call.message.message_id)
    # await call.message.answer("Сформировали ссылку\n\nОтлично, Тайный Санта уже готовится к раздаче подарков!")
    # await bot.send_message(call.from_user.id, link.invite_link, call.message.message_id)


@dp.callback_query_handler(text_contains='w')
async def logging_user(call: types.CallbackQuery):
    game_data['date_send'] = call.data
    # chat_id = 1015193447
    # expire_date = datetime.datetime.today() + timedelta(days=1)
    # link = await bot.create_chat_invite_link(chat_id)
    # await bot.delete_message(call.from_user.id, call.message.message_id)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton('Регистрация'))
    await bot.delete_message(call.from_user.id, call.message.message_id)
    await call.message.answer("Сформировали ссылку\n\nОтлично, Тайный Санта уже готовится к раздаче подарков!",
                              reply_markup=keyboard)
    await call.message.answer(
                fmt.text(
                    fmt.text(fmt.hunderline("Замечательно!\nТы собираешься участвовать в игре:\n\n")),
                    fmt.text(f"Название игры:   {game_data['name_game'].upper()}\n"),
                    fmt.text(f"\nЦеновой диапазон подарка:   {game_data['limit_price']}\n"),
                    fmt.text(f"\nПериод регистрации участников:   {game_data['date_reg']}\n"),
                    fmt.text(f"\nДата отправки подарков:   {game_data['date_send']}\n")
                )
    )


@dp.callback_query_handler(text='Регистрация')
async def logger(call: types.CallbackQuery):
    await bot.delete_message(call.from_user.id, call.message.message_id)
    await call.message.answer("далее....")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

