from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import asyncio
import os
import re
import sqlite3

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = 6840202483

bot = Bot(token=TOKEN)
dp = Dispatcher()



class Booking(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Записаться")],
            [KeyboardButton(text="💰 Прайс-лист")],
            [KeyboardButton(text="⭐ Отзывы")],
            [KeyboardButton(text="📞 Контакты")],
            [KeyboardButton(text="ℹ️ О нас")]
        ],
        resize_keyboard=True
    )


def services_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✂️ Стрижка")],
            [KeyboardButton(text="💅 Маникюр")],
            [KeyboardButton(text="🎨 Окрашивание")],
            [KeyboardButton(text="⬅️ Назад")],
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Мы поможем вам быстро записаться на услугу.\n"
        "Выберите нужный пункт меню ниже.",
        reply_markup=main_menu()
    )


@dp.message(F.text == "🏠 Главное меню")
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "🏠 Главное меню",
        reply_markup=main_menu()
    )


@dp.message(F.text == "⬅️ Назад")
async def back(message: Message):
    await message.answer(
        "Выберите услугу:",
        reply_markup=services_menu()
    )


@dp.message(F.text == "💰 Прайс-лист")
async def price(message: Message):
    await message.answer(
        "💰 Прайс-лист\n\n"
        "✂️ Стрижка — 20 €\n"
        "💅 Маникюр — 25 €\n"
        "🎨 Окрашивание — 50 €"
    )


@dp.message(F.text == "⭐ Отзывы")
async def reviews(message: Message):
    await message.answer(
        "⭐ Отзывы клиентов\n\n"
        "★★★★★ Отличный сервис!\n\n"
        "★★★★★ Очень доволен результатом.\n\n"
        "★★★★★ Обязательно обращусь снова."
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
        "ℹ️ О нас\n\n"
        "Мы оказываем профессиональные услуги.\n"
        "Работаем ежедневно с 09:00 до 20:00."
    )


@dp.message(F.text == "📅 Записаться")
async def booking(message: Message):
    await message.answer(
        "Выберите услугу:",
        reply_markup=services_menu()
    )


@dp.message(F.text.in_(["✂️ Стрижка", "💅 Маникюр", "🎨 Окрашивание"]))
async def service_selected(message: Message, state: FSMContext):
    await state.update_data(service=message.text)
    await state.set_state(Booking.waiting_for_name)

    await message.answer(
        "Введите ваше имя:"
    )


@dp.message(Booking.waiting_for_name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Booking.waiting_for_phone)

    await message.answer(
        "Введите номер телефона:"
    )


@dp.message(Booking.waiting_for_phone)
async def get_phone(message: Message, state: FSMContext):

    phone = message.text.strip()

    if not re.fullmatch(r"[\d+\-\s()]{6,20}", phone):
        await message.answer(
            "❌ Некорректный номер телефона.\n"
            "Введите номер ещё раз."
        )
        return

    await state.update_data(phone=phone)

    data = await state.get_data()
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO applications
    (service, name, phone, telegram_id, username)
    VALUES (?, ?, ?, ?, ?)
    """, (
        data["service"],
        data["name"],
        phone,
        message.from_user.id,
        message.from_user.username
    ))

    conn.commit()

    application_number = cursor.lastrowid

    conn.close()


    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else "не указан"
    )

    await message.answer(
        f"✅ Заявка успешно оформлена!\n\n"
        f"🆔 Номер заявки: #{application_number:04d}\n"
        f"📅 Услуга: {data['service']}\n"
        f"👤 Имя: {data['name']}\n"
        f"📞 Телефон: {data['phone']}\n\n"
        f"Мы свяжемся с вами в ближайшее время.\n"
        f"Спасибо за обращение!",
        reply_markup=main_menu()
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            f"🔔 Новая заявка!\n\n"
            f"🆔 #{application_number:04d}\n"
            f"📅 Услуга: {data['service']}\n"
            f"👤 Имя: {data['name']}\n"
            f"📞 Телефон: {data['phone']}\n\n"
            f"👤 Telegram: {username}\n"
            f"ID: {message.from_user.id}"
        )
    except Exception as e:
        print(f'Ошибка отправки админу: {e}')

    await state.clear()

@dp.message(Command("applications"))
async def applications(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещён")
        return

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, service, name, phone
    FROM applications
    ORDER BY id DESC
    LIMIT 10
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer("Заявок пока нет.")
        return

    text = "📋 Последние заявки:\n\n"

    for row in rows:
        text += (
            f"🆔 #{row[0]}\n"
            f"📅 {row[1]}\n"
            f"👤 {row[2]}\n"
            f"📞 {row[3]}\n\n"
        )

    await message.answer(text)

@dp.message(Command("count"))
async def count_applications(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM applications")
    count = cursor.fetchone()[0]

    conn.close()

    await message.answer(f"Всего заявок в базе: {count}")

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())