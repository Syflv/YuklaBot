import logging
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from yt_dlp import YoutubeDL
import os

# --- SOZLAMALAR ---
API_TOKEN = '8685709263:AAFoqXZAeV7-C6mlM3UecasV86fWq4hSl0A'
ADMIN_ID = 2085230699  # O'zingizning ID raqamingizni yozing
CHANNELS = [
    {'name': 'Kanal 1', 'id': -100123456789, 'url': 'https://t.me/kanal1'},
]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- MA'LUMOTLAR BAZASI ---
def db_init():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()
    return [u[0] for u in users]

# --- MAJBURIY OBUNA TEKSHIRUVI ---
async def check_sub(user_id):
    for channel in CHANNELS:
        status = await bot.get_chat_member(chat_id=channel['id'], user_id=user_id)
        if status.status == 'left':
            return False
    return True

def sub_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ch['name'], url=ch['url'])] for ch in CHANNELS
    ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="Tekshirish", callback_data="check")])
    return keyboard

# --- ADMIN PANEL TUGMALARI ---
def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Statistika 📊", callback_data="stats")],
        [InlineKeyboardButton(text="Reklama yuborish 📢", callback_data="broadcast")]
    ])

# --- ASOSIY HANDLERLAR ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    add_user(message.from_user.id)
    if not await check_sub(message.from_user.id):
        await message.answer("Botdan foydalanish uchun kanallarga a'zo bo'ling:", reply_markup=sub_keyboard())
        return
    await message.answer("Salom! Instagram yoki YouTube linkini yuboring, men uni yuklab beraman.")

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Admin panelga xush kelibsiz:", reply_markup=admin_keyboard())

@dp.callback_query(F.data == "stats")
async def show_stats(call: types.CallbackQuery):
    users = get_all_users()
    await call.message.answer(f"Bot foydalanuvchilari soni: {len(users)} ta")

@dp.callback_query(F.data == "broadcast")
async def start_broadcast(call: types.CallbackQuery):
    await call.message.answer("Reklama xabarini yuboring (matn, rasm yoki video):")
    # Bu yerda oddiyroq bo'lishi uchun keyingi kelgan xabarni reklama deb hisoblaymiz

# --- VIDEO YUKLASH MANTIQI ---
async def download_video(url, message: types.Message):
    wait_msg = await message.answer("Yuklanmoqda, iltimos kuting...")
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': '%(title).20s.%(ext)s',
        'max_filesize': 50 * 1024 * 1024, # 50MB limit
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            video = types.FSInputFile(filename)
            await message.answer_video(video, caption=f"Tayyor! \n\n@SizningBot_uz")
            os.remove(filename)
            await wait_msg.delete()
    except Exception as e:
        await wait_msg.edit_text(f"Xatolik yuz berdi: Fayl juda katta yoki link noto'g'ri.")

@dp.message()
async def handle_message(message: types.Message):
    if not await check_sub(message.from_user.id):
        await message.answer("Avval kanallarga a'zo bo'ling!", reply_markup=sub_keyboard())
        return

    # Agar admin reklama yubormoqchi bo'lsa (sodda mantiq)
    if message.from_user.id == ADMIN_ID and message.reply_to_message:
        users = get_all_users()
        count = 0
        for user_id in users:
            try:
                await message.copy_to(user_id)
                count += 1
            except:
                pass
        await message.answer(f"Reklama {count} kishiga yuborildi.")
        return

    if "instagram.com" in message.text or "youtube.com" in message.text or "youtu.be" in message.text:
        await download_video(message.text, message)

async def main():
    db_init()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())