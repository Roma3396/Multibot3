import asyncio
import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- KONFIGURATSIYA ---
TOKEN = os.getenv("BOT_TOKEN", "8511080877:AAF44psWL5zdY7Mdomi03e1rojguMwWG7zg")
ADMINS = [7829422043, 6881599988]
CHANNEL_ID = -1003155796926
CHANNEL_LINK = "https://t.me/FeaF_Helping"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect('films.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS films 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, photo TEXT, video TEXT, name TEXT, year TEXT, code TEXT, desc TEXT, likes INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS favorites (user_id INTEGER, film_id INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ratings (user_id INTEGER PRIMARY KEY, score INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# --- STATES ---
class AdminState(StatesGroup):
    waiting_for_data = State()
    waiting_for_video = State()
    waiting_for_post = State()
    waiting_for_coll_name = State()
    waiting_for_coll_codes = State()
    waiting_for_delete_code = State() # O'chirish uchun yangi state

class UserState(StatesGroup):
    waiting_for_search = State()
    waiting_for_support = State()

# --- KEYBOARDS ---
def main_menu(user_id):
    kb = [
        [KeyboardButton(text="🔍 Qidiruv"), KeyboardButton(text="🔥 Rek")],
        [KeyboardButton(text="💾 Saqlangan"), KeyboardButton(text="📩 Murojat")]
    ]
    if user_id in ADMINS:
        kb.append([KeyboardButton(text="🎬 Film joylash"), KeyboardButton(text="📢 Post Joylash")])
        kb.append([KeyboardButton(text="📊 Statistic"), KeyboardButton(text="🗑 O'chirish")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def post_menu():
    kb = [
        [KeyboardButton(text="1-Oddiy post")],
        [KeyboardButton(text="2-Baho uchun")],
        [KeyboardButton(text="3-Top filmlar")],
        [KeyboardButton(text="🔙 Orqaga")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def rating_kb():
    buttons = []
    row = []
    for i in range(1, 11):
        row.append(InlineKeyboardButton(text=str(i), callback_data=f"rate_{i}"))
        if i % 5 == 0:
            buttons.append(row)
            row = []
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Orqaga")]], resize_keyboard=True)

def sub_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Kanalga o'tish", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="Tasdiqlash ✅", callback_data="check_sub")]
    ])

# --- FUNKSIYALAR ---
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["creator", "administrator", "member"]
    except: return False

async def send_film_card(chat_id, film):
    text = f"🎬 **{film[3]}**\n\n📅 Yili: {film[4]}\n🔢 Kodi: {film[5]}\n📝 Izoh: {film[6]}\n\n❤️ {film[7]} ta like"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Chapga", callback_data=f"prev_{film[0]}"),
         InlineKeyboardButton(text=f"❤️ {film[7]}", callback_data=f"like_{film[0]}"),
         InlineKeyboardButton(text="💾 Saqlash", callback_data=f"save_{film[0]}"),
         InlineKeyboardButton(text="➡️ O'nga", callback_data=f"next_{film[0]}")],
        [InlineKeyboardButton(text="👁 Tomosha qilish", callback_data=f"watch_{film[0]}")]
    ])
    await bot.send_photo(chat_id, film[1], caption=text, reply_markup=kb, parse_mode="Markdown")

# --- HANDLERS ---
@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    conn = sqlite3.connect('films.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?)", (message.from_user.id,))
    conn.commit()
    conn.close()
    if await check_sub(message.from_user.id):
        await message.answer(f"Salom {message.from_user.full_name}! Botga xush kelibsiz 🎥", reply_markup=main_menu(message.from_user.id))
    else:
        await message.answer("Botdan foydalanish uchun kanalga obuna bo'ling!", reply_markup=sub_kb())

# --- O'CHIRISH FUNKSIYASI ---
@dp.message(F.text == "🗑 O'chirish", F.from_user.id.in_(ADMINS))
async def delete_start(message: types.Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_delete_code)
    await message.answer("O'chirmoqchi bo'lgan filmingiz kodini yuboring:", reply_markup=back_kb())

@dp.message(AdminState.waiting_for_delete_code)
async def delete_process(message: types.Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await state.clear()
        await message.answer("Asosiy menyu", reply_markup=main_menu(message.from_user.id))
        return
    
    code = message.text.strip()
    conn = sqlite3.connect('films.db')
    c = conn.cursor()
    c.execute("SELECT * FROM films WHERE code = ?", (code,))
    film = c.fetchone()
    
    if film:
        c.execute("DELETE FROM films WHERE code = ?", (code,))
        c.execute("DELETE FROM favorites WHERE film_id = ?", (film[0],))
        conn.commit()
        await message.answer(f"✅ Film (Kod: {code}) muvaffaqiyatli o'chirildi!", reply_markup=main_menu(message.from_user.id))
        await state.clear()
    else:
        await message.answer("❌ Bunday kodli film topilmadi. Qaytadan urinib ko'ring:")
    conn.close()

# --- STATISTIKA ---
@dp.message(F.text == "📊 Statistic", F.from_user.id.in_(ADMINS))
async def show_stats(message: types.Message):
    conn = sqlite3.connect('films.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    u_count = c.fetchone()[0]
    c.execute("SELECT name, likes FROM films ORDER BY likes DESC LIMIT 3")
    top_films = c.fetchall()
    c.execute("SELECT AVG(score), COUNT(*) FROM ratings")
    rating_data = c.fetchone()
    avg_score = round(rating_data[0], 1) if rating_data[0] else 0
    raters = rating_data[1]
    conn.close()
    
    text = f"📊 **Bot statistikasi:**\n\n👥 Foydalanuvchilar: {u_count} ta\n⭐ Bot reytingi: {avg_score}/10 ({raters} kishi)\n\n🏆 **Top 3 film:**\n"
    for i, f in enumerate(top_films, 1): text += f"{i}. {f[0]} — {f[1]} ❤️\n"
    await message.answer(text, parse_mode="Markdown")

# --- POST TIZIMI ---
@dp.message(F.text == "📢 Post Joylash", F.from_user.id.in_(ADMINS))
async def post_options(message: types.Message):
    await message.answer("Post turini tanlang:", reply_markup=post_menu())

@dp.message(F.text == "1-Oddiy post", F.from_user.id.in_(ADMINS))
async def simple_post(message: types.Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_post)
    await message.answer("Hohlagan postni yuboring:", reply_markup=back_kb())

@dp.message(F.text == "2-Baho uchun", F.from_user.id.in_(ADMINS))
async def rate_post(message: types.Message):
    conn = sqlite3.connect('films.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    for u in users:
        try: await bot.send_message(u[0], "Salom, bot sizga yoqyaptimi? Baho bering:", reply_markup=rating_kb())
        except: pass
    await message.answer("Baho posti yuborildi!")

@dp.callback_query(F.data.startswith("rate_"))
async def handle_rating(call: types.CallbackQuery):
    score = int(call.data.split("_")[1])
    conn = sqlite3.connect('films.db')
    c = conn.cursor()
    c.execute("SELECT * FROM ratings WHERE user_id = ?", (call.from_user.id,))
    if c.fetchone(): await call.answer("Siz baho bergansiz! 😊", show_alert=True)
    else:
        c.execute("INSERT INTO ratings VALUES (?, ?)", (call.from_user.id, score))
        conn.commit()
        await call.message.edit_text(f"Rahmat! Bahoyingiz: {score}")
    conn.close()

@dp.message(F.text == "3-Top filmlar", F.from_user.id.in_(ADMINS))
async def collection_start(message: types.Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_coll_name)
    await message.answer("To'plam nomi (Masalan: Yangi yil):", reply_markup=back_kb())

@dp.message(AdminState.waiting_for_coll_name)
async def coll_name(message: types.Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await state.clear()
        await message.answer("Menyu", reply_markup=main_menu(message.from_user.id))
        return
    await state.update_data(c_name=message.text)
    await state.set_state(AdminState.waiting_for_coll_codes)
    await message.answer("Filmlar kodlari (001/002/003):", reply_markup=back_kb())

@dp.message(AdminState.waiting_for_coll_codes)
async def coll_codes(message: types.Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await state.clear()
        await message.answer("Menyu", reply_markup=main_menu(message.from_user.id))
        return
    data = await state.get_data()
    codes = message.text.split('/')
    conn = sqlite3.connect('films.db')
    c = conn.cursor()
    found_films = []
    for code in codes:
        c.execute("SELECT * FROM films WHERE code = ?", (code.strip(),))
        f = c.fetchone()
        if f: found_films.append(f)
    conn.close()

    if not found_films:
        await message.answer("Kodlar topilmadi. Qayta urinib ko'ring:")
        return

    conn = sqlite3.connect('films.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()

    for u in users:
        try:
            await bot.send_message(u[0], f"✨ **{data['c_name']}** ✨")
            for film in found_films: await send_film_card(u[0], film)
        except: pass
    await message.answer("Yuborildi!", reply_markup=main_menu(message.from_user.id))
    await state.clear()

# --- FILM JOYLASH ---
@dp.message(F.text == "🎬 Film joylash", F.from_user.id.in_(ADMINS))
async def add_film_start(message: types.Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_data)
    await message.answer("Rasm + Nomi\\nYili\\nKodi\\nIzoh yuboring:", reply_markup=back_kb())

@dp.message(AdminState.waiting_for_data, F.photo)
async def get_data(message: types.Message, state: FSMContext):
    if not message.caption: return
    lines = message.caption.split('\n')
    if len(lines) < 4: return
    await state.update_data(photo=message.photo[-1].file_id, name=lines[0], year=lines[1], code=lines[2], desc="\n".join(lines[3:]))
    await state.set_state(AdminState.waiting_for_video)
    await message.answer("Video yuboring:")

@dp.message(AdminState.waiting_for_video, F.video)
async def get_video(message: types.Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect('films.db')
    c = conn.cursor()
    c.execute("INSERT INTO films (photo, video, name, year, code, desc) VALUES (?,?,?,?,?,?)",
              (data['photo'], message.video.file_id, data['name'], data['year'], data['code'], data['desc']))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer("Saqlandi!", reply_markup=main_menu(message.from_user.id))

# --- TUGMALAR ISHLASHI ---
@dp.callback_query(F.data.startswith(("next_", "prev_", "like_", "save_", "watch_")))
async def film_actions(call: types.CallbackQuery):
    action, f_id = call.data.split("_")
    conn = sqlite3.connect('films.db')
    c = conn.cursor()
    
    if action == "like":
        c.execute("UPDATE films SET likes = likes + 1 WHERE id = ?", (f_id,))
        conn.commit()
        await call.answer("❤️")
    elif action == "save":
        c.execute("INSERT OR IGNORE INTO favorites VALUES (?, ?)", (call.from_user.id, f_id))
        conn.commit()
        await call.answer("Saqlandi! 💾")
    elif action == "watch":
        c.execute("SELECT video FROM films WHERE id = ?", (f_id,))
        v = c.fetchone()
        if v: await bot.send_video(call.message.chat.id, v[0])
        await call.answer()
    elif action in ["next", "prev"]:
        if action == "next": c.execute("SELECT * FROM films WHERE id < ? ORDER BY id DESC LIMIT 1", (f_id,))
        else: c.execute("SELECT * FROM films WHERE id > ? ORDER BY id ASC LIMIT 1", (f_id,))
        film = c.fetchone()
        if film:
            text = f"🎬 **{film[3]}**\n\n📅 Yili: {film[4]}\n🔢 Kodi: {film[5]}\n📝 Izoh: {film[6]}\n\n❤️ {film[7]} ta like"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Chapga", callback_data=f"prev_{film[0]}"),
                 InlineKeyboardButton(text=f"❤️ {film[7]}", callback_data=f"like_{film[0]}"),
                 InlineKeyboardButton(text="💾 Saqlash", callback_data=f"save_{film[0]}"),
                 InlineKeyboardButton(text="➡️ O'nga", callback_data=f"next_{film[0]}")],
                [InlineKeyboardButton(text="👁 Tomosha qilish", callback_data=f"watch_{film[0]}")]
            ])
            await call.message.edit_media(types.InputMediaPhoto(media=film[1], caption=text, parse_mode="Markdown"), reply_markup=kb)
        else:
            await call.answer("Boshqa film yo'q!", show_alert=True)
    conn.close()

# --- QIDIRUV VA BOSHQA ---
@dp.message(F.text == "🔍 Qidiruv")
async def search_start(message: types.Message, state: FSMContext):
    await state.set_state(UserState.waiting_for_search)
    await message.answer("Nom yoki kodni yozing:", reply_markup=back_kb())

@dp.message(UserState.waiting_for_search)
async def search_result(message: types.Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await state.clear()
        await message.answer("Menyu", reply_markup=main_menu(message.from_user.id))
        return
    q = message.text.strip()
    conn = sqlite3.connect('films.db')
    c = conn.cursor()
    c.execute("SELECT * FROM films WHERE name LIKE ? OR code = ?", (f'%{q}%', q))
    film = c.fetchone()
    conn.close()
    if film: await send_film_card(message.chat.id, film)
    else: await message.answer("Topilmadi.")

@dp.message(F.text == "🔥 Rek")
async def show_rek(message: types.Message):
    conn = sqlite3.connect('films.db')
    c = conn.cursor()
    c.execute("SELECT * FROM films ORDER BY id DESC LIMIT 1")
    film = c.fetchone()
    conn.close()
    if film: await send_film_card(message.chat.id, film)

@dp.message(F.text == "💾 Saqlangan")
async def show_saved(message: types.Message):
    conn = sqlite3.connect('films.db')
    c = conn.cursor()
    c.execute("SELECT f.* FROM films f JOIN favorites fav ON f.id = fav.film_id WHERE fav.user_id = ?", (message.from_user.id,))
    films = c.fetchall()
    conn.close()
    if films:
        for f in films: await send_film_card(message.chat.id, f)
    else: await message.answer("Bo'sh.")

@dp.message(AdminState.waiting_for_post)
async def broadcast_simple(message: types.Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await state.clear()
        await message.answer("Asosiy menyu", reply_markup=main_menu(message.from_user.id))
        return
    conn = sqlite3.connect('films.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    for u in users:
        try: await message.copy_to(u[0])
        except: pass
    await message.answer("Post tarqatildi!", reply_markup=main_menu(message.from_user.id))
    await state.clear()

@dp.message(F.text == "🔙 Orqaga")
async def back_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Asosiy menyu", reply_markup=main_menu(message.from_user.id))

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
