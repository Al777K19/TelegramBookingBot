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

conn.commit()
conn.close()

print("Таблица applications создана")