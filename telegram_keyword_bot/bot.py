import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from database import db

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ─── Admin Commands ────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 සලාමුන් !\n\n"
        "මම keyword bot එකක්. Group එකේ keyword type කරන්න, reply දෙන්නම්.\n\n"
        "Admin commands:\n"
        "/addkeyword <keyword> | <reply> - Keyword add කරන්න\n"
        "/listkeywords - සියලු keywords බලන්න\n"
        "/deletekeyword <keyword> - Keyword delete කරන්න"
    )


async def add_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a keyword: /addkeyword keyword | reply text"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin විතරයි keyword add කරන්න පුළුවන්.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /addkeyword <keyword> | <reply>\n"
            "Example: /addkeyword daredevil born again | Daredevil: Born Again (2025-)"
        )
        return

    text = " ".join(context.args)
    if "|" not in text:
        await update.message.reply_text("❌ '|' separator use කරන්න keyword සහ reply වෙන් කරන්න.")
        return

    keyword, reply = text.split("|", 1)
    keyword = keyword.strip().lower()
    reply = reply.strip()

    if not keyword or not reply:
        await update.message.reply_text("❌ Keyword සහ reply දෙකම ඕනෑ.")
        return

    await db.upsert_keyword(keyword, reply)
    await update.message.reply_text(f"✅ Keyword saved!\n\n🔑 Keyword: `{keyword}`\n💬 Reply: {reply}", parse_mode="Markdown")


async def list_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all keywords"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin විතරයි keywords බලන්න පුළුවන්.")
        return

    keywords = await db.get_all_keywords()
    if not keywords:
        await update.message.reply_text("📭 Keywords නෑ. /addkeyword use කරලා add කරන්න.")
        return

    msg = "📋 *Saved Keywords:*\n\n"
    for kw in keywords:
        msg += f"🔑 `{kw['keyword']}` → {kw['reply'][:50]}{'...' if len(kw['reply']) > 50 else ''}\n"

    await update.message.reply_text(msg, parse_mode="Markdown")


async def delete_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a keyword: /deletekeyword keyword"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin විතරයි keyword delete කරන්න පුළුවන්.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /deletekeyword <keyword>")
        return

    keyword = " ".join(context.args).strip().lower()
    deleted = await db.delete_keyword(keyword)

    if deleted:
        await update.message.reply_text(f"✅ `{keyword}` deleted!", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ `{keyword}` keyword හොයාගන්න බැරි වුනා.", parse_mode="Markdown")


# ─── Message Handler ────────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if message matches any keyword and reply"""
    message = update.message
    if not message or not message.text:
        return

    text = message.text.strip().lower()
    user_name = message.from_user.first_name or "User"

    # Check exact match first, then partial match
    keyword_data = await db.find_keyword(text)
    if not keyword_data:
        # Try partial match
        keyword_data = await db.find_keyword_partial(text)

    if keyword_data:
        reply_text = keyword_data["reply"]
        buttons = keyword_data.get("buttons", [])

        keyboard = []
        for btn in buttons:
            keyboard.append([InlineKeyboardButton(btn["text"], callback_data=btn.get("data", btn["text"]))])

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        # Format reply with user's name
        formatted_reply = reply_text.replace("{name}", user_name).replace("{keyword}", text)

        await message.reply_text(
            formatted_reply,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses"""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(f"ඔබ '{query.data}' click කළා.")


# ─── Main ───────────────────────────────────────────────────────────────────────

async def post_init(application: Application):
    await db.connect()
    logger.info("MongoDB connected ✅")


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable not set!")

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addkeyword", add_keyword))
    app.add_handler(CommandHandler("listkeywords", list_keywords))
    app.add_handler(CommandHandler("deletekeyword", delete_keyword))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot starting... 🚀")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
