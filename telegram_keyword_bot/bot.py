import os
import logging
from dotenv import load_dotenv
load_dotenv()
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler,
    ContextTypes, filters
)
from database import db

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

# ─── Conversation States ───────────────────────────────────────────────────────
WAIT_KEYWORD, WAIT_IMAGE, WAIT_CAPTION, WAIT_BTN_TEXT, WAIT_BTN_URL = range(5)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ══════════════════════════════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_admin(user.id):
        msg = (
            "👋 <b>Admin Panel</b>\n\n"
            "🎬 <b>Movie Filter Bot</b>\n\n"
            "<b>Commands:</b>\n"
            "➕ /addmovie — New movie keyword add කරන්න\n"
            "📋 /listmovies — සියලු movies බලන්න\n"
            "🗑 /deletemovie — Movie delete කරන්න\n"
        )
    else:
        msg = (
            "👋 <b>Movie Filter Bot</b>\n\n"
            "Group එකේ movie name type කරන්න.\n"
            "Bot reply දෙනවා! 🎬"
        )
    await update.message.reply_text(msg, parse_mode="HTML")


# ══════════════════════════════════════════════════════════════════════════════
#  /addmovie  —  Multi-step ConversationHandler
# ══════════════════════════════════════════════════════════════════════════════

async def addmovie_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin විතරයි movie add කරන්න පුළුවන්.")
        return ConversationHandler.END

    context.user_data.clear()
    await update.message.reply_text(
        "🎬 <b>Step 1/4</b>\n\n"
        "Movie keyword type කරන්න:\n"
        "<i>(Example: daredevil born again)</i>\n\n"
        "Cancel කරන්න: /cancel",
        parse_mode="HTML"
    )
    return WAIT_KEYWORD


async def received_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = update.message.text.strip().lower()
    context.user_data["keyword"] = keyword
    await update.message.reply_text(
        f"✅ Keyword: <code>{keyword}</code>\n\n"
        "🖼 <b>Step 2/4</b>\n\n"
        "Movie poster/image send කරන්න:\n"
        "<i>(Image upload කරන්න)</i>",
        parse_mode="HTML"
    )
    return WAIT_IMAGE


async def received_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Image එකක් send කරන්න. (Photo upload කරන්න)")
        return WAIT_IMAGE

    photo = update.message.photo[-1]
    context.user_data["photo_file_id"] = photo.file_id

    await update.message.reply_text(
        "✅ Image received!\n\n"
        "📝 <b>Step 3/4</b>\n\n"
        "Movie caption/description type කරන්න:\n"
        "<i>HTML tags use කරන්න පුළුවන්: &lt;b&gt;bold&lt;/b&gt;, &lt;i&gt;italic&lt;/i&gt;</i>\n\n"
        "Example:\n"
        "<code>🎬 Daredevil: Born Again (2025)\n\n"
        "📌 Genre: Action, Crime\n"
        "⭐ Rating: 8.2/10\n"
        "🌐 Language: English</code>",
        parse_mode="HTML"
    )
    return WAIT_CAPTION


async def received_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["caption"] = update.message.text

    await update.message.reply_text(
        "✅ Caption saved!\n\n"
        "🔘 <b>Step 4/4</b>\n\n"
        "Download button text type කරන්න:\n"
        "<i>(Example: <code>⬇️ Download</code> or <code>📥 Download HD</code>)</i>",
        parse_mode="HTML"
    )
    return WAIT_BTN_TEXT


async def received_btn_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["btn_text"] = update.message.text.strip()

    await update.message.reply_text(
        f"✅ Button text: <code>{context.user_data['btn_text']}</code>\n\n"
        "🔗 Download link (URL) type කරන්න:\n"
        "<i>(Example: https://t.me/yourchannel/123)</i>",
        parse_mode="HTML"
    )
    return WAIT_BTN_URL


async def received_btn_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not url.startswith("http"):
        await update.message.reply_text("❌ Valid URL එකක් දෙන්න. (https:// ලින් start කරන්න)")
        return WAIT_BTN_URL

    keyword       = context.user_data["keyword"]
    photo_file_id = context.user_data["photo_file_id"]
    caption       = context.user_data["caption"]
    btn_text      = context.user_data["btn_text"]

    await db.upsert_movie(keyword, photo_file_id, caption, btn_text, url)

    keyboard = [[InlineKeyboardButton(btn_text, url=url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("✅ <b>Movie saved! Preview:</b>", parse_mode="HTML")
    await update.message.reply_photo(
        photo=photo_file_id,
        caption=caption,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  /listmovies
# ══════════════════════════════════════════════════════════════════════════════

async def list_movies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin විතරයි list බලන්න පුළුවන්.")
        return

    movies = await db.get_all_movies()
    if not movies:
        await update.message.reply_text("📭 Movies නෑ. /addmovie use කරලා add කරන්න.")
        return

    msg = "📋 <b>Saved Movies:</b>\n\n"
    for i, m in enumerate(movies, 1):
        msg += f"{i}. 🎬 <code>{m['keyword']}</code>\n"

    msg += "\n<i>Delete කරන්න: /deletemovie &lt;keyword&gt;</i>"
    await update.message.reply_text(msg, parse_mode="HTML")


# ══════════════════════════════════════════════════════════════════════════════
#  /deletemovie
# ══════════════════════════════════════════════════════════════════════════════

async def delete_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin විතරයි delete කරන්න පුළුවන්.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /deletemovie <keyword>\nExample: /deletemovie daredevil born again")
        return

    keyword = " ".join(context.args).strip().lower()
    deleted = await db.delete_movie(keyword)

    if deleted:
        await update.message.reply_text(f"✅ <code>{keyword}</code> deleted!", parse_mode="HTML")
    else:
        await update.message.reply_text(f"❌ <code>{keyword}</code> හොයාගන්න බැරි වුනා.", parse_mode="HTML")


# ══════════════════════════════════════════════════════════════════════════════
#  Group message handler — keyword detection
# ══════════════════════════════════════════════════════════════════════════════

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    text = message.text.strip().lower()

    movie = await db.find_movie(text)
    if not movie:
        movie = await db.find_movie_partial(text)

    if movie:
        keyboard = [[InlineKeyboardButton(movie["btn_text"], url=movie["btn_url"])]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await message.reply_photo(
            photo=movie["photo_file_id"],
            caption=movie["caption"],
            reply_markup=reply_markup,
            parse_mode="HTML"
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════════════

async def post_init(application: Application):
    await db.connect()
    logger.info("MongoDB connected ✅")


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable not set!")

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    add_conv = ConversationHandler(
        entry_points=[CommandHandler("addmovie", addmovie_start)],
        states={
            WAIT_KEYWORD:  [MessageHandler(filters.TEXT & ~filters.COMMAND, received_keyword)],
            WAIT_IMAGE:    [MessageHandler(filters.PHOTO, received_image),
                            MessageHandler(filters.TEXT & ~filters.COMMAND, received_image)],
            WAIT_CAPTION:  [MessageHandler(filters.TEXT & ~filters.COMMAND, received_caption)],
            WAIT_BTN_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_btn_text)],
            WAIT_BTN_URL:  [MessageHandler(filters.TEXT & ~filters.COMMAND, received_btn_url)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(add_conv)
    app.add_handler(CommandHandler("listmovies", list_movies))
    app.add_handler(CommandHandler("deletemovie", delete_movie))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Movie Filter Bot starting... 🚀")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
