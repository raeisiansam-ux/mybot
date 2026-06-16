import logging
import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BOT_TOKEN = "8583044644:AAHMJIZY7wWfDUlRw6jNPB78oCcs3kK3V5w"
ADMIN_ID = 5989298023
CHANNEL_URL = "https://t.me/tunnelyconfig"
CARD_NUMBER = "5022291506942869"
CARD_OWNER = "رضایی"
DB_FILE = "database.json"

# ─── PLANS ────────────────────────────────────────────────────────────────────
PLANS = {
    "10gb": {"name": "10 گیگ مولتی لوکیشن ⭐", "gb": 10, "price": 200000},
    "30gb": {"name": "30 گیگ مولتی لوکیشن ⭐", "gb": 30, "price": 450000},
    "50gb": {"name": "50 گیگ مولتی لوکیشن ⭐", "gb": 50, "price": 600000},
}

# ─── STATES ───────────────────────────────────────────────────────────────────
(
    AWAITING_CHARGE_AMOUNT,
    AWAITING_RECEIPT,
    AWAITING_CONFIG_FOR_USER,
) = range(3)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── DATABASE ─────────────────────────────────────────────────────────────────
def load_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def get_user(user_id):
    db = load_db()
    uid = str(user_id)
    if uid not in db["users"]:
        db["users"][uid] = {"balance": 0, "transactions": [], "configs": []}
        save_db(db)
    return db["users"][uid]

def save_user(user_id, data):
    db = load_db()
    db["users"][str(user_id)] = data
    save_db(db)

def add_transaction(user_id, label, amount):
    user = get_user(user_id)
    user["transactions"].insert(0, {
        "label": label,
        "amount": amount,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    user["transactions"] = user["transactions"][:20]  # keep last 20
    save_user(user_id, user)

# ─── KEYBOARDS ────────────────────────────────────────────────────────────────
def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🛒 خرید کانفیگ"), KeyboardButton("👛 کیف پول")],
        [KeyboardButton("📱 کانفیگ های من"), KeyboardButton("📢 کانال اصلی")],
    ], resize_keyboard=True)

# ─── /start ───────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id)  # init user
    await update.message.reply_text(
        f"سلام {user.first_name} عزیز! 👋\n\nبه ربات فروش VPN خوش اومدی 🌐\nیه گزینه رو انتخاب کن:",
        reply_markup=main_keyboard()
    )

# ─── WALLET ───────────────────────────────────────────────────────────────────
async def show_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    balance = user["balance"]
    txs = user["transactions"]

    tx_text = ""
    if txs:
        for tx in txs[:10]:
            sign = "🟢 +" if tx["amount"] > 0 else "🔴 -"
            tx_text += f"{sign}{abs(tx['amount']):,} — {tx['label']} ({tx['date']})\n"
    else:
        tx_text = "هنوز تراکنشی نداری.\n"

    text = (
        "👛 *کیف پول*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 موجودی: *{balance:,} تومان*\n\n"
        "📜 *آخرین تراکنش‌ها:*\n"
        f"{tx_text}"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ شارژ کیف پول", callback_data="charge_wallet")]
    ])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

# ─── CHANNEL ──────────────────────────────────────────────────────────────────
async def show_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 ورود به کانال اصلی", url=CHANNEL_URL)]
    ])
    await update.message.reply_text("برای ورود به کانال اصلی دکمه زیر را بزنید:", reply_markup=kb)

# ─── MY CONFIGS ───────────────────────────────────────────────────────────────
async def show_my_configs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    configs = user.get("configs", [])

    if not configs:
        await update.message.reply_text("📱 *کانفیگ‌های شما*\n\nهنوز کانفیگی نداری.\nبرای خرید از منو اصلی اقدام کن.", parse_mode="Markdown")
        return

    text = f"📱 *کانفیگ‌های شما*\n\nتعداد کل: *{len(configs)} کانفیگ*\n\nلیست کانفیگ‌ها در پیام‌های زیر ارسال می‌شود:\n"
    await update.message.reply_text(text, parse_mode="Markdown")
    for i, cfg in enumerate(configs, 1):
        await update.message.reply_text(
            f"*کانفیگ {i}*\n🔑 {cfg['label']}\n\n`{cfg['config']}`",
            parse_mode="Markdown"
        )

# ─── BUY CONFIG ───────────────────────────────────────────────────────────────
async def show_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ {p['name']} — {p['price']:,} تومان", callback_data=f"plan_{k}")]
        for k, p in PLANS.items()
    ])
    await update.message.reply_text(
        "🛒 *پلن‌های کتگوری «سرور حجمی» 🔋*\n\nپلن مورد نظر را انتخاب کنید:",
        parse_mode="Markdown",
        reply_markup=kb
    )

async def plan_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_key = query.data.replace("plan_", "")
    plan = PLANS[plan_key]
    context.user_data["selected_plan"] = plan_key
    context.user_data["quantity"] = 1

    await show_plan_quantity(query, context, plan, 1)

async def show_plan_quantity(query, context, plan, qty):
    plan_key = context.user_data["selected_plan"]
    total = plan["price"] * qty
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➖", callback_data="qty_minus"),
            InlineKeyboardButton(str(qty), callback_data="qty_show"),
            InlineKeyboardButton("➕", callback_data="qty_plus"),
        ],
        [InlineKeyboardButton("✅ تایید و ادامه", callback_data="confirm_plan")],
        [InlineKeyboardButton("❌ انصراف", callback_data="cancel")],
    ])
    text = (
        f"📦 *پلن: {plan['name']}*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💲 قیمت واحد: {plan['price']:,} تومان\n"
        f"🔢 تعداد: {qty}\n"
        f"💰 مجموع: {total:,} تومان\n\n"
        "تعداد را انتخاب کنید:"
    )
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)

async def qty_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    qty = context.user_data.get("quantity", 1)
    if action == "qty_plus":
        qty = min(qty + 1, 6)
    elif action == "qty_minus":
        qty = max(qty - 1, 1)
    context.user_data["quantity"] = qty
    plan = PLANS[context.user_data["selected_plan"]]
    await show_plan_quantity(query, context, plan, qty)

async def confirm_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    plan_key = context.user_data["selected_plan"]
    qty = context.user_data.get("quantity", 1)
    plan = PLANS[plan_key]
    total = plan["price"] * qty
    user = get_user(user_id)
    balance = user["balance"]

    text = (
        "🛒 *تأیید خرید*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 پلن: {plan['name']}\n"
        f"🔢 تعداد: {qty}\n"
        f"💲 قیمت واحد: {plan['price']:,} تومان\n"
        f"💰 مجموع: {total:,} تومان\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👛 موجودی شما: {balance:,} تومان\n"
    )

    if balance >= total:
        text += "\n✅ موجودی کافی دارید. آیا تأیید می‌کنید؟"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ خرید با کیف پول", callback_data="buy_with_wallet")],
            [InlineKeyboardButton("❌ انصراف", callback_data="cancel")],
        ])
    else:
        text += "\n⚠️ موجودی کافی نیست! ابتدا کیف پول را شارژ کنید."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ شارژ کیف پول", callback_data="charge_wallet")],
            [InlineKeyboardButton("❌ انصراف", callback_data="cancel")],
        ])

    context.user_data["total"] = total
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)

async def buy_with_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    plan_key = context.user_data["selected_plan"]
    qty = context.user_data.get("quantity", 1)
    plan = PLANS[plan_key]
    total = context.user_data["total"]

    user = get_user(user_id)
    user["balance"] -= total
    save_user(user_id, user)
    add_transaction(user_id, f"خرید {plan['name']} x{qty}", -total)

    await query.edit_message_text(
        f"✅ *خرید موفق!*\n\nپلن *{plan['name']}* x{qty} خریداری شد.\nکانفیگ شما به زودی توسط ادمین ارسال می‌شود.",
        parse_mode="Markdown"
    )

    # Notify admin
    await context.bot.send_message(
        ADMIN_ID,
        f"🛒 *خرید جدید!*\n\n"
        f"👤 کاربر: {query.from_user.full_name} (ID: `{user_id}`)\n"
        f"📦 پلن: {plan['name']} x{qty}\n"
        f"💰 مبلغ: {total:,} تومان\n\n"
        f"برای ارسال کانفیگ: /sendconfig {user_id}",
        parse_mode="Markdown"
    )

# ─── CHARGE WALLET ────────────────────────────────────────────────────────────
async def charge_wallet_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💰 *مبلغ شارژ را وارد کنید (تومان):*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📝 مبلغ مورد نظر را به تومان وارد کنید 👇 کارت به کارت",
        parse_mode="Markdown"
    )
    return AWAITING_CHARGE_AMOUNT

async def charge_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace(",", "").strip()
    if not text.isdigit():
        await update.message.reply_text("❌ لطفاً یک عدد صحیح وارد کنید.")
        return AWAITING_CHARGE_AMOUNT

    amount = int(text)
    if amount < 10000:
        await update.message.reply_text("❌ حداقل مبلغ شارژ ۱۰,۰۰۰ تومان است.")
        return AWAITING_CHARGE_AMOUNT

    context.user_data["charge_amount"] = amount

    await update.message.reply_text(
        f"💳 *پرداخت کارت به کارت*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 مبلغ: *{amount:,} تومان*\n\n"
        f"💳 شماره کارت:\n`{CARD_NUMBER}`\n"
        f"👤 صاحب حساب: *{CARD_OWNER}*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📎 پس از واریز، تصویر یا متن رسید را ارسال کنید:",
        parse_mode="Markdown"
    )
    return AWAITING_RECEIPT

async def receipt_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amount = context.user_data.get("charge_amount", 0)

    await update.message.reply_text(
        "✅ رسید شما دریافت شد.\nادمین به زودی پرداخت را تأیید می‌کند."
    )

    # Forward receipt to admin
    caption = (
        f"💳 *درخواست شارژ کیف پول*\n\n"
        f"👤 کاربر: {user.full_name} (ID: `{user.id}`)\n"
        f"💰 مبلغ: {amount:,} تومان\n\n"
        f"برای تأیید:\n/approve {user.id} {amount}\n\n"
        f"برای رد:\n/reject {user.id}"
    )

    if update.message.photo:
        await context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id, caption=caption, parse_mode="Markdown")
    else:
        await context.bot.send_message(ADMIN_ID, caption + f"\n\n📝 متن رسید: {update.message.text}", parse_mode="Markdown")

    return ConversationHandler.END

# ─── ADMIN COMMANDS ───────────────────────────────────────────────────────────
async def approve_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("استفاده: /approve USER_ID AMOUNT")
        return
    uid, amount = int(args[0]), int(args[1])
    user = get_user(uid)
    user["balance"] += amount
    save_user(uid, user)
    add_transaction(uid, "شارژ کیف پول (کارت به کارت)", amount)
    await update.message.reply_text(f"✅ {amount:,} تومان به کاربر {uid} اضافه شد.")
    await context.bot.send_message(uid, f"✅ کیف پول شما با موفقیت *{amount:,} تومان* شارژ شد!", parse_mode="Markdown")

async def reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if not args:
        await update.message.reply_text("استفاده: /reject USER_ID")
        return
    uid = int(args[0])
    await update.message.reply_text(f"❌ پرداخت کاربر {uid} رد شد.")
    await context.bot.send_message(uid, "❌ متأسفانه پرداخت شما تأیید نشد. برای پشتیبانی با ادمین در تماس باشید.")

async def send_config_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if not args:
        await update.message.reply_text("استفاده: /sendconfig USER_ID\nسپس کانفیگ را در پیام بعدی ارسال کن.")
        return
    context.user_data["config_target"] = int(args[0])
    await update.message.reply_text(f"✅ آماده‌ام. کانفیگ را برای کاربر {args[0]} ارسال کن:")
    return AWAITING_CONFIG_FOR_USER

async def receive_config_for_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    target_uid = context.user_data.get("config_target")
    config_text = update.message.text

    user = get_user(target_uid)
    user["configs"].append({
        "label": f"کانفیگ {len(user['configs']) + 1}",
        "config": config_text,
        "date": datetime.now().strftime("%Y-%m-%d")
    })
    save_user(target_uid, user)

    await context.bot.send_message(
        target_uid,
        f"📦 *کانفیگ شما آماده شد!*\n\n🔑 `{config_text}`\n\nبرای مشاهده همه کانفیگ‌ها: کانفیگ های من",
        parse_mode="Markdown"
    )
    await update.message.reply_text(f"✅ کانفیگ برای کاربر {target_uid} ارسال شد.")
    return ConversationHandler.END

# ─── CANCEL ───────────────────────────────────────────────────────────────────
async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ لغو شد.")
    return ConversationHandler.END

async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ لغو شد.", reply_markup=main_keyboard())
    return ConversationHandler.END

# ─── TEXT ROUTER ──────────────────────────────────────────────────────────────
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🛒 خرید کانفیگ":
        await show_buy(update, context)
    elif text == "👛 کیف پول":
        await show_wallet(update, context)
    elif text == "📱 کانفیگ های من":
        await show_my_configs(update, context)
    elif text == "📢 کانال اصلی":
        await show_channel(update, context)

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Charge wallet conversation
    charge_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(charge_wallet_start, pattern="^charge_wallet$")],
        states={
            AWAITING_CHARGE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, charge_amount_received)],
            AWAITING_RECEIPT: [MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, receipt_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)],
    )

    # Admin send config conversation
    config_conv = ConversationHandler(
        entry_points=[CommandHandler("sendconfig", send_config_cmd)],
        states={
            AWAITING_CONFIG_FOR_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_config_for_user)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", approve_payment))
    app.add_handler(CommandHandler("reject", reject_payment))
    app.add_handler(charge_conv)
    app.add_handler(config_conv)
    app.add_handler(CallbackQueryHandler(plan_selected, pattern="^plan_"))
    app.add_handler(CallbackQueryHandler(qty_change, pattern="^qty_"))
    app.add_handler(CallbackQueryHandler(confirm_plan, pattern="^confirm_plan$"))
    app.add_handler(CallbackQueryHandler(buy_with_wallet, pattern="^buy_with_wallet$"))
    app.add_handler(CallbackQueryHandler(cancel_action, pattern="^cancel$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
