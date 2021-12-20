import asyncio
import datetime
import os
import re
import time
import json
import random

from datetime import timedelta

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Text
import aiogram.utils.markdown as fmt

from dotenv import load_dotenv

load_dotenv()
token = os.getenv("TG_BOT_TOKEN")
loop = asyncio.get_event_loop()
bot = Bot(token=token, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage, loop=loop)
game_data = {}
participants_of_game = []
collect_games = []


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
    msg = message.text
    msg_text = re.sub(r'\d+', "", str(msg))
    if not str(msg_text) == '/start reg' or str(msg_text) == 'Отмена':
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
        game_data['limit_price'] = 'Нет ограничений'
    user_date = datetime.datetime.today()
    das = user_date + timedelta(weeks=4)
    count_date = das - user_date
    days = user_date + timedelta(days=count_date.days)
    keyboard = types.InlineKeyboardMarkup(row_width=3, resize_keyboard=True, one_time_keyboard=True)
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
    keyboard = types.InlineKeyboardMarkup(row_width=3, resize_keyboard=True, one_time_keyboard=True)
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
    game_data['link_game'] = f'https://t.me/{bot_name.username}?start=reg{game_data["game_id"]}'
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

    keyboard.add(types.InlineKeyboardButton(text='Посмотреть все ссылки игр?', callback_data='links')),
    keyboard.add(types.InlineKeyboardButton(text='Запустить жеребьевку сейчас', callback_data='Запустить жеребьевку сейчас')),
    keyboard.add(types.InlineKeyboardButton(text='Удалить участника', callback_data='Удалить участника')),

    await call.message.answer("Отлично! Тайный Санта уже готовится к раздаче подарков!")
    await call.message.answer(
        fmt.text(
            fmt.text("Перешлите ссылку новому участнику игры для регистрации:\n\n"),
            fmt.text(f"Игра:  {game_data['name_game']}\n"),
            fmt.text(f'https://t.me/{bot_name.username}?start=reg{game_data["game_id"]}'),
        ), reply_markup=keyboard
    )
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


@dp.callback_query_handler(text_contains='links')
async def print_links(call: types.CallbackQuery):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(KeyboardButton(text='Создать игру'))
    with open('games.json', 'r') as games:
        games_db = json.load(games)
    for links in games_db:
        await call.message.answer(f"Игра: {links['name_game']}\n{links['link_game']}")


def validate_email(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return bool(re.fullmatch(regex, email))


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
    keyboard.add(KeyboardButton(text='Отправить письмо санте!', callback_data='register_finish')),
    keyboard.add(KeyboardButton(text='Изменить письмо санте')),
    keyboard.add(KeyboardButton(text='Отмена'))
    await message.answer('🎅', reply_markup=keyboard)


@dp.message_handler(state=RegisterOrder.register_finish)
async def register_finish(message: types.Message, state: FSMContext):
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


@dp.callback_query_handler(text='Удалить участника')
async def choice_del_user(call: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    if call.data == 'Удалить участника':
        with open('users.json') as f:
            file_data = json.load(f)
        for user in file_data:
            buttons = [
                types.InlineKeyboardButton(
                    text=f'{user["user_name"]}',
                    callback_data=f'{user["user_name"]}6')]
            keyboard.row(*buttons)
        await call.message.answer(f"Выберите кого удалить", reply_markup=keyboard)


@dp.callback_query_handler(text_contains='6')
async def del_user(call: types.CallbackQuery):
    del_user = re.sub(r'6', "", call.data)
    with open('users.json') as f:
        file_data = json.load(f)
    for user in file_data:
        if del_user == user["user_name"]:
            await call.message.answer(f'{user["user_name"]} - удален')
            del user
        else:
            with open('users.json', 'w') as file:
                json.dump(user, file, ensure_ascii=False, default=str, indent=3)


@dp.callback_query_handler(text_contains='Запустить жеребьевку сейчас')
@dp.callback_query_handler(text='Посмотреть список желаний:')
async def random_choice(call: types.CallbackQuery):
    await call.message.answer(call.data)
    if not call.data == 'Запустить жеребьевку сейчас':
        await call.message.answer(call.data)
        keyboard = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        buttons = [
            types.InlineKeyboardButton(text='Посмотреть список желаний участников!', callback_data='список')
        ]
        keyboard.row(*buttons)
        await call.message.answer(f'Превосходно, ты в игре! {game_data["date_reg"]} мы проведем жеребьевку'
                                  f' и ты узнаешь имя и контакты своего тайного друга.'
                                  f' Ему и нужно будет подарить подарок!', reply_markup=types.ReplyKeyboardRemove())
        await call.answer()
        with open('games.json', 'r') as games:
            games_db = json.load(games)
        with open('users.json', 'r') as users:
            users_d = json.load(users)
        for user in users_d:
            collect_games.append(user['game_id'])
            for game in games_db:
                if user['game_id'] == game['game_id'] and user['date_reg'] == game['date_reg']:
                    if user['date_reg'] == game_data['date_reg']:
                        participants_of_game.append([user['user_id'], user['user_name'], user['user_wishlist'],
                                                     user['user_email'], user['letter_to_santa']])
        for wish in participants_of_game:
            await call.message.answer(f"Игрок: {wish[1]} желает получить:\n\n{wish[2]}")
    #     while True:
    #         time.sleep(60 * 60)
    #         date_today = datetime.datetime.today()
    #         date_reg = re.sub(r'q', "", game_data['date_reg'])
    #         day, month, year = date_reg.split(".")
    #         user_date = datetime.datetime(int(year), int(month), int(day))
    #         activate = user_date + timedelta(hours=12)
    #         if activate <= date_today:
    #             for user in users_d:
    #                 for game in games_db:
    #                     if user['date_reg'] == game['date_reg'] and user['game_id'] == game['game_id']:
    #                         random.shuffle(participants_of_game)
    #                         offset = [participants_of_game[-1]] + participants_of_game[:-1]
    #                         stop_send = 0
    #                         for current_user, receiver in zip(participants_of_game, offset):
    #                             stop_send += 1
    #                             if stop_send == len(participants_of_game):
    #                                 break
    #                             print(current_user, "Дарит подарок", receiver)
    #                             if current_user[0] == user["user_id"]:
    #                                 await bot.send_message(
    #                                     user["user_id"], "Жеребьевка в игре “Тайный Санта” проведена!"
    #                                                      " Спешу сообщить кто тебе выпал!")
    #                                 await bot.send_message(
    #                                     user["user_id"],
    #                                     fmt.text(
    #                                         fmt.text(
    #                                             f"Тебе выпал игрок:  {receiver[1]}\n\n"),
    #                                         fmt.text(
    #                                             f"Email:  {receiver[3]}\n\n"),
    #                                         fmt.text(
    #                                             f"\nПисьмо Санте:   {receiver[4]}\n\n"),
    #                                         fmt.text(
    #                                             f"\nЖелания:   {receiver[2]}\n"),
    #                                     )
    #                                 )
    #                         break
    #                 break
    #             break
    # else:
    #     with open('games.json', 'r') as games:
    #         games_db = json.load(games)
    #     with open('users.json', 'r') as users:
    #         users_d = json.load(users)
    #     for user in users_d:
    #         collect_games.append(user['game_id'])
    #         for game in games_db:
    #             if user['game_id'] == game['game_id'] and user['date_reg'] == game['date_reg']:
    #                 if user['date_reg'] == game_data['date_reg']:
    #                     participants_of_game.append([user['user_id'], user['user_name'], user['user_wishlist'],
    #                                                  user['user_email'], user['letter_to_santa']])
    #     while True:
    #         time.sleep(2)
    #         for user in users_d:
    #             for game in games_db:
    #                 if user['date_reg'] == game['date_reg'] and user['game_id'] == game['game_id']:
    #                     random.shuffle(participants_of_game)
    #                     offset = [participants_of_game[-1]] + participants_of_game[:-1]
    #                     stop_send = 0
    #                     for current_user, receiver in zip(participants_of_game, offset):
    #                         stop_send += 1
    #                         if stop_send == len(participants_of_game):
    #                             break
    #                         print(current_user, "Дарит подарок", receiver)
    #                         if current_user[0] == user["user_id"]:
    #                             await bot.send_message(
    #                                 user["user_id"], "Жеребьевка в игре “Тайный Санта” проведена!"
    #                                                  " Спешу сообщить кто тебе выпал!")
    #                             await bot.send_message(
    #                                 user["user_id"],
    #                                 fmt.text(
    #                                     fmt.text(
    #                                         f"Тебе выпал игрок:  {receiver[1]}\n\n"),
    #                                     fmt.text(
    #                                         f"Email:  {receiver[3]}\n\n"),
    #                                     fmt.text(
    #                                         f"\nПисьмо Санте:   {receiver[4]}\n\n"),
    #                                     fmt.text(
    #                                         f"\nЖелания:   {receiver[2]}\n"),
    #                                 )
    #                             )
    #                     break
    #             break
    #         break

# block for test

        user_date_1 = datetime.datetime.today() + timedelta(minutes=1)
        while True:
            date_today = datetime.datetime.today()
            time.sleep(10)
            if user_date_1 <= date_today:
                for user in users_d:
                    for game in games_db:
                        time.sleep(2)
                        if user['date_reg'] == game['date_reg'] and user['game_id'] == game['game_id']:
                            random.shuffle(participants_of_game)
                            offset = [participants_of_game[-1]] + participants_of_game[:-1]
                            stop_send = 0
                            for current_user, receiver in zip(participants_of_game, offset):
                                stop_send += 1
                                if stop_send == len(participants_of_game):
                                    break
                                print(current_user, "Дарит подарок", receiver)
                                if current_user[0] == user["user_id"]:
                                    await bot.send_message(
                                        user["user_id"], "Жеребьевка в игре “Тайный Санта” проведена!"
                                                         " Спешу сообщить кто тебе выпал!")
                                    await bot.send_message(
                                        user["user_id"],
                                        fmt.text(
                                            fmt.text(
                                                f"Тебе выпал игрок:  {receiver[1]}\n\n"),
                                            fmt.text(
                                                f"Email:  {receiver[3]}\n\n"),
                                            fmt.text(
                                                f"\nПисьмо Санте:   {receiver[4]}\n\n"),
                                            fmt.text(
                                                f"\nЖелания:   {receiver[2]}\n"),
                                        )
                                    )
                            break
                    break
                break
            print('-----')
    else:
        with open('games.json', 'r') as games:
            games_db = json.load(games)
        with open('users.json', 'r') as users:
            users_d = json.load(users)
        for user in users_d:
            collect_games.append(user['game_id'])
            for game in games_db:
                if user['game_id'] == game['game_id'] and user['date_reg'] == game['date_reg']:
                    if user['date_reg'] == game_data['date_reg']:
                        participants_of_game.append([user['user_id'], user['user_name'], user['user_wishlist'],
                                                     user['user_email'], user['letter_to_santa']])
        while True:
            time.sleep(2)
            for user in users_d:
                for game in games_db:
                    if user['date_reg'] == game['date_reg'] and user['game_id'] == game['game_id']:
                        random.shuffle(participants_of_game)
                        offset = [participants_of_game[-1]] + participants_of_game[:-1]
                        stop_send = 0
                        for current_user, receiver in zip(participants_of_game, offset):
                            stop_send += 1
                            if stop_send == len(participants_of_game):
                                break
                            print(current_user, "Дарит подарок", receiver)
                            if current_user[0] == user["user_id"]:
                                await bot.send_message(
                                    user["user_id"], "Жеребьевка в игре “Тайный Санта” проведена!"
                                                     " Спешу сообщить кто тебе выпал!")
                                await bot.send_message(
                                    user["user_id"],
                                    fmt.text(
                                        fmt.text(
                                            f"Тебе выпал игрок:  {receiver[1]}\n\n"),
                                        fmt.text(
                                            f"Email:  {receiver[3]}\n\n"),
                                        fmt.text(
                                            f"\nПисьмо Санте:   {receiver[4]}\n\n"),
                                        fmt.text(
                                            f"\nЖелания:   {receiver[2]}\n"),
                                    )
                                )

                        break

                break
            break
        print('-----')


@dp.message_handler()
async def name_game(message: types.Message):
    if not game_data['name_game']:
        game_data['name_game'] = message.text
        game_data['game_id'] = random.randint(101, 701)
        await bot.delete_message(message.from_user.id, message.message_id)
        keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
        button_yes = types.InlineKeyboardButton(text='ДА', callback_data='yes')
        button_no = types.InlineKeyboardButton(text='НЕТ', callback_data='pp')
        keyboard.add(button_yes, button_no)
        await message.answer(f"Для игры - {game_data['name_game']}\n\nТребуется ограничение стоимости подарка?",
                             reply_markup=keyboard)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
