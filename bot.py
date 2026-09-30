import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Singapore"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "-1001623940278"))
ADMIN_IDS = {
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}
WELCOME_MESSAGE = os.getenv(
    "WELCOME_MESSAGE",
    "👋 Welcome to AskCouple, {name}!\n\nFollow the group for upcoming LIVE sessions, brand collaborations, products and special announcements."
)

def is_admin(user_id: int) -> bool:
    return not ADMIN_IDS or user_id in ADMIN_IDS

async def require_admin(update: Update) -> bool:
    user = update.effective_user
    if not user or not is_admin(user.id):
        if update.effective_message:
            await update.effective_message.reply_text("This command is for AskCouple admins.")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 AskCouple Assistant is online.\n\n"
        "Use /help to see the available commands."
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ASKCOUPLE BOT\n\n"
        "/live <time> | <brand> | <message>\n"
        "Create a LIVE announcement for approval.\n\n"
        "/schedule YYYY-MM-DD HH:MM | <brand> | <message>\n"
        "Schedule an approved-style announcement.\n\n"
        "/announce <message>\n"
        "Post a normal announcement.\n\n"
        "/id\n"
        "Show your Telegram user ID and this chat ID.\n\n"
        "/rules\n"
        "Show group rules.\n\n"
        "Tip: Attach a real product photo and put /live ... in the photo caption."
    )

async def ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Your user ID: {update.effective_user.id}\n"
        f"Chat ID: {update.effective_chat.id}"
    )

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 AskCouple Group Rules\n\n"
        "• Be respectful.\n"
        "• No spam or repeated promotions.\n"
        "• No suspicious links.\n"
        "• Keep discussions relevant.\n"
        "• Admin decisions apply to group moderation."
    )

def build_live_text(time_text: str, brand: str, message: str) -> str:
    return (
        "🔴 <b>ASKCOUPLE LIVE</b>\n\n"
        f"✨ <b>{brand}</b>\n"
        f"⏰ <b>LIVE: {time_text}</b>\n\n"
        f"{message}\n\n"
        "📲 Join us LIVE at AskCouple!\n"
        "#AskCouple #AskCoupleLive"
    )

async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    raw = " ".join(context.args)
    parts = [p.strip() for p in raw.split("|", 2)]
    if len(parts) != 3:
        await update.message.reply_text(
            "Format:\n/live 8:40 AM | Kinohimitsu | Join us for today's special LIVE!"
        )
        return

    time_text, brand, message = parts
    text = build_live_text(time_text, brand, message)
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve & Post", callback_data="post_live"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_live"),
        ]
    ])

    context.user_data["pending_live"] = {
        "text": text,
        "photo_file_id": (
            update.message.photo[-1].file_id if update.message.photo else None
        ),
    }
    await update.message.reply_text(
        "PREVIEW — approve before posting:\n\n" + text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )

async def photo_caption_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.caption or ""
    if caption.startswith("/live"):
        fake_args = caption[len("/live"):].strip().split()
        context.args = fake_args
        await live(update, context)

async def approval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.answer("Admins only.", show_alert=True)
        return

    if query.data == "cancel_live":
        context.user_data.pop("pending_live", None)
        await query.edit_message_text("❌ LIVE announcement cancelled.")
        return

    pending = context.user_data.get("pending_live")
    if not pending:
        await query.edit_message_text("This preview has expired. Create it again with /live.")
        return

    chat_id = TARGET_CHAT_ID
    if pending["photo_file_id"]:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=pending["photo_file_id"],
            caption=pending["text"],
            parse_mode=ParseMode.HTML,
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=pending["text"],
            parse_mode=ParseMode.HTML,
        )
    context.user_data.pop("pending_live", None)
    await query.edit_message_text("✅ Posted to AskCouple.")

async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("Format: /announce Your announcement here")
        return
    await context.bot.send_message(update.effective_chat.id, f"📣 <b>ASKCOUPLE</b>\n\n{text}", parse_mode=ParseMode.HTML)

async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    raw = " ".join(context.args)
    parts = [p.strip() for p in raw.split("|", 2)]
    if len(parts) != 3:
        await update.message.reply_text(
            "Format:\n/schedule 2026-10-01 08:00 | Brand Name | LIVE today at 8:40 AM!"
        )
        return

    when_text, brand, message = parts
    try:
        when = datetime.strptime(when_text, "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
    except ValueError:
        await update.message.reply_text("Use date/time format: YYYY-MM-DD HH:MM")
        return

    if when <= datetime.now(TZ):
        await update.message.reply_text("Please choose a future date/time.")
        return

    job_name = f"askcouple_{update.effective_chat.id}_{int(when.timestamp())}"
    context.job_queue.run_once(
        scheduled_post,
        when=when,
        data={
            "chat_id": update.effective_chat.id,
            "brand": brand,
            "message": message,
        },
        name=job_name,
    )
    await update.message.reply_text(
        f"✅ Scheduled for {when.strftime('%d %b %Y, %I:%M %p')} Singapore time."
    )

async def scheduled_post(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    text = (
        "📣 <b>ASKCOUPLE UPDATE</b>\n\n"
        f"✨ <b>{data['brand']}</b>\n\n"
        f"{data['message']}\n\n"
        "#AskCouple #AskCoupleLive"
    )
    await context.bot.send_message(data["chat_id"], text, parse_mode=ParseMode.HTML)

async def welcome_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        name = member.first_name or "there"
        await update.message.reply_text(WELCOME_MESSAGE.format(name=name))

async def anti_spam_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if is_admin(update.effective_user.id):
        return
    text = update.message.text.lower()
    suspicious = ("t.me/", "telegram.me/", "bit.ly/", "tinyurl.com/")
    if any(x in text for x in suspicious):
        try:
            await update.message.delete()
            await context.bot.send_message(
                update.effective_chat.id,
                f"⚠️ {update.effective_user.first_name}, promotional/suspicious links are not allowed."
            )
        except Exception:
            logger.exception("Could not delete message. Check bot admin permissions.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("id", ids))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("live", live))
    app.add_handler(CommandHandler("announce", announce))
    app.add_handler(CommandHandler("schedule", schedule))
    app.add_handler(CallbackQueryHandler(approval_callback, pattern="^(post_live|cancel_live)$"))
    app.add_handler(MessageHandler(filters.PHOTO & filters.CaptionRegex(r"^/live"), photo_caption_router))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_members))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anti_spam_links))

    logger.info("AskCouple bot starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
