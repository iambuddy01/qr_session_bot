import asyncio
import logging
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import API_ID, API_HASH, BOT_TOKEN
from qr_generator import generate_pyrogram_session


# -------------------------------------------------
# Logging Setup (Beautiful VPS / Heroku Logs)
# -------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def startup_banner():
    banner = f"""
╔══════════════════════════════════════════════════╗
║                                                  ║
║        🚀 QR SESSION GENERATOR BOT              ║
║                                                  ║
╠══════════════════════════════════════════════════╣
║  ✅ Status      : ONLINE                        ║
║  🤖 Framework   : Pyrogram v2                   ║
║  🔐 Mode        : QR Login (User Session)       ║
║  🕒 Started At  : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC   ║
║                                                  ║
╚══════════════════════════════════════════════════╝
"""
    logger.info(banner)


# -------------------------------------------------
# Bot Initialization
# -------------------------------------------------

bot = Client(
    "qr_session_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Temporary store for 2FA sessions
pending_password = {}


# -------------------------------------------------
# Start Command
# -------------------------------------------------

@bot.on_message(filters.command("start"))
async def start_handler(client, message):
    text = (
        "🚀 **Welcome to QR Session Generator**\n\n"
        "Generate your Telegram **Pyrogram String Session** "
        "instantly using secure QR login.\n\n"
        "✨ No phone number typing\n"
        "✨ No OTP entering\n"
        "✨ Secure & fast login\n\n"
        "Click the button below to begin."
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⚡ Generate Pyrogram Session", callback_data="gen_pyro")]
        ]
    )

    await message.reply_text(text, reply_markup=keyboard)


# -------------------------------------------------
# QR Generate Callback
# -------------------------------------------------

@bot.on_callback_query(filters.regex("gen_pyro"))
async def generate_callback(client, callback_query):
    user_id = callback_query.from_user.id

    await callback_query.message.edit_text(
        "⏳ **Generating QR Code...**\n\nPlease wait..."
    )

    result = await generate_pyrogram_session(bot, user_id)

    # If 2FA required
    if isinstance(result, tuple) and result[0] == "PASSWORD_REQUIRED":
        pending_password[user_id] = result[1]
        await bot.send_message(
            user_id,
            "🔐 **Two-Step Verification Enabled**\n\n"
            "Please send your Telegram account password."
        )
        return

    # Success
    if isinstance(result, tuple) and result[0] == "SUCCESS":
        me = result[1]

        await bot.send_message(
            user_id,
            f"🎉 **Login Successful!**\n\n"
            f"👤 Name: {me.first_name}\n"
            f"🆔 ID: `{me.id}`\n\n"
            "✅ Your session has been securely saved in your **Saved Messages**.\n\n"
            "📂 Open Telegram → Saved Messages\n"
            "🔐 Keep your session private."
        )


# -------------------------------------------------
# Handle 2FA Password Input
# -------------------------------------------------

@bot.on_message(filters.private & ~filters.command("start"))
async def password_handler(client, message):
    user_id = message.from_user.id

    if user_id not in pending_password:
        return

    app = pending_password[user_id]

    try:
        await app.check_password(message.text)
        me = await app.get_me()
        session_string = await app.export_session_string()

        # Save session in Saved Messages
        await app.send_message(
            "me",
            f"🔐 **Your Pyrogram String Session**\n\n"
            f"`{session_string}`\n\n"
            f"⚠️ Keep it secure."
        )

        await app.disconnect()

        await message.reply(
            f"🎉 **Login Successful!**\n\n"
            f"👤 Name: {me.first_name}\n"
            f"🆔 ID: `{me.id}`\n\n"
            "✅ Session saved in your Saved Messages."
        )

        del pending_password[user_id]

    except Exception:
        await message.reply("❌ Incorrect password. Try again.")


# -------------------------------------------------
# Run Bot
# -------------------------------------------------

if __name__ == "__main__":
    startup_banner()
    bot.run()
