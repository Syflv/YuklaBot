import logging
import asyncio
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from yt_dlp import YoutubeDL

# --- SOZLAMALAR ---
API_TOKEN = '8685709263:AAFoqXZAeV7-C6mlM3UecasV86fWq4hSl0A'
ADMIN_ID = 2085230699  # O'zingizning ID raqamingizni yozing

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- MA'LUMOTLAR BAZASI ---
def db_init():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    # Foydalanuvchilar jadvali
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    # Kanallar jadvali
    cursor.execute('CREATE TABLE IF NOT EXISTS channels (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT, url TEXT)')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def get_channels():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id, url FROM channels')
    rows = cursor.fetchall()
    conn.close()
    return rows

# --- MAJBURIY OBUNA TEKSHIRUVI ---
async def check_sub(user_id):
    channels = get_channels()
    if not channels:
        return True
    
    for chat_id, url in channels:
        try:
            status = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if status.status == 'left':
                return False
        except Exception as e:
            logging.error(f"Kanalni tekshirishda xatolik ({chat_id}): {e}")
            continue # Agar bot kanalga admin bo'lmasa, o'tkazib yuboradi
    return True

def sub_keyboard(channels):
    keyboard = []
    for i, (chat_id, url) in enumerate(channels, 1):
        keyboard.append([InlineKeyboardButton(text=f"{i}-kanal", url=url)])
    keyboard.append([InlineKeyboardButton(text="Tekshirish ✅", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# --- ADMIN PANEL ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        kb = [
            [InlineKeyboardButton(text="Statistika 📊", callback_data="stats")],
            [InlineKeyboardButton(text="Reklama yuborish 📢", callback_data="broadcast")],
            [InlineKeyboardButton(text="Kanal qo'shish ➕", callback_data="add_channel")],
            [InlineKeyboardButton(text="Kanallarni tozalash 🗑", callback_data="clear_channels")]
        ]
        await message.answer("Admin panel:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "stats")
async def show_stats(call: types.CallbackQuery):
    conn = sqlite3.connect('bot_data.db')
    count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    conn.close()
    await call.message.answer(f"Bot foydalanuvchilari soni: {count} ta")

@dp.callback_query(F.data == "clear_channels")
async def clear_ch(call: types.CallbackQuery):
    conn = sqlite3.connect('bot_data.db')
    conn.execute('DELETE FROM channels')
    conn.commit()
    conn.close()
    await call.answer("Barcha kanallar o'chirildi!", show_alert=True)

@dp.callback_query(F.data == "add_channel")
async def ask_channel(call: types.CallbackQuery):
    await call.message.answer("Kanal qo'shish uchun quyidagi formatda yuboring:\n`kanal -10012345678 https://t.me/kanal_link`", parse_mode="Markdown")

@dp.message(F.text.startswith("kanal "))
async def process_add_channel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        try:
            parts = message.text.split()
            chat_id = parts[1]
            url = parts[2]
            conn = sqlite3.connect('bot_data.db')
            conn.execute('INSERT INTO channels (chat_id, url) VALUES (?, ?)', (chat_id, url))
            conn.commit()
            conn.close()
            await message.answer("Kanal muvaffaqiyatli qo'shildi!")
        except:
            await message.answer("Xato! Format: `kanal ID LINK` bo'lishi kerak.")

@dp.callback_query(F.data == "broadcast")
async def start_broadcast(call: types.CallbackQuery):
    await call.message.answer("Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni **Reply** (javob) qilib yuboring va `reklama` so'zini yozing.")

@dp.message(F.text == "reklama")
async def send_broadcast(message: types.Message):
    if message.from_user.id == ADMIN_ID and message.reply_to_message:
        conn = sqlite3.connect('bot_data.db')
        users = conn.execute('SELECT user_id FROM users').fetchall()
        conn.close()
        
        count = 0
        for (u_id,) in users:
            try:
                await message.reply_to_message.copy_to(u_id)
                count += 1
                await asyncio.sleep(0.05) # Spamga tushmaslik uchun
            except: pass
        await message.answer(f"Reklama {count} kishiga yetkazildi.")

# --- ASOSIY ISH ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    add_user(message.from_user.id)
    channels = get_channels()
    if not await check_sub(message.from_user.id):
        await message.answer("Botdan foydalanish uchun kanallarga obuna bo'ling:", reply_markup=sub_keyboard(channels))
        return
    await message.answer("Link yuboring, videoni yuklab beraman!")

@dp.callback_query(F.data == "check_sub")
async def check_sub_call(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.delete()
        await call.message.answer("Rahmat! Endi link yuborishingiz mumkin.")
    else:
        await call.answer("Hali hamma kanallarga a'zo bo'lmadingiz!", show_alert=True)

@dp.message()
async def handle_video(message: types.Message):
    if not await check_sub(message.from_user.id):
        channels = get_channels()
        await message.answer("Avval kanallarga obuna bo'ling!", reply_markup=sub_keyboard(channels))
        return

    url = message.text
    if "instagram.com" in url or "youtube.com" in url or "youtu.be" in url:
        wait_m = await message.answer("Yuklanmoqda...")
        ydl_opts = {'format': 'best[ext=mp4]/best', 'outtmpl': 'video_%(id)s.mp4', 'max_filesize': 45*1024*1024}
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                fn = ydl.prepare_filename(info)
                await message.answer_video(types.FSInputFile(fn))
                os.remove(fn)
                await wait_m.delete()
        except:
            await wait_m.edit_text("Xato: Video juda katta yoki link noto'g'ri.")

async def main():
    db_init()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
