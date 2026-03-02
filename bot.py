import asyncio
import logging
import base64
import qrcode
from io import BytesIO
from datetime import datetime

from telethon import TelegramClient, Button
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

from config import API_ID, API_HASH, BOT_TOKEN


# -------------------------------------------------
# Logging
# -------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def startup_banner():
    banner = f"""
╔══════════════════════════════════════════════════╗
║                                                  ║
║      🚀 TELETHON QR SESSION GENERATOR           ║
║                                                  ║
╠══════════════════════════════════════════════════╣
║  ✅ Status      : ONLINE                        ║
║  🔐 Engine      : Telethon QR Login             ║
║  🕒 Started At  : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC   ║
║                                                  ║
╚══════════════════════════════════════════════════╝
"""
    logger.info(banner)


# -------------------------------------------------
# Bot Client
# -------------------------------------------------

bot = TelegramClient("qr_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Store active login flows
pending_logins = {}


# -------------------------------------------------
# /start
# -------------------------------------------------

@bot.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    await event.respond(
        "🚀 **Telethon QR Session Generator**\n\n"
        "Generate Telegram session securely using QR login.\n\n"
        "✨ Works with 2FA\n"
        "✨ Same device supported\n"
        "✨ Instant session delivery\n\n"
        "Click below to begin.",
        buttons=[
            [Button.inline("⚡ Generate Session", b"generate")]
        ]
    )


# -------------------------------------------------
# Generate QR
# -------------------------------------------------

from telethon import events

@bot.on(events.CallbackQuery(data=b"generate"))
async def generate_qr(event):
    user_id = event.sender_id

    await event.edit("⏳ Generating QR...")

    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()

    qr_login = await client.qr_login()

    # Generate QR image
    qr = qrcode.make(qr_login.url)
    bio = BytesIO()
    bio.name = "qr.png"
    qr.save(bio, "PNG")
    bio.seek(0)

    pending_logins[user_id] = (client, qr_login)

    await bot.send_file(
        user_id,
        bio,
        caption=(
            "📲 **Scan QR To Login**\n\n"
            "OR tap below if using same device.\n\n"
            "⏳ Expires in 60 seconds."
        ),
        buttons=[
            [Button.url("🔗 Login From This Device", qr_login.url)]
        ]
    )

    # Wait for login
    try:
        await qr_login.wait(timeout=60)
    except asyncio.TimeoutError:
        await bot.send_message(
            user_id,
            "❌ QR Expired.",
            buttons=[[Button.inline("🔄 Regenerate", b"generate")]]
        )
        await client.disconnect()
        return

    # Handle 2FA
    try:
        me = await client.get_me()
    except SessionPasswordNeededError:
        await bot.send_message(
            user_id,
            "🔐 Two-Step Verification Enabled.\n\nPlease send your password."
        )
        pending_logins[user_id] = (client, qr_login)
        return

    await finalize_login(user_id, client)


# -------------------------------------------------
# Handle 2FA Password
# -------------------------------------------------

@bot.on(events.NewMessage)
async def password_handler(event):
    user_id = event.sender_id

    if user_id not in pending_logins:
        return

    client, qr_login = pending_logins[user_id]

    try:
        await client.sign_in(password=event.text)
        await finalize_login(user_id, client)
    except:
        await event.reply("❌ Incorrect password. Try again.")


# -------------------------------------------------
# Finalize Login
# -------------------------------------------------

async def finalize_login(user_id, client):
    me = await client.get_me()
    session_string = client.session.save()

    # Save to Saved Messages
    await client.send_message(
        "me",
        f"🔐 **Your Telethon String Session**\n\n`{session_string}`"
    )

    await bot.send_message(
        user_id,
        f"""
🎉 **Login Successful!**

👤 {me.first_name}
🆔 `{me.id}`

✅ Session saved in Saved Messages.
"""
    )

    await client.disconnect()
    pending_logins.pop(user_id, None)


# -------------------------------------------------
# Run
# -------------------------------------------------

if __name__ == "__main__":
    startup_banner()
    bot.run_until_disconnected()
