from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import asyncio
import os
import re
import sqlite3
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = 6840202483

bot = Bot(token=TOKEN)
dp = Dispatcher()



class Booking(StatesGroup):
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_broadcast = State()
    waiting_for_broadcast_confirm = State()
    waiting_for_review = State()




def main_menu(user_id=None):
    keyboard = [
        [KeyboardButton(text="📅 Записаться")],
        [KeyboardButton(text="📋 Мои записи")],
        [KeyboardButton(text="💰 Прайс-лист")],
        [KeyboardButton(text="⭐ Отзывы")],
        [KeyboardButton(text="⭐ Оставить отзыв")],
        [KeyboardButton(text="📞 Контакты")],
        [KeyboardButton(text="ℹ️ О нас")]
    ]

    if user_id:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT COUNT(*)
        FROM applications
        WHERE telegram_id = ?
        """, (user_id,))

        has_booking = cursor.fetchone()[0] > 0
        conn.close()

        if has_booking:
            keyboard.insert(
                2,
                [KeyboardButton(text="❌ Отменить запись")]
            )

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Расписание")],
            [KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="👥 Клиенты")],
            [KeyboardButton(text="💰 Выручка")],
            [KeyboardButton(text="📢 Рассылка")]
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

    menu = (
        admin_menu()
        if message.from_user.id == ADMIN_ID
        else main_menu(message.from_user.id)
    )

    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Мы поможем вам быстро записаться на услугу.\n"
        "Выберите нужный пункт меню ниже.",
        reply_markup=menu
    )


@dp.message(F.text == "🏠 Главное меню")
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "🏠 Главное меню",
        reply_markup=main_menu(message.from_user.id)
    )


@dp.message(F.text == "⬅️ Назад")
async def back(message: Message):
    await message.answer(
        "Выберите услугу:",
        reply_markup=services_menu()
    )

@dp.message(F.text == "📋 Мои записи")
async def my_bookings_button(message: Message):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, service, booking_date, booking_time
    FROM applications
    WHERE telegram_id = ?
    ORDER BY id DESC
    """, (message.from_user.id,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer("У вас пока нет записей.")
        return

    text = "📋 Ваши записи\n\n"

    for row in rows:
        text += (
            f"🆔 #{row[0]}\n"
            f"✂️ Услуга: {row[1]}\n"
            f"📆 Дата: {row[2]}\n"
            f"🕒 Время: {row[3]}\n\n"
        )

    await message.answer(text)

@dp.message(F.text == "❌ Отменить запись")
async def cancel_booking(message: Message):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id
    FROM applications
    WHERE telegram_id = ?
    ORDER BY id DESC
    LIMIT 1
    """, (message.from_user.id,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        await message.answer("У вас нет активных записей.")
        return

    booking_id = row[0]

    cursor.execute(
        "DELETE FROM applications WHERE id = ?",
        (booking_id,)
    )

    conn.commit()
    conn.close()

    await message.answer(
        f"✅ Запись №{booking_id} отменена.",
        reply_markup=main_menu(message.from_user.id)
    )

@dp.message(F.text == "💰 Прайс-лист")
async def price(message: Message):
    await message.answer(
        "💰 Прайс-лист\n\n"
        "✂️ Стрижка — 1500 ₽\n"
        "💅 Маникюр — 2000 ₽\n"
        "🎨 Окрашивание — 5000 ₽"
    )


@dp.message(F.text == "⭐ Отзывы")
async def reviews(message: Message):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT name, review
    FROM reviews
    ORDER BY id DESC
    LIMIT 10
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer(
            "⭐ Отзывов пока нет."
        )
        return

    text = "⭐ Последние отзывы:\n\n"

    for name, review in rows:
        text += (
            f"👤 {name}\n"
            f"💬 {review}\n\n"
        )

    await message.answer(text)


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
    await state.set_state(Booking.waiting_for_date)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Сегодня")],
            [KeyboardButton(text="Завтра")],
            [KeyboardButton(text="Послезавтра")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "📆 Выберите дату:",
        reply_markup=keyboard
    )

@dp.message(Booking.waiting_for_date)
async def get_date(message: Message, state: FSMContext):
    await state.update_data(date=message.text)

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT booking_time
    FROM applications
    WHERE booking_date = ?
    """, (message.text,))

    busy_times = [row[0] for row in cursor.fetchall()]
    conn.close()

    all_times = ["09:00", "11:00", "13:00", "15:00", "17:00"]

    free_times = [
        time for time in all_times
        if time not in busy_times
    ]

    if not free_times:
        await message.answer(
            "❌ На выбранную дату свободного времени нет."
        )
        return

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=time)]
            for time in free_times
        ],
        resize_keyboard=True
    )

    await state.set_state(Booking.waiting_for_time)

    await message.answer(
        "🕒 Выберите время:",
        reply_markup=keyboard
    )

@dp.message(Booking.waiting_for_time)
async def get_time(message: Message, state: FSMContext):
    data = await state.get_data()

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT COUNT(*)
    FROM applications
    WHERE booking_date = ?
    AND booking_time = ?
    """, (
        data["date"],
        message.text
    ))

    count = cursor.fetchone()[0]
    conn.close()

    if count > 0:
        await message.answer(
            "❌ Это время уже занято.\n"
            "Выберите другое время."
        )
        return

    await state.update_data(time=message.text)
    await state.set_state(Booking.waiting_for_name)

    await message.answer(
        "Введите ваше имя:",
        reply_markup=ReplyKeyboardRemove()
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
    (service, booking_date, booking_time, name, phone, telegram_id, username)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["service"],
        data["date"],
        data["time"],
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
        f"📆 Дата: {data['date']}\n"
        f"🕒 Время: {data['time']}\n"
        f"👤 Имя: {data['name']}\n"
        f"📞 Телефон: {data['phone']}\n\n"
        f"Мы свяжемся с вами в ближайшее время.\n"
        f"Спасибо за обращение!",
        reply_markup=main_menu(message.from_user.id)
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            f"🔔 Новая заявка!\n\n"
            f"🆔 #{application_number:04d}\n"
            f"📅 Услуга: {data['service']}\n"
            f"📆 Дата: {data['date']}\n"
            f"🕒 Время: {data['time']}\n"
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

@dp.message(Command("stats"))
async def stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM applications")
    total = cursor.fetchone()[0]

    cursor.execute("""
    SELECT service, COUNT(*)
    FROM applications
    GROUP BY service
    """)

    rows = cursor.fetchall()
    conn.close()

    text = f"📊 Статистика\n\nВсего заявок: {total}\n\n"

    for service, count in rows:
        text += f"{service}: {count}\n"

    await message.answer(text)

@dp.message(Command("schedule"))
async def schedule(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT booking_date, booking_time, service, name
    FROM applications
    ORDER BY booking_date, booking_time
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer("Записей пока нет.")
        return

    text = "📅 Расписание\n\n"

    for date, time, service, name in rows:
        text += (
            f"📆 {date}\n"
            f"🕒 {time} — {service} — {name}\n\n"
        )

    await message.answer(text)

@dp.message(F.text == "📅 Расписание")
async def schedule(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT service, booking_date, booking_time, name
    FROM applications
    ORDER BY id DESC
    LIMIT 20
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer("Записей пока нет.")
        return

    text = "📅 Расписание\n\n"

    for row in rows:
        text += (
            f"✂️ {row[0]}\n"
            f"📆 {row[1]}\n"
            f"🕒 {row[2]}\n"
            f"👤 {row[3]}\n\n"
        )

    await message.answer(text)

@dp.message(F.text == "📊 Статистика")
async def statistics(message: Message):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Всего записей
    cursor.execute("SELECT COUNT(*) FROM applications")
    total_bookings = cursor.fetchone()[0]

    # Уникальные клиенты
    cursor.execute("SELECT COUNT(DISTINCT telegram_id) FROM applications")
    total_clients = cursor.fetchone()[0]

    # Самая популярная услуга
    cursor.execute("""
        SELECT service, COUNT(*)
        FROM applications
        GROUP BY service
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """)
    popular = cursor.fetchone()

    if popular:
        service_name = popular[0]
        service_count = popular[1]
    else:
        service_name = "Нет данных"
        service_count = 0

    # Выручка
    cursor.execute("SELECT service FROM applications")
    services = cursor.fetchall()

    revenue = 0
    for service in services:
        revenue += PRICES.get(service[0], 0)

    conn.close()

    await message.answer(
        f"📊 Статистика\n\n"
        f"👥 Клиентов: {total_clients}\n"
        f"📅 Записей: {total_bookings}\n"
        f"🏆 Популярная услуга: {service_name}\n"
        f"🔢 Записей на неё: {service_count}\n"
        f"💰 Выручка: {revenue} ₽"
    )

@dp.message(F.text == "👥 Клиенты")
async def clients(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT DISTINCT name, phone
    FROM applications
    ORDER BY name
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer("Клиентов пока нет.")
        return

    text = "👥 Клиенты\n\n"

    for name, phone in rows:
        text += (
            f"👤 {name}\n"
            f"📞 {phone}\n\n"
        )

    await message.answer(text)

@dp.message(F.text == "💰 Выручка")
async def revenue(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT service, COUNT(*)
    FROM applications
    GROUP BY service
    """)

    rows = cursor.fetchall()
    conn.close()

    prices = {
        "✂️ Стрижка": 1500,
        "💅 Маникюр": 2000,
        "🎨 Окрашивание": 5000
    }

    total = 0
    text = "💰 Выручка\n\n"

    for service, count in rows:
        revenue = count * prices.get(service, 0)
        total += revenue

        text += (
            f"{service}\n"
            f"{count} × {prices.get(service, 0)}₽ = {revenue}₽\n\n"
        )

    text += f"💵 Итого: {total}₽"

    await message.answer(text)

@dp.message(F.text == "📢 Рассылка")
async def broadcast_start(message: Message, state: FSMContext):

    if message.from_user.id != ADMIN_ID:
        return

    await state.set_state(Booking.waiting_for_broadcast)

    await message.answer(
        "📢 Введите текст для рассылки:"
    )

@dp.message(Booking.waiting_for_broadcast)
async def broadcast_send(message: Message, state: FSMContext):

    if message.from_user.id != ADMIN_ID:
        return

    await state.update_data(broadcast_text=message.text)
    await state.set_state(Booking.waiting_for_broadcast_confirm)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Отправить")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        f"📢 Текст рассылки:\n\n{message.text}\n\nОтправить рассылку?",
        reply_markup=keyboard
    )

@dp.message(Booking.waiting_for_broadcast_confirm, F.text == "✅ Отправить")
async def confirm_broadcast(message: Message, state: FSMContext):

    data = await state.get_data()
    text_to_send = data["broadcast_text"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT DISTINCT telegram_id
    FROM applications
    """)

    users = cursor.fetchall()
    conn.close()

    sent = 0

    for user in users:
        try:
            await bot.send_message(
                user[0],
                f"📢 Сообщение от администрации\n\n{text_to_send}"
            )
            sent += 1
        except Exception:
            pass

    await message.answer(
        f"✅ Рассылка завершена.\nОтправлено: {sent}",
        reply_markup=admin_menu()
    )

    await state.clear()

@dp.message(Booking.waiting_for_broadcast_confirm, F.text == "❌ Отмена")
async def cancel_broadcast(message: Message, state: FSMContext):

    await state.clear()

    await message.answer(
        "❌ Рассылка отменена.",
        reply_markup=admin_menu()
    )

@dp.message(F.text == "⭐ Оставить отзыв")
async def review_start(message: Message, state: FSMContext):

    await state.set_state(Booking.waiting_for_review)

    await message.answer(
        "⭐ Напишите ваш отзыв:"
    )


@dp.message(Booking.waiting_for_review)
async def save_review(message: Message, state: FSMContext):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO reviews (name, review)
    VALUES (?, ?)
    """, (
        message.from_user.full_name,
        message.text
    ))

    conn.commit()
    conn.close()

    await message.answer(
        "✅ Спасибо за отзыв!",
        reply_markup=main_menu()
    )

    await state.clear()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())