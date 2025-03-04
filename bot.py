import os
import asyncio
from telethon import TelegramClient, events
from pymongo import MongoClient
from flask import Flask
import threading

# ✅ Load Environment Variables
API_ID = int(os.getenv("API_ID", "21953115"))  
API_HASH = os.getenv("API_HASH", "edfd34085e9ba51303155f75d77b09ae")  
BOT_TOKEN = os.getenv("BOT_TOKEN", "6546811614:AAGdwWWHWLcqaneUnM5OpJ12tB0RgKIRzbY")  
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://Gowtham:Gowt380+@cluster0.du2bi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")  
CHANNELS = [-1002001238432]  # 🔴 Replace with your Telegram channel ID(s)

# ✅ Initialize Telegram Client
client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ✅ Connect to MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["MovieBot"]
movies_collection = db["movies"]

# ✅ Auto-Indexing: Store movie details from channel
@client.on(events.NewMessage(chats=CHANNELS))
async def index_movies(event):
    if event.document:  # Check if it's a file
        file_name = event.document.attributes[0].file_name if event.document.attributes else "Unknown"
        file_id = event.document.id
        file_unique_id = event.document.file_reference

        movies_collection.update_one(
            {"file_unique_id": file_unique_id},
            {"$set": {"file_name": file_name, "file_id": file_id, "channel_id": event.chat_id}},
            upsert=True
        )
        print(f"✅ Indexed: {file_name}")

# ✅ Search System: Find movies in the database
@client.on(events.NewMessage(pattern='/search'))
async def search_movies(event):
    query = event.text.split(maxsplit=1)[-1].strip()
    if not query:
        await event.reply("⚠️ Please enter a movie name to search.")
        return

    results = list(movies_collection.find({"file_name": {"$regex": query, "$options": "i"}}).limit(10))
    
    if not results:
        await event.reply("❌ No movies found.")
        return

    response = "🎬 **Search Results:**\n\n"
    for movie in results:
        response += f"📂 `{movie['file_name']}`\n👉 [Download](https://t.me/{event.chat.username}/{movie['file_id']})\n\n"
    
    await event.reply(response, link_preview=False)

# ✅ Inline Search System
@client.on(events.InlineQuery)
async def inline_search(event):
    query = event.text.strip()
    if not query:
        return

    results = list(movies_collection.find({"file_name": {"$regex": query, "$options": "i"}}).limit(10))
    
    if not results:
        await event.answer([], switch_pm_text="❌ No movies found.", switch_pm_parameter="start")
        return

    articles = [
        client.builder.article(
            title=movie["file_name"],
            description="Click to download",
            url=f"https://t.me/{event.chat.username}/{movie['file_id']}",
            text=f"🎬 **{movie['file_name']}**\n👉 [Download](https://t.me/{event.chat.username}/{movie['file_id']})"
        )
        for movie in results
    ]
    await event.answer(articles)

# ✅ Admin Control: Filter Management
@client.on(events.NewMessage(pattern='/filter'))
async def filter_command(event):
    if not await is_admin(event.chat_id, event.sender_id):
        await event.reply("🚫 Only admins can use this command.")
        return
    await event.reply("✅ Admin filter settings applied.")

async def is_admin(chat_id, user_id):
    try:
        participant = await client.get_participant(chat_id, user_id)
        return participant.is_admin
    except:
        return False

# ✅ Flask Web Service for Koyeb Deployment
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"

def run_web():
    app.run(host="0.0.0.0", port=8000)

# ✅ Run Bot & Web Server Together
if __name__ == '__main__':
    threading.Thread(target=run_web).start()
    with client:
        print("🚀 Bot started successfully!")
        client.run_until_disconnected()