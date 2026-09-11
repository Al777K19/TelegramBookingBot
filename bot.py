from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import asyncio
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)


TIMEZONE = ZoneInfo("Asia/Almaty")


def init_database():
    from db import get_connection

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id SERIAL PRIMARY KEY,
        service TEXT,
        booking_date TEXT,
        booking_time TEXT,
        name TEXT,
        phone TEXT,
        telegram_id BIGINT,
        username TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    ALTER TABLE applications
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'pending'
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id SERIAL PRIMARY KEY,
        name TEXT,
        review TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    cursor.close()
    conn.close()

    print("✅ База данных проверена")


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


cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True
)


def main_menu(user_id=None):
    keyboard = [
        [KeyboardButton(text="👤 Личный кабинет")],
        [KeyboardButton(text="📅 Записаться")],
        [KeyboardButton(text="📋 Мои записи")],
        [KeyboardButton(text="💰 Прайс-лист")],
        [KeyboardButton(text="⭐ Отзывы")],
        [KeyboardButton(text="⭐ Оставить отзыв")],
        [KeyboardButton(text="📞 Контакты")],
        [KeyboardButton(text="ℹ️ О нас")]
    ]

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
            [KeyboardButton(text="❌ Отмена")]
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

    from db import get_connection

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, service, booking_date, booking_time, status
    FROM applications
    WHERE telegram_id = %s
    AND status != 'cancelled'
    ORDER BY booking_date, booking_time
    """, (message.from_user.id,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer(
            "📋 У вас пока нет активных записей."
        )
        return

    for row in rows:

        booking_id = row[0]
        service = row[1]
        booking_date = row[2]
        booking_time = row[3]
        status = row[4]

        if status == "pending":
            status_text = "📌 Запись оформлена"
        elif status == "confirmed":
            status_text = "🟢 Подтверждена"
        elif status == "completed":
            status_text = "🔵 Завершена"
        else:
            status_text = "⚪ Неизвестный статус"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"❌ Отменить #{booking_id:04d}",
                        callback_data=f"user_cancel_{booking_id}"
                    )
                ]
            ]
        )

        await message.answer(
            f"🆔 Запись #{booking_id:04d}\n\n"
            f"✂️ Услуга: {service}\n"
            f"📆 Дата: {booking_date}\n"
            f"🕒 Время: {booking_time}\n"
            f"📌 Статус: {status_text}",
            reply_markup=keyboard
        )

@dp.callback_query(F.data.startswith("user_cancel_"))
async def user_cancel_booking(callback: CallbackQuery):

    booking_id = int(
        callback.data.replace("user_cancel_", "")
    )

    from db import get_connection

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT service, booking_date, booking_time, status
    FROM applications
    WHERE id = %s
    AND telegram_id = %s
    """, (
        booking_id,
        callback.from_user.id
    ))

    booking = cursor.fetchone()

    if not booking:
        conn.close()

        await callback.answer(
            "❌ Запись не найдена.",
            show_alert=True
        )
        return

    service, booking_date, booking_time, status = booking

    if status == "cancelled":
        conn.close()

        await callback.answer(
            "Эта запись уже отменена.",
            show_alert=True
        )
        return

    cursor.execute("""
    UPDATE applications
    SET status = 'cancelled'
    WHERE id = %s
    AND telegram_id = %s
    """, (
        booking_id,
        callback.from_user.id
    ))

    conn.commit()
    conn.close()

    await callback.message.edit_text(
        f"❌ Запись #{booking_id:04d} отменена.\n\n"
        f"✂️ Услуга: {service}\n"
        f"📆 Дата: {booking_date}\n"
        f"🕒 Время: {booking_time}"
    )

    await callback.answer("Запись отменена")


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

    from db import get_connection

    conn = get_connection()
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

@dp.message(F.text == "👤 Личный кабинет")
async def profile(message: Message):

    from db import get_connection

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT name, phone
    FROM applications
    WHERE telegram_id = %s
    ORDER BY id DESC
    LIMIT 1
    """, (message.from_user.id,))

    user = cursor.fetchone()

    cursor.execute("""
    SELECT COUNT(*)
    FROM applications
    WHERE telegram_id = %s
    """, (message.from_user.id,))

    bookings_count = cursor.fetchone()[0]

    cursor.execute("""
    SELECT service, booking_date, booking_time
    FROM applications
    WHERE telegram_id = %s
    ORDER BY id DESC
    LIMIT 1
    """, (message.from_user.id,))

    last_booking = cursor.fetchone()

    conn.close()

    if not user:
        await message.answer(
            "❌ У вас пока нет записей."
        )
        return

    name, phone = user

    if bookings_count >= 10:
        status = "🥇 VIP клиент"
    elif bookings_count >= 5:
        status = "🥈 Постоянный клиент"
    else:
        status = "🥉 Новый клиент"

    text = (
        f"👤 Личный кабинет\n\n"
        f"🙍 Имя: {name}\n"
        f"📞 Телефон: {phone}\n"
        f"📅 Записей: {bookings_count}\n"
        f"🏆 Статус: {status}\n\n"
    )

    if last_booking:
        text += (
            f"📌 Последняя запись:\n"
            f"{last_booking[0]}\n"
            f"📆 {last_booking[1]}\n"
            f"🕒 {last_booking[2]}"
        )

    await message.answer(text)

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

    today = datetime.now(TIMEZONE).date()

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
                     [KeyboardButton(
                         text=(today + timedelta(days=i)).strftime("%d.%m.%Y")
                     )]
                     for i in range(7)
                 ] + [
                     [KeyboardButton(text="❌ Отмена")]
                 ],
        resize_keyboard=True
    )

    await message.answer(
        "📆 Выберите дату:",
        reply_markup=keyboard
    )

@dp.message(Booking.waiting_for_date)
async def get_date(message: Message, state: FSMContext):

    if message.text == "❌ Отмена":
        await state.clear()

        await message.answer(
            "❌ Запись отменена.",
            reply_markup=main_menu(message.from_user.id)
        )
        return

    try:
        selected_date = datetime.strptime(
            message.text,
            "%d.%m.%Y"
        ).date()
    except ValueError:
        await message.answer(
            "⚠️ Пожалуйста, выберите дату кнопкой."
        )
        return

    today = datetime.now(TIMEZONE).date()

    # Защита от выбора прошедшей даты
    if selected_date < today:
        await message.answer(
            "❌ Нельзя выбрать прошедшую дату."
        )
        return

    await state.update_data(
        date=selected_date.strftime("%Y-%m-%d")
    )

    from db import get_connection

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT booking_time
    FROM applications
    WHERE booking_date = %s
    AND status != 'cancelled'
    """, (
        selected_date.strftime("%Y-%m-%d"),
    ))

    busy_times = [row[0] for row in cursor.fetchall()]

    conn.close()

    all_times = [
        "09:00",
        "11:00",
        "13:00",
        "15:00",
        "17:00"
    ]

    # Если выбрали сегодняшний день,
    # убираем уже прошедшее время
    if selected_date == today:

        current_time = datetime.now(TIMEZONE).time()

        all_times = [
            time for time in all_times
            if datetime.strptime(
                time,
                "%H:%M"
            ).time() > current_time
        ]

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
        ] + [
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

    await state.set_state(Booking.waiting_for_time)

    await message.answer(
        "🕒 Выберите свободное время:",
        reply_markup=keyboard
    )


@dp.message(Booking.waiting_for_time)
async def get_time(message: Message, state: FSMContext):

    if message.text == "❌ Отмена":
        await state.clear()

        await message.answer(
            "❌ Запись отменена.",
            reply_markup=main_menu(message.from_user.id)
        )
        return

    allowed_times = [
        "09:00",
        "11:00",
        "13:00",
        "15:00",
        "17:00"
    ]

    if message.text not in allowed_times:
        await message.answer(
            "⚠️ Пожалуйста, выберите время кнопкой."
        )
        return

    data = await state.get_data()

    from db import get_connection

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT COUNT(*)
    FROM applications
    WHERE booking_date = %s
    AND booking_time = %s
    AND status != 'cancelled'
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
        reply_markup=cancel_keyboard
    )


@dp.message(Booking.waiting_for_name)
async def get_name(message: Message, state: FSMContext):

    if message.text == "❌ Отмена":
        await state.clear()

        await message.answer(
            "❌ Запись отменена.",
            reply_markup=main_menu(message.from_user.id)
        )
        return

    await state.update_data(name=message.text)
    await state.set_state(Booking.waiting_for_phone)

    await message.answer(
        "Введите номер телефона:",
        reply_markup=cancel_keyboard
    )


@dp.message(Booking.waiting_for_phone)
async def get_phone(message: Message, state: FSMContext):

    if message.text == "❌ Отмена":
        await state.clear()

        await message.answer(
            "❌ Запись отменена.",
            reply_markup=main_menu(message.from_user.id)
        )
        return

    phone = message.text.strip()

    if not re.fullmatch(r"[\d+\-\s()]{6,20}", phone):
        await message.answer(
            "❌ Некорректный номер телефона.\n"
            "Введите номер ещё раз."
        )
        return

    await state.update_data(phone=phone)

    data = await state.get_data()

    from db import get_connection

    conn = get_connection()
    cursor = conn.cursor()

    # Проверяем, не занято ли время
    cursor.execute("""
    SELECT COUNT(*)
    FROM applications
    WHERE booking_date = %s
    AND booking_time = %s
    AND status != 'cancelled'
    """, (
        data["date"],
        data["time"]
    ))

    count = cursor.fetchone()[0]

    if count > 0:
        conn.close()

        await message.answer(
            "❌ Это время уже занято.\n\n"
            "Пожалуйста, выберите другое время.",
            reply_markup=main_menu(message.from_user.id)
        )

        await state.clear()
        return

    # Создаём запись
    try:

        cursor.execute("""
        INSERT INTO applications
        (service, booking_date, booking_time, name, phone, telegram_id, username)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """, (
            data["service"],
            data["date"],
            data["time"],
            data["name"],
            phone,
            message.from_user.id,
            message.from_user.username
        ))

        application_number = cursor.fetchone()[0]

        conn.commit()

    except Exception as e:

        conn.rollback()
        conn.close()

        print(f"Ошибка создания записи: {e}")

        await message.answer(
            "❌ К сожалению, это время только что занял другой клиент.\n\n"
            "Пожалуйста, выберите другое время.",
            reply_markup=main_menu(message.from_user.id)
        )

        await state.clear()
        return

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

    # Уведомление администратора
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
        print(f"Ошибка отправки админу: {e}")

    await state.clear()


@dp.message(Command("applications"))
async def applications(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещён")
        return

    from db import get_connection

    conn = get_connection()
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

    from db import get_connection

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM applications")
    count = cursor.fetchone()[0]

    conn.close()

    await message.answer(f"Всего заявок в базе: {count}")

@dp.message(Command("stats"))
async def stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    from db import get_connection

    conn = get_connection()
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


@dp.message(F.text == "📅 Расписание")
async def schedule(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    from db import get_connection

    conn = get_connection()
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

prices = {
    "✂️ Стрижка": 1500,
    "💅 Маникюр": 2000,
    "🎨 Окрашивание": 5000
}

@dp.message(F.text == "📊 Статистика")
async def statistics(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    from db import get_connection

    conn = get_connection()
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
        revenue += prices.get(service[0], 0)

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

    from db import get_connection

    conn = get_connection()
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

    from db import get_connection

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT service, COUNT(*)
    FROM applications
    GROUP BY service
    """)

    rows = cursor.fetchall()
    conn.close()


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

    from db import get_connection

    conn = get_connection()
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

    from db import get_connection

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO reviews (name, review)
    VALUES (%s, %s)
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

@dp.message(F.text == "❌ Отмена")
async def cancel_action(message: Message, state: FSMContext):

    await state.clear()

    await message.answer(
        "❌ Запись отменена."
    )

    await message.answer(
        "🏠 Главное меню",
        reply_markup=main_menu(message.from_user.id)
    )

async def main():
    init_database()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())