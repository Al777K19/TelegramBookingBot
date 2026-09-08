from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import asyncio
import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()


class Booking(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()


@dp.message(Command("start"))
async def start(message: Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Записаться")],
            [KeyboardButton(text="📞 Контакты")],
            [KeyboardButton(text="ℹ️ О нас")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "Добро пожаловать!",
        reply_markup=keyboard
    )


@dp.message(F.text == "📞 Контакты")
async def contacts(message: Message):
    await message.answer(
        "📞 Телефон: +49 123 456 78 90\n"
        "📧 Email: info@example.com"
    )


@dp.message(F.text == "ℹ️ О нас")
async def about(message: Message):
    await message.answer(
        "Мы оказываем профессиональные услуги.\n"
        "Работаем ежедневно с 09:00 до 20:00."
    )


@dp.message(F.text == "📅 Записаться")
async def booking(message: Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✂️ Стрижка")],
            [KeyboardButton(text="💅 Маникюр")],
            [KeyboardButton(text="🎨 Окрашивание")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "Выберите услугу:",
        reply_markup=keyboard
    )


@dp.message(F.text.in_(["✂️ Стрижка", "💅 Маникюр", "🎨 Окрашивание"]))
async def service_selected(message: Message, state: FSMContext):
    await state.update_data(service=message.text)
    await state.set_state(Booking.waiting_for_name)

    await message.answer("Введите ваше имя:")


@dp.message(Booking.waiting_for_name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Booking.waiting_for_phone)

    await message.answer("Введите номер телефона:")


@dp.message(Booking.waiting_for_phone)
async def get_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)

    data = await state.get_data()

    await message.answer(
        f"✅ Запись оформлена!\n\n"
        f"Услуга: {data['service']}\n"
        f"Имя: {data['name']}\n"
        f"Телефон: {data['phone']}"
    )

    await state.clear()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
