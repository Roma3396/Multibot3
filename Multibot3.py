import asyncio
import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import web

# --- KONFIGURATSIYA ---
TOKEN = os.getenv("BOT_TOKEN", "8511080877:AAEVEy9tBlEoNtsT_5kOex4KdcSO-iwSw4g")
ADMINS = [7829422043, 6881599988]
CHANNEL_ID = -1003155796926
CHANNEL_LINK = "https://t.me/FeaF_Helping"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- RENDER VEB-SERVER (24/7 UCHUN) ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, '0.0.0.0', port).start()

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect('films.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    c.execute('''CREATE TABLE IF NOT EXISTS films 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, photo TEXT, video TEXT, name TEXT, year TEXT, code TEXT, desc TEXT, likes INTEGER DEFAULT 0)''')
    c.execute('CREATE TABLE IF NOT EXISTS favorites (user_id INTEGER, film_id INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS ratings (user_id INTEGER PRIMARY KEY, score INTEGER)')
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
    waiting_for_delete_code = State()

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
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="1-Oddiy post")],
        [KeyboardButton(text="2-Baho uchun")],
        [KeyboardButton(text="3-Top filmlar")],
        [KeyboardButton(text="🔙 Orqaga")]
    ], resize_keyboard=True)

def rating_kb():
    buttons = []
    row = []
    for i in range(1, 11):
        row.append(InlineKeyboardButton(text=str(i), callback_data=f"rate_{i}"))
        if i % 5 == 0:
            buttons.append(row); row = []
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Orqaga")]], resize_keyboard=True)

def get_film_kb(film_id, likes):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Chapga", callback_data=f"prev_{film_id}"),
         InlineKeyboardButton(text=f"❤️ {likes}", callback_data=f"like_{film_id}"),
         InlineKeyboardButton(text="💾 Saqlash", callback_data=f"save_{film_id}"),
         InlineKeyboardButton(text="➡️ O'nga", callback_data=f"next_{film_id}")],
        [InlineKeyboardButton(text="👁 Tomosha qilish", callback_data=f"watch_{film_id}")]
    ])

# --- FUNKSIYALAR ---
async def send_film_card(chat_id, film, edit=False, message_id=None):
    text = f"🎬 **{film[3]}**\n\n📅 Yili: {film[4]}\n🔢 Kodi: {film[5]}\n📝 Izoh: {film[6]}\n\n❤️ {film[7]} ta like"
    kb = get_film_kb(film[0], film[7])
    if edit and message_id:
        try:
            await bot.edit_message_media(
                chat_id=chat_id, message_id=message_id,
                media=types.InputMediaPhoto(media=film[1], caption=text, parse_mode="Markdown"),
                reply_markup=kb
            )
        except: pass
    else:
        await bot.send_photo(chat_id, film[1], caption=text, reply_markup=kb, parse_mode="Markdown")

# --- HANDLERS ---
@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    conn = sqlite3.connect('films.db'); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?)", (message.from_user.id,))
    conn.commit(); conn.close()
    await message.answer(f"Xush kelibsiz! Filmlar olami 🎥", reply_markup=main_menu(message.from_user.id))

# 🔥 REK (REELS USLUBI)
@dp.message(F.text == "🔥 Rek")
async def show_rek(message: types.Message):
    conn = sqlite3.connect('films.db'); c = conn.cursor()
    c.execute("SELECT * FROM films ORDER BY id DESC LIMIT 1"); film = c.fetchone()
    conn.close()
    if film: await send_film_card(message.chat.id, film)
    else: await message.answer("Filmlar hali yo'q.")

# 🔍 QIDIRUV
@dp.message(F.text == "🔍 Qidiruv")
async def search_start(message: types.Message, state: FSMContext):
    await state.set_state(UserState.waiting_for_search)
    await message.answer("Film nomi yoki kodini yozing:", reply_markup=back_kb())

@dp.message(UserState.waiting_for_search)
async def search_res(message: types.Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await state.clear(); await message.answer("Menyu", reply_markup=main_menu(message.from_user.id)); return
    conn = sqlite3.connect('films.db'); c = conn.cursor()
    c.execute("SELECT * FROM films WHERE name LIKE ? OR code = ?", (f'%{message.text}%', message.text))
    film = c.fetchone(); conn.close()
    if film: await send_film_card(message.chat.id, film)
    else: await message.answer("Hech narsa topilmadi.")

# 📩 MUROJAT
@dp.message(F.text == "📩 Murojat")
async def support_start(message: types.Message, state: FSMContext):
    await state.set_state(UserState.waiting_for_support)
    await message.answer("Adminlarga xabaringizni yozing:", reply_markup=back_kb())

@dp.message(UserState.waiting_for_support)
async def support_send(message: types.Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await state.clear(); await message.answer("Menyu", reply_markup=main_menu(message.from_user.id)); return
    for admin in ADMINS:
        try: await bot.send_message(admin, f"📩 YANGI MUROJAT:\nKimdan: {message.from_user.full_name}\nID: {message.from_user.id}\nXabar: {message.text}")
        except: pass
    await message.answer("Xabaringiz adminga yuborildi! ✅", reply_markup=main_menu(message.from_user.id))
    await state.clear()

# 💾 SAQLANGANLAR
@dp.message(F.text == "💾 Saqlangan")
async def show_saved(message: types.Message):
    conn = sqlite3.connect('films.db'); c = conn.cursor()
    c.execute("SELECT f.* FROM films f JOIN favorites fav ON f.id = fav.film_id WHERE fav.user_id = ?", (message.from_user.id,))
    films = c.fetchall(); conn.close()
    if films:
        for f in films: await send_film_card(message.chat.id, f)
    else: await message.answer("Sizda hali saqlangan filmlar yo'q.")

# 🎬 FILM JOYLASh (ADMIN)
@dp.message(F.text == "🎬 Film joylash", F.from_user.id.in_(ADMINS))
async def add_film(message: types.Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_data)
    await message.answer("Film rasmini yuboring (Captionda: Nomi, Yili, Kodi, Izoh):", reply_markup=back_kb())

@dp.message(AdminState.waiting_for_data, F.photo)
async def get_f_data(message: types.Message, state: FSMContext):
    if not message.caption: await message.answer("Caption yozish esdan chiqdi!"); return
    lines = message.caption.split('\n')
    if len(lines) < 4: await message.answer("Format xato! Kamida 4 qator bo'lsin."); return
    await state.update_data(photo=message.photo[-1].file_id, name=lines[0], year=lines[1], code=lines[2], desc="\n".join(lines[3:]))
    await state.set_state(AdminState.waiting_for_video); await message.answer("Endi video yuboring:")

@dp.message(AdminState.waiting_for_video, F.video)
async def get_f_video(message: types.Message, state: FSMContext):
    d = await state.get_data(); conn = sqlite3.connect('films.db'); c = conn.cursor()
    c.execute("INSERT INTO films (photo, video, name, year, code, desc) VALUES (?,?,?,?,?,?)", (d['photo'], message.video.file_id, d['name'], d['year'], d['code'], d['desc']))
    conn.commit(); conn.close(); await state.clear()
    await message.answer("Film bazaga qo'shildi! ✅", reply_markup=main_menu(message.from_user.id))

# 📢 POST JOYLASh (ADMIN)
@dp.message(F.text == "📢 Post Joylash", F.from_user.id.in_(ADMINS))
async def post_options(message: types.Message):
    await message.answer("Post turini tanlang:", reply_markup=post_menu())

@dp.message(F.text == "1-Oddiy post", F.from_user.id.in_(ADMINS))
async def simple_post(message: types.Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_post)
    await message.answer("Barcha userlarga yuboriladigan postni (rasm, video yoki matn) yuboring:", reply_markup=back_kb())

@dp.message(AdminState.waiting_for_post)
async def broadcast_post(message: types.Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await state.clear(); await message.answer("Admin menyu", reply_markup=main_menu(message.from_user.id)); return
    conn = sqlite3.connect('films.db'); c = conn.cursor(); c.execute("SELECT user_id FROM users"); users = c.fetchall(); conn.close()
    for u in users:
        try: await message.copy_to(u[0])
        except: pass
    await message.answer("Post hammaga yuborildi! ✅", reply_markup=main_menu(message.from_user.id))
    await state.clear()

@dp.message(F.text == "2-Baho uchun", F.from_user.id.in_(ADMINS))
async def rating_post(message: types.Message):
    conn = sqlite3.connect('films.db'); c = conn.cursor(); c.execute("SELECT user_id FROM users"); users = c.fetchall(); conn.close()
    for u in users:
        try: await bot.send_message(u[0], "Botimiz sizga yoqyaptimi? Baho bering:", reply_markup=rating_kb())
        except: pass
    await message.answer("Baho posti yuborildi!")

@dp.message(F.text == "3-Top filmlar", F.from_user.id.in_(ADMINS))
async def top_coll_start(message: types.Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_coll_name)
    await message.answer("To'plam nomi (masalan: Haftaning top filmlari):", reply_markup=back_kb())

@dp.message(AdminState.waiting_for_coll_name)
async def top_coll_codes(message: types.Message, state: FSMContext):
    if message.text == "🔙 Orqaga": await state.clear(); await message.answer("Menyu", reply_markup=main_menu(message.from_user.id)); return
    await state.update_data(c_name=message.text)
    await state.set_state(AdminState.waiting_for_coll_codes)
    await message.answer("Filmlar kodlarini '/' bilan yuboring (masalan: 001/005/012):")

@dp.message(AdminState.waiting_for_coll_codes)
async def top_coll_send(message: types.Message, state: FSMContext):
    data = await state.get_data(); codes = message.text.split('/')
    conn = sqlite3.connect('films.db'); c = conn.cursor()
    films = []
    for code in codes:
        c.execute("SELECT * FROM films WHERE code = ?", (code.strip(),))
        f = c.fetchone()
        if f: films.append(f)
    c.execute("SELECT user_id FROM users"); users = c.fetchall(); conn.close()
    for u in users:
        try:
            await bot.send_message(u[0], f"🌟 **{data['c_name']}** 🌟")
            for f in films: await send_film_card(u[0], f)
        except: pass
    await message.answer("To'plam yuborildi!", reply_markup=main_menu(message.from_user.id))
    await state.clear()

# 📊 STATISTIKA
@dp.message(F.text == "📊 Statistic", F.from_user.id.in_(ADMINS))
async def stats(message: types.Message):
    conn = sqlite3.connect('films.db'); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users"); u = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM films"); f = c.fetchone()[0]
    c.execute("SELECT AVG(score) FROM ratings"); r = c.fetchone()[0] or 0
    conn.close()
    await message.answer(f"📊 **Statistika:**\n\n👤 Userlar: {u}\n🎬 Filmlar: {f}\n⭐ Reyting: {round(r, 1)}/10")

# 🗑 O'CHIRISH
@dp.message(F.text == "🗑 O'chirish", F.from_user.id.in_(ADMINS))
async def del_start(message: types.Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_delete_code)
    await message.answer("O'chirmoqchi bo'lgan film kodini yuboring:", reply_markup=back_kb())

@dp.message(AdminState.waiting_for_delete_code)
async def del_process(message: types.Message, state: FSMContext):
    if message.text == "🔙 Orqaga": await state.clear(); await message.answer("Menyu", reply_markup=main_menu(message.from_user.id)); return
    conn = sqlite3.connect('films.db'); c = conn.cursor()
    c.execute("DELETE FROM films WHERE code = ?", (message.text.strip(),))
    conn.commit(); conn.close()
    await message.answer("Film o'chirildi! ✅", reply_markup=main_menu(message.from_user.id)); await state.clear()

# CALLBACK ACTIONS (Like, Save, Watch, Varaqlash)
@dp.callback_query(F.data.startswith(("next_", "prev_", "like_", "save_", "watch_", "rate_")))
async def call_handlers(call: types.CallbackQuery):
    data = call.data.split("_")
    action = data[0]; val = data[1]
    conn = sqlite3.connect('films.db'); c = conn.cursor()
    
    if action == "next":
        c.execute("SELECT * FROM films WHERE id < ? ORDER BY id DESC LIMIT 1", (val,))
        f = c.fetchone()
        if f: await send_film_card(call.message.chat.id, f, True, call.message.message_id)
        else: await call.answer("Oxirgi film!", show_alert=True)
    elif action == "prev":
        c.execute("SELECT * FROM films WHERE id > ? ORDER BY id ASC LIMIT 1", (val,))
        f = c.fetchone()
        if f: await send_film_card(call.message.chat.id, f, True, call.message.message_id)
        else: await call.answer("Siz birinchi filmdasiz!", show_alert=True)
    elif action == "like":
        c.execute("UPDATE films SET likes = likes + 1 WHERE id = ?", (val,))
        conn.commit(); await call.answer("❤️")
    elif action == "save":
        c.execute("INSERT OR IGNORE INTO favorites VALUES (?, ?)", (call.from_user.id, val))
        conn.commit(); await call.answer("Saqlandi! 💾")
    elif action == "watch":
        c.execute("SELECT video FROM films WHERE id = ?", (val,))
        v = c.fetchone()
        if v: await bot.send_video(call.message.chat.id, v[0])
    elif action == "rate":
        c.execute("INSERT OR REPLACE INTO ratings VALUES (?, ?)", (call.from_user.id, int(val)))
        conn.commit(); await call.message.edit_text(f"Rahmat! Siz {val} ball berdingiz.")
    conn.close()

@dp.message(F.text == "🔙 Orqaga")
async def global_back(message: types.Message, state: FSMContext):
    await state.clear(); await message.answer("Asosiy menyu", reply_markup=main_menu(message.from_user.id))

async def main():
    asyncio.create_task(start_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
