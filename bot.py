import os
import asyncio
from telethon import TelegramClient, events
from flask import Flask
import threading

# ✅ Load environment variables (Replace these with your actual values)
API_ID = int(os.getenv("API_ID", "21953115"))  # Replace with your API ID
API_HASH = os.getenv("API_HASH", "edfd34085e9ba51303155f75d77b09ae")  # Replace with your API Hash
BOT_TOKEN = os.getenv("BOT_TOKEN", "6546811614:AAGdwWWHWLcqaneUnM5OpJ12tB0RgKIRzbY")  # Replace with your bot token

# ✅ Initialize Telethon Client
client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ✅ Event Handler: Respond to /start command
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply("Hello! I'm your bot 🤖")

# ✅ Flask Web Service (Required for Koyeb)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"

def run_web():
    app.run(host="0.0.0.0", port=8000)

# ✅ Run Bot & Web Server in Parallel
if __name__ == '__main__':
    threading.Thread(target=run_web).start()
    with client:
        print("Bot started 🚀")
        client.run_until_disconnected()