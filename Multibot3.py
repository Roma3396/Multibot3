import asyncio
import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton, 
                            ReplyKeyboardMarkup, KeyboardButton, FSInputFile)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- KONFIGURATSIYA ---
TOKEN = "8511080877:AAEU3z1iTpaj62X6-rowkmVxLJ7iI2ZfXiQ"
ADMINS = [7829422043, 6881599988]
CHANNELS = [
    {"id": -1003155796926, "link": "https://t.me/FeaF_Helping"},
    {"id": -1003646737157, "link": "https://t.me/Disney_Multfilmlar1"} 
]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- MA'LUMOTLAR BAZASI ---
def get_db():
    conn = sqlite3.connect('films.db')
    return conn, conn.cursor()

def init_db():
    conn, c = get_db()
    c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    c.execute('''CREATE TABLE IF NOT EXISTS films 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, photo TEXT, video TEXT, name TEXT, year TEXT, code TEXT, desc TEXT, likes INTEGER DEFAULT 0)''')
    c.execute('CREATE TABLE IF NOT EXISTS favorites (user_id INTEGER, film_id INTEGER, UNIQUE(user_id, film_id))')
    c.execute('CREATE TABLE IF NOT EXISTS ratings (user_id INTEGER PRIMARY KEY, score INTEGER)')
    conn.commit(); conn.close()

init_db()

# --- STATES ---
class AdminState(StatesGroup):
    waiting_for_data = State()
    waiting_for_video = State()
    waiting_for_broadcast = State()
    waiting_for_delete_code = State()
    coll_photo = State()
    coll_name = State()
    coll_codes = State()

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
        kb.append([KeyboardButton(text="📊 Statistic"), KeyboardButton(text="📂 Backup DB")])
        kb.append([KeyboardButton(text="🗑 O'chirish")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def sub_kb():
    buttons = [[InlineKeyboardButton(text=f"{i+1}-kanalga a'zo bo'lish", url=c['link'])] for i, c in enumerate(CHANNELS)]
    buttons.append([InlineKeyboardButton(text="Tekshirish ✅", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def post_options():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="1-Oddiy post")],
        [KeyboardButton(text="2-Baholash uchun")],
        [KeyboardButton(text="3-Top filmlar")],
        [KeyboardButton(text="🔙 Orqaga")]
    ], resize_keyboard=True)

def rating_inline():
    buttons = []
    row = []
    for i in range(1, 11):
        row.append(InlineKeyboardButton(text=str(i), callback_data=f"score_{i}"))
        if i % 5 == 0:
            buttons.append(row); row = []
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- FUNKSIYALAR ---
async def check_sub(user_id):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(channel['id'], user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except: return False
    return True

async def send_film_card(chat_id, film, is_fav=False, edit=False, message_id=None):
    bot_info = await bot.get_me()
    text = f"🎬 **{film[3]}**\n\n📅 Yili: {film[4]}\n🔢 Kodi: {film[5]}\n📝 Izoh: {film[6]}\n\n❤️ {film[7]} ta like"
    
    act_btn = InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"unf_{film[0]}") if is_fav else InlineKeyboardButton(text="💾 Saqlash", callback_data=f"save_{film[0]}")
    mode = "f" if is_fav else "a"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️", callback_data=f"prev_{film[0]}_{mode}"),
         InlineKeyboardButton(text=f"❤️ {film[7]}", callback_data=f"like_{film[0]}"),
         InlineKeyboardButton(text="➡️", callback_data=f"next_{film[0]}_{mode}")],
        [act_btn,
         InlineKeyboardButton(text="🚀 Ulashish", url=f"https://t.me/share/url?url=https://t.me/{bot_info.username}?start={film[5]}")],
        [InlineKeyboardButton(text="👁 Tomosha qilish", callback_data=f"watch_{film[0]}")]
    ])
    
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
async def start(message: types.Message):
    if not await check_sub(message.from_user.id):
        await message.answer("Botdan foydalanish uchun kanallarga a'zo bo'ling!", reply_markup=sub_kb())
        return
    args = message.text.split()
    if len(args) > 1:
        conn, c = get_db(); c.execute("SELECT * FROM films WHERE code = ?", (args[1],)); film = c.fetchone(); conn.close()
        if film: await send_film_card(message.chat.id, film); return
    conn, c = get_db(); c.execute("INSERT OR IGNORE INTO users VALUES (?)", (message.from_user.id,)); conn.commit(); conn.close()
    await message.answer("Xush kelibsiz!", reply_markup=main_menu(message.from_user.id))

@dp.callback_query(F.data == "check_sub")
async def check_callback(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.delete(); await call.message.answer("Rahmat!", reply_markup=main_menu(call.from_user.id))
    else:
        await call.answer("Hali a'zo emassiz ❌", show_alert=True)

# 📢 POST JOYLASh MENU VA FUNKSIYALAR
@dp.message(F.text == "📢 Post Joylash", F.from_user.id.in_(ADMINS))
async def broad_menu(message: types.Message):
    await message.answer("Post turini tanlang:", reply_markup=post_options())

@dp.message(F.text == "1-Oddiy post", F.from_user.id.in_(ADMINS))
async def simple_post(message: types.Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_broadcast); await message.answer("Xabarni yuboring:")

@dp.message(AdminState.waiting_for_broadcast)
async def simple_send(message: types.Message, state: FSMContext):
    conn, c = get_db(); c.execute("SELECT user_id FROM users"); users = c.fetchall(); conn.close()
    for u in users:
        try: await message.copy_to(u[0])
        except: pass
    await message.answer("Xabar yuborildi!", reply_markup=main_menu(message.from_user.id)); await state.clear()

@dp.message(F.text == "2-Baholash uchun", F.from_user.id.in_(ADMINS))
async def rate_broad(message: types.Message):
    conn, c = get_db(); c.execute("SELECT user_id FROM users"); users = c.fetchall(); conn.close()
    for u in users:
        try: await bot.send_message(u[0], "Botimizni baholang:", reply_markup=rating_inline())
        except: pass
    await message.answer("Baholash xabari yuborildi!")

@dp.callback_query(F.data.startswith("score_"))
async def save_score(call: types.CallbackQuery):
    score = int(call.data.split("_")[1]); conn, c = get_db()
    c.execute("INSERT OR REPLACE INTO ratings (user_id, score) VALUES (?, ?)", (call.from_user.id, score))
    conn.commit(); conn.close()
    await call.message.edit_text(f"Rahmat! Siz {score} ball berdingiz.")

@dp.message(F.text == "3-Top filmlar", F.from_user.id.in_(ADMINS))
async def coll_start(message: types.Message, state: FSMContext):
    await state.set_state(AdminState.coll_photo); await message.answer("Toplam uchun rasm yuboring:")

@dp.message(AdminState.coll_photo, F.photo)
async def coll_get_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id); await state.set_state(AdminState.coll_name); await message.answer("Toplam nomi?")

@dp.message(AdminState.coll_name)
async def coll_get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text); await state.set_state(AdminState.coll_codes); await message.answer("Kodlarni kiriting (001,002...):")

@dp.message(AdminState.coll_codes)
async def coll_send(message: types.Message, state: FSMContext):
    d = await state.get_data(); codes_str = message.text.replace(" ", ""); conn, c = get_db()
    text = f"🌟 **{d['name']}**\n\nFilmlar toplami tayyor!"; kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Ochish 📂", callback_data=f"open_{codes_str}")]])
    c.execute("SELECT user_id FROM users"); users = c.fetchall(); conn.close()
    for u in users:
        try: await bot.send_photo(u[0], d['photo'], caption=text, reply_markup=kb, parse_mode="Markdown")
        except: pass
    await message.answer("Yuborildi!", reply_markup=main_menu(message.from_user.id)); await state.clear()

@dp.callback_query(F.data.startswith("open_"))
async def open_coll(call: types.CallbackQuery):
    code = call.data.split("_")[1].split(",")[0]; conn, c = get_db(); c.execute("SELECT * FROM films WHERE code = ?", (code,)); f = c.fetchone(); conn.close()
    if f: await call.message.delete(); await send_film_card(call.message.chat.id, f)

# 🎬 FILM JOYLASh VA O'CHIRISH
@dp.message(F.text == "🎬 Film joylash", F.from_user.id.in_(ADMINS))
async def add_film_start(message: types.Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_data); await message.answer("Rasmni va captionni yuboring (Nomi, Yili, Kodi, Izoh):")

@dp.message(AdminState.waiting_for_data, F.photo)
async def get_f_data(message: types.Message, state: FSMContext):
    lines = message.caption.split('\n')
    await state.update_data(photo=message.photo[-1].file_id, name=lines[0], year=lines[1], code=lines[2], desc="\n".join(lines[3:]))
    await state.set_state(AdminState.waiting_for_video); await message.answer("Videoni yuboring:")

@dp.message(AdminState.waiting_for_video, F.video)
async def get_f_video(message: types.Message, state: FSMContext):
    d = await state.get_data(); conn, c = get_db()
    c.execute("INSERT INTO films (photo, video, name, year, code, desc) VALUES (?,?,?,?,?,?)", (d['photo'], message.video.file_id, d['name'], d['year'], d['code'], d['desc'])); conn.commit(); conn.close()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Kanalga post ✅", callback_data="post_to_chan")]])
    await message.answer("Saqlandi!", reply_markup=kb)

@dp.callback_query(F.data == "post_to_chan")
async def post_to_chan(call: types.CallbackQuery, state: FSMContext):
    d = await state.get_data(); bot_info = await bot.get_me()
    text = f"🎬 **{d['name']}**\n🔢 Kodi: {d['code']}\n\nKo'rish uchun 👇"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👁 Ko'rish", url=f"https://t.me/{bot_info.username}?start={d['code']}")]])
    await bot.send_photo(CHANNELS[1]['id'], d['photo'], caption=text, reply_markup=kb, parse_mode="Markdown"); await call.answer("Joylandi!")

@dp.message(F.text == "🗑 O'chirish", F.from_user.id.in_(ADMINS))
async def del_cmd(message: types.Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_delete_code); await message.answer("Kod?")

@dp.message(AdminState.waiting_for_delete_code)
async def del_do(message: types.Message, state: FSMContext):
    conn, c = get_db(); c.execute("DELETE FROM films WHERE code = ?", (message.text,)); conn.commit(); conn.close()
    await message.answer("O'chirildi!"); await state.clear()

# 📊 STATISTIKA & BACKUP
@dp.message(F.text == "📊 Statistic")
async def stats_cmd(message: types.Message):
    conn, c = get_db()
    c.execute("SELECT COUNT(*) FROM users"); u = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM films"); f = c.fetchone()[0]
    c.execute("SELECT AVG(score) FROM ratings"); avg = c.fetchone()[0] or 0
    conn.close()
    await message.answer(f"📊 Statistika:\n👤 Userlar: {u}\n🎬 Filmlar: {f}\n⭐ Reyting: {round(avg,1)}")

@dp.message(F.text == "📂 Backup DB", F.from_user.id.in_(ADMINS))
async def backup_cmd(message: types.Message):
    if os.path.exists("films.db"):
        await message.answer_document(FSInputFile("films.db"), caption="Baza nusxasi 📂")

# 💾 SAQLANGANLAR & REK
@dp.message(F.text == "💾 Saqlangan")
async def saved_cmd(message: types.Message):
    conn, c = get_db()
    c.execute("""SELECT f.* FROM films f JOIN favorites fav ON f.id = fav.film_id 
                 WHERE fav.user_id = ? ORDER BY f.id DESC LIMIT 1""", (message.from_user.id,))
    f = c.fetchone(); conn.close()
    if f: await send_film_card(message.chat.id, f, is_fav=True)
    else: await message.answer("Saqlangan filmlar yo'q.")

@dp.message(F.text == "🔥 Rek")
async def rek_cmd(message: types.Message):
    conn, c = get_db(); c.execute("SELECT * FROM films ORDER BY RANDOM() LIMIT 1"); f = c.fetchone(); conn.close()
    if f: await send_film_card(message.chat.id, f)

# 🔍 QIDIRUV & MUROJAT
@dp.message(F.text == "🔍 Qidiruv")
async def search_cmd(message: types.Message, state: FSMContext):
    await state.set_state(UserState.waiting_for_search); await message.answer("Film nomi yoki kodi?")

@dp.message(UserState.waiting_for_search)
async def search_do(message: types.Message, state: FSMContext):
    conn, c = get_db(); c.execute("SELECT * FROM films WHERE name LIKE ? OR code = ?", (f"%{message.text}%", message.text)); f = c.fetchone(); conn.close()
    if f: await send_film_card(message.chat.id, f); await state.clear()
    else: await message.answer("Topilmadi.")

@dp.message(F.text == "📩 Murojat")
async def supp_cmd(message: types.Message, state: FSMContext):
    await state.set_state(UserState.waiting_for_support); await message.answer("Xabaringizni yozing:")

@dp.message(UserState.waiting_for_support)
async def supp_do(message: types.Message, state: FSMContext):
    for a in ADMINS:
        try: await bot.send_message(a, f"📩 Murojat:\n{message.text}\nID: {message.from_user.id}")
        except: pass
    await message.answer("Yuborildi!"); await state.clear()

# CALLBACK ACTIONS (LIKE, SAVE, WATCH, NAVIGATE, UNFOLLOW)
@dp.callback_query(F.data.startswith(("next_", "prev_", "like_", "save_", "watch_", "unf_")))
async def act_do(call: types.CallbackQuery):
    if not await check_sub(call.from_user.id): await call.answer("Obuna bo'ling!", True); return
    data = call.data.split("_"); act = data[0]; val = data[1]; conn, c = get_db()
    
    if act == "watch":
        c.execute("SELECT video FROM films WHERE id = ?", (val,)); v = c.fetchone()
        if v: await bot.send_video(call.message.chat.id, v[0], protect_content=True)
    elif act == "like":
        c.execute("UPDATE films SET likes = likes + 1 WHERE id = ?", (val,)); conn.commit(); await call.answer("❤️")
    elif act == "save":
        try: c.execute("INSERT INTO favorites VALUES (?, ?)", (call.from_user.id, val)); conn.commit(); await call.answer("Saqlandi!")
        except: await call.answer("Oldin saqlangan!", True)
    elif act == "unf":
        c.execute("DELETE FROM favorites WHERE user_id = ? AND film_id = ?", (call.from_user.id, val)); conn.commit()
        await call.message.delete(); await call.answer("O'chirildi! 🗑")
    elif act in ["next", "prev"]:
        mode = data[2]; s = ">" if act == "next" else "<"; o = "ASC" if act == "next" else "DESC"
        if mode == "f":
            c.execute(f"SELECT f.* FROM films f JOIN favorites fav ON f.id = fav.film_id WHERE fav.user_id = ? AND f.id {s} ? ORDER BY f.id {o} LIMIT 1", (call.from_user.id, val))
        else:
            c.execute(f"SELECT * FROM films WHERE id {s} ? ORDER BY id {o} LIMIT 1", (val,))
        f = c.fetchone()
        if f: await send_film_card(call.message.chat.id, f, is_fav=(mode=="f"), edit=True, message_id=call.message.message_id)
        else: await call.answer("Oxiri!", True)
    conn.close()

@dp.message(F.text == "🔙 Orqaga")
async def back_cmd(message: types.Message, state: FSMContext):
    await state.clear(); await message.answer("Asosiy menyu", reply_markup=main_menu(message.from_user.id))

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
                   
