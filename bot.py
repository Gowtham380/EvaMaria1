import os
import asyncio
import logging
import threading
from telethon import TelegramClient, events, Button
from flask import Flask
from pymongo import MongoClient

# ✅ Enable Logging for Debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Load environment variables
API_ID = int(os.getenv("API_ID", "21953115"))  # Replace with your API ID
API_HASH = os.getenv("API_HASH", "edfd34085e9ba51303155f75d77b09ae")  # Replace with your API Hash
BOT_TOKEN = os.getenv("BOT_TOKEN", "6546811614:AAGdwWWHWLcqaneUnM5OpJ12tB0RgKIRzbY")  # Replace with your bot token
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://Gowtham:Gowt380+@cluster0.du2bi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")  # Replace with your MongoDB URL

# ✅ Initialize Telethon Client
client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ✅ Connect to MongoDB for storing files
mongo_client = MongoClient(MONGO_URL)
db = mongo_client["BotDatabase"]
files_collection = db["files"]

# ✅ Flask Web Service (Required for Koyeb)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"

def run_web():
    app.run(host="0.0.0.0", port=8000)

# ✅ Event Handler: Start Command with Buttons
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user = event.sender.first_name
    buttons = [[Button.text("Help ℹ️", resize=True)], [Button.text("Search 🔍", resize=True)]]
    await event.reply(f"Hello {user}! I'm your bot 🤖\n\nUse /help to see available commands.", buttons=buttons)

# ✅ Help Menu
@client.on(events.NewMessage(pattern='/help'))
async def help(event):
    help_text = """
    **Bot Commands:**
    - `/start` - Start the bot
    - `/help` - Show help menu
    - `/search <query>` - Search for files
    - `/admin` - Admin panel (Admins only)
    - `/addfile` - Upload a file to the bot
    """
    await event.reply(help_text)

# ✅ Event Handler: File Upload
@client.on(events.NewMessage(pattern='/addfile'))
async def add_file(event):
    if event.media:
        file = event.media.document
        file_name = file.attributes[0].file_name if file.attributes else "UnknownFile"
        
        # Save file to the database
        file_data = {
            "file_id": file.id,
            "file_name": file_name
        }
        files_collection.insert_one(file_data)
        
        await event.reply(f"✅ File `{file_name}` added to the database!")
    else:
        await event.reply("❌ Please send a file with this command.")

# ✅ Event Handler: Search Files
@client.on(events.NewMessage(pattern='/search (.*)'))
async def search(event):
    query = event.pattern_match.group(1)
    if not query:
        await event.reply("Please provide a search query!")
        return

    results = files_collection.find({"file_name": {"$regex": query, "$options": "i"}})
    file_list = [f"📂 `{file['file_name']}`" for file in results]

    if file_list:
        response = "**Search Results:**\n" + "\n".join(file_list)
    else:
        response = "No matching files found."

    await event.reply(response)

# ✅ Admin Only Commands
@client.on(events.NewMessage(pattern='/admin'))
async def admin(event):
    admin_ids = [6619130727]  # Replace with actual admin IDs
    sender = await event.get_sender()
    
    if sender.id not in admin_ids:
        await event.reply("❌ You are not authorized to use this command.")
        return

    await event.reply("✅ Admin panel activated. Use /ban <user_id> to ban users.")

# ✅ Inline Query Handler (Search in Inline Mode)
@client.on(events.InlineQuery)
async def inline_query(event):
    query = event.text
    if not query:
        return

    results = files_collection.find({"file_name": {"$regex": query, "$options": "i"}})
    articles = [
        event.builder.article(title=file["file_name"], description="Click to get file", text=f"📂 `{file['file_name']}`")
        for file in results
    ]

    await event.answer(articles)

# ✅ Flood Control (Prevent Spamming)
user_message_count = {}

@client.on(events.NewMessage)
async def flood_control(event):
    user_id = event.sender_id
    user_message_count[user_id] = user_message_count.get(user_id, 0) + 1

    if user_message_count[user_id] > 5:
        await event.reply("⚠️ Please slow down! You're sending too many messages.")
        return

# ✅ Run Bot & Web Server in Parallel
if __name__ == '__main__':
    threading.Thread(target=run_web).start()
    with client:
        logger.info("Bot started 🚀")
        client.run_until_disconnected()