import os
import asyncio
from telethon import TelegramClient, events, Button
from pymongo import MongoClient
from flask import Flask
import threading

# ✅ Load environment variables
API_ID = int(os.getenv("API_ID", "21953115"))  
API_HASH = os.getenv("API_HASH", "edfd34085e9ba51303155f75d77b09ae")  
BOT_TOKEN = os.getenv("BOT_TOKEN", "6546811614:AAGdwWWHWLcqaneUnM5OpJ12tB0RgKIRzbY")  
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://Gowtham:Gowt380+@cluster0.du2bi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")  
CHANNELS = list(map(int, os.getenv("CHANNELS", "-1002001238432").split(",")))  # ✅ Add multiple channels

# ✅ Initialize Telethon Client
client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ✅ MongoDB Connection
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["MovieBot"]
movies_collection = db["movies"]

# ✅ Auto Indexing: Store files from multiple channels
@client.on(events.NewMessage(chats=CHANNELS))
async def index_movies(event):
    if event.document:
        file_name = event.document.attributes[0].file_name if event.document.attributes else "Unknown"
        file_id = event.message.id
        file_unique_id = event.document.file_unique_id

        movies_collection.update_one(
            {"file_unique_id": file_unique_id},
            {"$set": {"file_name": file_name, "file_id": file_id, "channel_id": event.chat_id}},
            upsert=True
        )
        print(f"Indexed: {file_name} from Channel {event.chat_id}")

# ✅ Search System: Find movies
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

    buttons = [
        [Button.url(movie['file_name'], f"https://t.me/c/{abs(movie['channel_id'])}/{movie['file_id']}")]
        for movie in results
    ]
    
    await event.reply("🎬 **Search Results:**", buttons=buttons)

# ✅ Start Command
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply(
        "👋 Hello! I'm your movie bot.\n\n"
        "🔍 Use /search <movie name> to find movies.\n"
        "🎬 Use inline search (@botusername <movie name>) to find movies."
    )

# ✅ Admin Controls
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

# ✅ Flask Web Service (Keeps bot alive)
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