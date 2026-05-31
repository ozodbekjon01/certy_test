import asyncio
import sqlite3
import aiosqlite
import hmac
import hashlib
import time
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, CallbackQuery
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart, Command
from werkzeug.security import generate_password_hash

# =========================
# CONFIG
# =========================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DB_PATH = "database.db"
SITE_URL = "https://ustoznext.uz"
SECRET_KEY = os.environ.get("SECRET_KEY", "")
ADMIN_ID = 6471394705
CARD_NUMBER = "8600 1234 5678 9012"

# =========================
# FSM
# =========================

class RegisterState(StatesGroup):
    waiting_username = State()
    waiting_password = State()

class PaymentState(StatesGroup):
    waiting_for_receipt = State()

# =========================
# BOT
# =========================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# =========================
# HELPERS
# =========================

def _make_login_url(username: str) -> str:
    ts = int(time.time())
    token = hmac.new(SECRET_KEY.encode(), f"{username}:{ts}".encode(), hashlib.sha256).hexdigest()
    return f"{SITE_URL}/auth/url_login/{username}?token={token}&ts={ts}"

def main_menu_kb(has_account: bool) -> InlineKeyboardMarkup:
    if has_account:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🖥 Kabinetni ochish", callback_data="open_cabinet")],
            [
                InlineKeyboardButton(text="📦 Tariflar", callback_data="show_offers"),
                InlineKeyboardButton(text="📁 Xaridlarim", callback_data="my_contracts"),
            ],
            [
                InlineKeyboardButton(text="📊 Statistika", callback_data="my_stats"),
                InlineKeyboardButton(text="❓ Yordam", callback_data="help"),
            ],
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Ro'yxatdan o'tish", callback_data="start_register")],
            [InlineKeyboardButton(text="❓ Yordam", callback_data="help")],
        ])

async def get_user(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, username FROM users WHERE tg_id=?", (tg_id,))
        return await cur.fetchone()

# =========================
# /start
# =========================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    name = message.from_user.first_name or "Foydalanuvchi"

    # Deep link: /start offers — to'g'ridan tariflar sahifasiga
    payload = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    if payload == "offers" and user:
        await message.answer("📦 Mavjud tariflar:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Tariflarni ko'rish", callback_data="show_offers")]
        ]))
        return

    if user:
        text = (
            f"👋 Xush kelibsiz, <b>{name}</b>!\n\n"
            f"🎓 <b>IC3 GS6 Test Platformasi</b>\n\n"
            f"Quyidagi menyudan foydalaning:"
        )
    else:
        text = (
            f"👋 Salom, <b>{name}</b>!\n\n"
            f"🎓 <b>IC3 GS6 Test Platformasiga xush kelibsiz!</b>\n\n"
            f"IC3 (Internet and Computing Core Certification) — bu xalqaro tan olingan "
            f"kompyuter savodxonligi sertifikati.\n\n"
            f"Platformadan foydalanish uchun avval ro'yxatdan o'ting:"
        )

    await message.answer(text, parse_mode="HTML", reply_markup=main_menu_kb(bool(user)))

# =========================
# REGISTER FSM
# =========================

@dp.callback_query(F.data == "start_register")
async def cb_start_register(call: CallbackQuery, state: FSMContext):
    user = await get_user(call.from_user.id)
    if user:
        await call.answer("Siz allaqachon ro'yxatdan o'tgansiz!", show_alert=True)
        return
    await call.message.answer("📝 Ro'yxatdan o'tish\n\nIltimos, <b>login</b> kiriting (faqat lotin harflari va raqamlar):", parse_mode="HTML")
    await state.set_state(RegisterState.waiting_username)
    await call.answer()

@dp.message(RegisterState.waiting_username)
async def reg_username(message: Message, state: FSMContext):
    username = message.text.strip()
    if not username.isalnum() or len(username) < 3:
        await message.answer("❌ Login kamida 3 ta belgi bo'lishi va faqat harf/raqamdan iborat bo'lishi kerak. Qayta kiriting:")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM users WHERE username=?", (username,))
        if await cur.fetchone():
            await message.answer("❌ Bu login band. Boshqa login kiriting:")
            return
    await state.update_data(username=username)
    await message.answer(f"✅ Login: <b>{username}</b>\n\nEndi <b>parol</b> kiriting (kamida 6 ta belgi):", parse_mode="HTML")
    await state.set_state(RegisterState.waiting_password)

@dp.message(RegisterState.waiting_password)
async def reg_password(message: Message, state: FSMContext):
    password = message.text.strip()
    if len(password) < 6:
        await message.answer("❌ Parol kamida 6 ta belgi bo'lishi kerak. Qayta kiriting:")
        return
    data = await state.get_data()
    username = data["username"]
    tg_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO users (username, tg_id, password_hash, role) VALUES (?, ?, ?, ?)",
            (username, tg_id, generate_password_hash(password), "user")
        )
        await db.commit()
    await state.clear()
    # Parolni o'chirish (xavfsizlik)
    await message.delete()
    await message.answer(
        f"🎉 <b>Muvaffaqiyatli ro'yxatdan o'tdingiz!</b>\n\n"
        f"👤 Login: <code>{username}</code>\n"
        f"🔑 Parolingizni eslab qoling!\n\n"
        f"Endi kabinetga kirishingiz mumkin:",
        parse_mode="HTML",
        reply_markup=main_menu_kb(True)
    )

# =========================
# CABINET
# =========================

@dp.callback_query(F.data == "open_cabinet")
async def cb_open_cabinet(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    if not user:
        await call.answer("Avval ro'yxatdan o'ting!", show_alert=True)
        return
    url = _make_login_url(user[1])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖥 Kabinetni ochish", web_app=WebAppInfo(url=url))],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")],
    ])
    await call.message.edit_text("🖥 Kabinetingizga kirish uchun tugmani bosing:", reply_markup=kb)
    await call.answer()

# =========================
# OFFERS
# =========================

@dp.callback_query(F.data == "show_offers")
async def cb_show_offers(call: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id, offer_name, offer_time, price, discount FROM offers")
        offers = await cur.fetchall()

    if not offers:
        await call.answer("Hozircha tariflar mavjud emas.", show_alert=True)
        return

    text = "📦 <b>Mavjud tariflar:</b>\n\n"
    buttons = []
    for o in offers:
        o_id, o_name, o_time, price, discount = o
        final = price - discount
        text += f"🔹 <b>{o_name}</b> — {o_time} kun\n"
        if discount > 0:
            text += f"   <s>{int(price):,}</s> → <b>{int(final):,} so'm</b> (chegirma: {int(discount):,})\n\n"
        else:
            text += f"   <b>{int(final):,} so'm</b>\n\n"
        buttons.append([InlineKeyboardButton(text=f"🛒 {o_name} — {int(final):,} so'm", callback_data=f"buy_{o_id}")])

    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")])
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await call.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def cb_buy(call: CallbackQuery, state: FSMContext):
    offer_id = int(call.data.split("_")[1])
    user = await get_user(call.from_user.id)
    if not user:
        await call.answer("Avval ro'yxatdan o'ting!", show_alert=True)
        return

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT offer_name, price, discount FROM offers WHERE id=?", (offer_id,))
        offer = await cur.fetchone()

    if not offer:
        await call.answer("Tarif topilmadi.", show_alert=True)
        return

    final = offer[1] - offer[2]
    await state.update_data(offer_id=offer_id, user_id=user[0])
    await state.set_state(PaymentState.waiting_for_receipt)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_payment")]
    ])
    await call.message.edit_text(
        f"🛒 <b>{offer[0]}</b> tarifi tanlandi\n\n"
        f"💰 To'lov summasi: <b>{int(final):,} so'm</b>\n\n"
        f"💳 Karta raqami:\n<code>{CARD_NUMBER}</code>\n\n"
        f"To'lov qilib, <b>chek rasmini</b> shu yerga yuboring 👇",
        parse_mode="HTML", reply_markup=kb
    )
    await call.answer()

@dp.callback_query(F.data == "cancel_payment")
async def cb_cancel_payment(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ To'lov bekor qilindi.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="back_main")]
    ]))
    await call.answer()

@dp.message(PaymentState.waiting_for_receipt, F.photo)
async def process_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    offer_id = data.get("offer_id")
    user_id = data.get("user_id")
    photo_id = message.photo[-1].file_id

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"conf_{user_id}_{offer_id}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"rej_{user_id}"),
    ]])
    await bot.send_photo(
        chat_id=ADMIN_ID, photo=photo_id,
        caption=f"📩 Yangi to'lov cheki!\n👤 @{message.from_user.username} (tg_id: {message.from_user.id})\nUser ID: {user_id} | Offer ID: {offer_id}",
        reply_markup=kb
    )
    await state.clear()
    await message.answer("✅ Chekingiz qabul qilindi. Admin tekshirib, tasdiqlagach xabar beramiz.", reply_markup=main_menu_kb(True))

@dp.message(PaymentState.waiting_for_receipt)
async def receipt_invalid(message: Message):
    await message.answer("📸 Iltimos, to'lov chekini <b>rasm</b> ko'rinishida yuboring.", parse_mode="HTML")

@dp.callback_query(F.data.startswith("conf_") | F.data.startswith("rej_"))
async def admin_decision(call: CallbackQuery):
    parts = call.data.split("_")
    action = parts[0]
    user_id = int(parts[1])

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT tg_id, username FROM users WHERE id=?", (user_id,))
        user_info = await cur.fetchone()
        if not user_info:
            await call.answer("Foydalanuvchi topilmadi!", show_alert=True)
            return
        tg_id, username = user_info

        if action == "conf":
            offer_id = int(parts[2])
            await db.execute("INSERT INTO contracts (user_id, offer_id) VALUES (?, ?)", (user_id, offer_id))
            await db.commit()
            cur = await db.execute("SELECT offer_name, offer_time FROM offers WHERE id=?", (offer_id,))
            offer = await cur.fetchone()
            await call.message.edit_caption(caption=call.message.caption + "\n\n✅ Tasdiqlandi!")
            await bot.send_message(
                tg_id,
                f"🎉 <b>To'lovingiz tasdiqlandi!</b>\n\n"
                f"📦 <b>{offer[0]}</b> tarifi <b>{offer[1]} kun</b> muddatga faollashtirildi.\n\n"
                f"Kabinetga kirib testlarni boshlashingiz mumkin 👇",
                parse_mode="HTML", reply_markup=main_menu_kb(True)
            )
        else:
            await call.message.edit_caption(caption=call.message.caption + "\n\n❌ Rad etildi!")
            await bot.send_message(
                tg_id,
                "❌ <b>To'lovingiz rad etildi.</b>\n\nChekni to'g'ri yuborganingizga ishonch hosil qilib, qayta urinib ko'ring.",
                parse_mode="HTML", reply_markup=main_menu_kb(True)
            )
    await call.answer()

# =========================
# MY CONTRACTS
# =========================

@dp.callback_query(F.data == "my_contracts")
async def cb_my_contracts(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    if not user:
        await call.answer("Avval ro'yxatdan o'ting!", show_alert=True)
        return

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT o.offer_name, o.offer_time, c.contract_date
            FROM contracts c
            JOIN offers o ON c.offer_id = o.id
            WHERE c.user_id = ?
            ORDER BY c.contract_date DESC
        """, (user[0],))
        contracts = await cur.fetchall()

    if not contracts:
        await call.message.edit_text(
            "📁 <b>Xaridlarim</b>\n\nSizda hali xaridlar yo'q.\nTariflarni ko'rish uchun quyidagi tugmani bosing:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📦 Tariflar", callback_data="show_offers")],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")],
            ])
        )
        await call.answer()
        return

    now = datetime.now()
    text = "📁 <b>Sizning xaridlaringiz:</b>\n\n"
    for o_name, o_time, c_date_str in contracts:
        try:
            c_date = datetime.strptime(c_date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            c_date = datetime.fromisoformat(c_date_str)
        expires_at = c_date + timedelta(days=o_time)
        remaining = (expires_at - now).days

        if now < expires_at:
            status = f"🟢 Faol ({remaining} kun qoldi)"
        else:
            status = "🔴 Tugagan"

        text += (
            f"📦 <b>{o_name}</b>\n"
            f"   📅 Boshlanish: {c_date.strftime('%d.%m.%Y')}\n"
            f"   ⏳ Tugash: {expires_at.strftime('%d.%m.%Y')}\n"
            f"   {status}\n\n"
        )

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")]
    ]))
    await call.answer()

# =========================
# STATS
# =========================

@dp.callback_query(F.data == "my_stats")
async def cb_my_stats(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    if not user:
        await call.answer("Avval ro'yxatdan o'ting!", show_alert=True)
        return

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            SELECT COUNT(*), AVG(percentage), MAX(percentage), MIN(percentage),
                   SUM(correct_answers), SUM(wrong_answers)
            FROM attempts WHERE user_id=?
        """, (user[0],))
        row = await cur.fetchone()

        cur2 = await db.execute("""
            SELECT t.name, a.percentage, a.correct_answers, a.wrong_answers, a.created_at
            FROM attempts a JOIN tests t ON a.test_id = t.id
            WHERE a.user_id=?
            ORDER BY a.created_at DESC LIMIT 5
        """, (user[0],))
        last5 = await cur2.fetchall()

    total, avg_p, max_p, min_p, total_correct, total_wrong = row
    if not total:
        await call.message.edit_text(
            "📊 <b>Statistika</b>\n\nSiz hali birorta test topshirmadingiz.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")]
            ])
        )
        await call.answer()
        return

    ic3_pass = "✅" if (avg_p or 0) >= 70 else "❌"
    text = (
        f"📊 <b>Sizning statistikangiz</b>\n\n"
        f"🔢 Jami urinishlar: <b>{total}</b>\n"
        f"📈 O'rtacha ball: <b>{avg_p:.1f}%</b> {ic3_pass}\n"
        f"🏆 Eng yuqori: <b>{max_p:.1f}%</b>\n"
        f"📉 Eng past: <b>{min_p:.1f}%</b>\n"
        f"✅ Jami to'g'ri: <b>{total_correct or 0}</b>\n"
        f"❌ Jami noto'g'ri: <b>{total_wrong or 0}</b>\n\n"
        f"<i>IC3 GS6 o'tish bali: 70%</i>\n\n"
        f"📋 <b>So'nggi 5 ta urinish:</b>\n"
    )
    for t_name, pct, correct, wrong, created in last5:
        icon = "✅" if pct >= 70 else "❌"
        text += f"{icon} {t_name}: <b>{pct:.1f}%</b> ({correct}✓ {wrong}✗)\n"

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")]
    ]))
    await call.answer()

# =========================
# HELP
# =========================

@dp.callback_query(F.data == "help")
async def cb_help(call: CallbackQuery):
    text = (
        "❓ <b>Yordam</b>\n\n"
        "🎓 <b>IC3 GS6 Test Platformasi</b>\n\n"
        "<b>Qanday ishlaydi?</b>\n"
        "1️⃣ Ro'yxatdan o'ting\n"
        "2️⃣ Tarif xarid qiling\n"
        "3️⃣ Kabinetga kiring va testlarni boshlang\n"
        "4️⃣ Natijalaringizni kuzating\n\n"
        "<b>IC3 GS6 haqida:</b>\n"
        "• O'tish bali: <b>70%</b>\n"
        "• 3 ta modul: Computing Fundamentals, Key Applications, Living Online\n\n"
        "<b>Buyruqlar:</b>\n"
        "/start — Bosh menyu\n\n"
        "📞 Muammo bo'lsa admin bilan bog'laning."
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")]
    ]))
    await call.answer()

# =========================
# BACK TO MAIN
# =========================

@dp.callback_query(F.data == "back_main")
async def cb_back_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await get_user(call.from_user.id)
    name = call.from_user.first_name or "Foydalanuvchi"
    if user:
        text = f"👋 <b>{name}</b>, bosh menyu:"
    else:
        text = f"👋 <b>{name}</b>, platformaga xush kelibsiz! Ro'yxatdan o'ting:"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_kb(bool(user)))
    await call.answer()

# =========================
# MAIN
# =========================

async def main():
    print("Bot ishga tushdi ✅")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
