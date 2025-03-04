from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, InlineQueryResultDocument
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# Load environment variables correctly
API_ID = int(os.getenv("21953115"))
API_HASH = os.getenv("edfd34085e9ba51303155f75d77b09ae")
BOT_TOKEN = os.getenv("6546811614:AAGdwWWHWLcqaneUnM5OpJ12tB0RgKIRzbY")
MONGO_URL = os.getenv("mongodb+srv://Gowtham:Gowt380+@cluster0.du2bi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

# Database setup
client = AsyncIOMotorClient(MONGO_URL)
db = client['EvaMaria']
files_col = db['files']
users_col = db['users']

bot = Client("EvaMaria", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Start command
def get_start_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Search Files", switch_inline_query="")],
        [InlineKeyboardButton("Help", callback_data="help")]
    ])

@bot.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply_text("Hello! I am a file store bot. Upload a file, and I will save it for you!", reply_markup=get_start_keyboard())
    user_data = {"_id": message.from_user.id, "name": message.from_user.first_name, "joined": datetime.utcnow()}
    await users_col.update_one({"_id": message.from_user.id}, {"$set": user_data}, upsert=True)

# Save files
def get_file_keyboard(file_id):
    return InlineKeyboardMarkup([[InlineKeyboardButton("Download", url=f"https://t.me/{bot.username}?start={file_id}")]])

@bot.on_message(filters.document | filters.video | filters.audio | filters.photo)
async def save_file(client, message: Message):
    file_id = message.document.file_id if message.document else message.video.file_id if message.video else message.audio.file_id if message.audio else message.photo.file_id
    file_data = {"_id": file_id, "file_name": message.caption or "No Name"}
    await files_col.insert_one(file_data)
    await message.reply_text("File saved!", reply_markup=get_file_keyboard(file_id))

# Search stored files
@bot.on_inline_query()
async def inline_search(client, query):
    search_results = files_col.find({"file_name": {"$regex": query.query, "$options": "i"}})
    results = [InlineQueryResultDocument(title=file["file_name"], document=file["_id"]) for file in await search_results.to_list(length=10)]
    await query.answer(results, cache_time=1)

# Broadcast to all users (Admin only)
ADMIN_ID = 123456789  # Replace with your Telegram ID

@bot.on_message(filters.command("broadcast") & filters.user(ADMIN_ID))
async def broadcast(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Usage: /broadcast <message>")
        return

    text = message.text.split(" ", 1)[1]
    users = await users_col.find().to_list(length=10000)

    for user in users:
        try:
            await client.send_message(user["_id"], text)
        except:
            pass

# Run the bot
bot.run()
