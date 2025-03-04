import os
import uvicorn
from fastapi import FastAPI
from threading import Thread
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client["telegram_bot_db"]
movies_collection = db["movies"]
filters_collection = db["filters"]

CHANNELS = list(map(int, os.getenv("CHANNELS", "").split(",")))
ADMINS = list(map(int, os.getenv("ADMINS", "").split(",")))

# Initialize Pyrogram Bot
bot = Client("EvaMaria1", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Start FastAPI for Koyeb health check
app = FastAPI()

@app.get("/")
def home():
    return {"status": "Bot is running"}

# Function to Save Movie Files to MongoDB
def save_to_db(file_id, file_name, file_size, channel_id):
    if not movies_collection.find_one({"file_id": file_id}):
        movies_collection.insert_one({
            "file_id": file_id,
            "file_name": file_name,
            "file_size": file_size,
            "channel_id": channel_id
        })

# Check if the user is an admin
def is_admin(user_id):
    return user_id in ADMINS

# Auto Indexing: Listen for New Files in Channel
@bot.on_message(filters.channel & filters.document)
async def index_files(client, message: Message):
    file_id = message.document.file_id
    file_name = message.document.file_name
    file_size = message.document.file_size
    channel_id = message.chat.id

    if channel_id in CHANNELS:
        save_to_db(file_id, file_name, file_size, channel_id)
        print(f"Indexed: {file_name}")  
    else:
        print("File from unauthorized channel ignored.")

# Start Command
@bot.on_message(filters.command("start"))
async def start(_, message):
    await message.reply_text("Hello! I am your Movie Search Bot. Use /search <movie name> to find movies.")

# Search for Movies in MongoDB
@bot.on_message(filters.command("search"))
async def search_movies(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Please provide a movie name to search.\n\nExample: `/search Inception`")
        return

    query = message.text.split(" ", 1)[1].strip()
    results = movies_collection.find({"file_name": {"$regex": query, "$options": "i"}}).limit(10)

    movie_list = []
    for movie in results:
        file_name = movie["file_name"]
        file_id = movie["file_id"]
        file_size = movie.get("file_size", "Unknown")

        button = InlineKeyboardMarkup([[InlineKeyboardButton("Download", callback_data=f"download_{file_id}")]])
        movie_list.append((file_name, file_size, button, file_id))

    if not movie_list:
        await message.reply_text("No movies found matching your search. Try a different keyword.")
        return

    for name, size, button, file_id in movie_list:
        await message.reply_text(f"🎬 **{name}**\n📦 Size: {size}", reply_markup=button)

# Handle File Download Requests
@bot.on_callback_query()
async def handle_callback_query(client, callback_query):
    data = callback_query.data
    if data.startswith("download_"):
        file_id = data.split("_")[1]
        await client.send_document(chat_id=callback_query.message.chat.id, document=file_id)
        await callback_query.answer("Downloading...")

# Admin Command: Add Filter
@bot.on_message(filters.command("add_filter"))
async def add_filter(client, message: Message):
    if message.from_user.id not in ADMINS:
        await message.reply_text("❌ You are not authorized to use this command.")
        return

    if len(message.command) < 3:
        await message.reply_text("Usage: `/add_filter keyword reply_text`")
        return

    keyword = message.command[1].lower()
    reply_text = " ".join(message.command[2:])

    filters_collection.update_one({"keyword": keyword}, {"$set": {"reply_text": reply_text}}, upsert=True)
    await message.reply_text(f"✅ Filter added for **{keyword}**")

# Admin Command: Remove Filter
@bot.on_message(filters.command("remove_filter"))
async def remove_filter(client, message: Message):
    if message.from_user.id not in ADMINS:
        await message.reply_text("❌ You are not authorized to use this command.")
        return

    if len(message.command) < 2:
        await message.reply_text("Usage: `/remove_filter keyword`")
        return

    keyword = message.command[1].lower()
    result = filters_collection.delete_one({"keyword": keyword})

    if result.deleted_count > 0:
        await message.reply_text(f"✅ Filter for **{keyword}** removed.")
    else:
        await message.reply_text("❌ No such filter found.")

# Admin Command: Show Bot Statistics
@bot.on_message(filters.command("stats"))
async def bot_stats(client, message: Message):
    if message.from_user.id not in ADMINS:
        await message.reply_text("❌ You are not authorized to use this command.")
        return

    total_movies = movies_collection.count_documents({})
    total_filters = filters_collection.count_documents({})

    await message.reply_text(
        f"📊 **Bot Statistics**\n"
        f"🎥 Total Movies Indexed: {total_movies}\n"
        f"🔍 Total Filters: {total_filters}"
    )

# Run bot in a separate thread
def run_bot():
    bot.run()

Thread(target=run_bot).start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)