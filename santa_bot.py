import os
import re

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

load_dotenv()
tg_bot_token = os.getenv('TG_BOT_TOKEN')
bot = Bot(token=tg_bot_token)
dp = Dispatcher(bot, storage=MemoryStorage())


def validate_email(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return bool(re.fullmatch(regex, email))


class RegisterOrder(StatesGroup):
    game_id = State()
    user_name = State()
    user_email = State()
    user_wishlist = State()
    letter_to_santa = State()


@dp.message_handler(commands=['register'])
async def cmd_register(message: types.Message, state: FSMContext):
    try:
        game_id = int(message.text.split()[1])
        user_id = message['from']['id']
        await state.update_data(game_id=game_id)
        await state.update_data(user_id=user_id)
        await RegisterOrder.user_name.set()
        await message.answer('Теперь укажите имя пользователя:')
    except IndexError:
        await message.reply('Введите id игры.')
        await RegisterOrder.game_id.set()
    except ValueError:
        await message.answer('id игры должен быть целым числом')
        return


@dp.message_handler(state=RegisterOrder.game_id)
async def get_game_id(message: types.Message, state: FSMContext):
    print('id игры')
    try:
        game_id = int(message.text)
        await state.update_data(game_id=game_id)
        await RegisterOrder.next()
        await message.answer('Теперь укажите имя пользователя:')
    except ValueError:
        await message.answer('id игры должен быть целым числом')
        return

@dp.message_handler(state=RegisterOrder.user_name)
async def get_user_name(message: types.Message, state: FSMContext):
    print('Имя пользователя')
    user_name = message.text
    await state.update_data(user_name=user_name)
    await RegisterOrder.next()
    await message.answer('Теперь укажите email пользователя:')

@dp.message_handler(state=RegisterOrder.user_email)
async def get_user_email(message: types.Message, state: FSMContext):
    print('email пользователя')
    user_email = message.text
    if not validate_email(user_email.strip()):
        await message.answer('Введите корректный email')
        return
    await state.update_data(user_email=user_email)
    await RegisterOrder.next()
    await message.answer('Теперь укажите ваш вишлист (введите стоп, что бы продолжить дальше):')

@dp.message_handler(state=RegisterOrder.user_wishlist)
async def get_user_wishlist(message: types.Message, state: FSMContext):
    print('Хотелки пользователя')
    user_wishlist = message.text
    await state.update_data(user_wishlist=user_wishlist)
    await RegisterOrder.next()
    await message.answer('Напишите письмо санте:')

@dp.message_handler(state=RegisterOrder.letter_to_santa)
async def write_letter_to_santa(message: types.Message, state: FSMContext):
    print('Пишем письмо санте')
    letter = message.text
    await state.update_data(letter_to_santa=letter)
    user_data = await state.get_data()
    print(user_data)
    await state.finish()
    await message.answer('Вы зарегистрированы на игру. Ожидайте сообщения о начале игры.')

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
