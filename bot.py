import os
import logging
from dotenv import load_dotenv
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot credentials from environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
CHANNELS = list(map(int, os.getenv("CHANNELS", "").split(",")))  # List of channel IDs
ADMINS = list(map(int, os.getenv("ADMINS", "").split(",")))  # List of admin user IDs

# Initialize bot client
bot = Client("MovieBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Connect to MongoDB
try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client["MovieBotDB"]
    movie_collection = db["movies"]
    logger.info("Connected to MongoDB!")
except Exception as e:
    logger.error(f"MongoDB Connection Error: {e}")

# Start Command
@bot.on_message(filters.command("start"))
def start(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Search Movies", switch_inline_query_current_chat="")]
    ])
    message.reply_text(f"👋 Hello {message.from_user.first_name}!\n\nSearch movies by typing their name.", reply_markup=keyboard)

# Help Command
@bot.on_message(filters.command("help"))
def help_command(client, message):
    message.reply_text("🔍 Search for movies by typing their name.\n\nAdmins can use /filter to add new movies.")

# Add Filter Command (Admin Only)
@bot.on_message(filters.command("filter") & filters.user(ADMINS))
def add_filter(client, message):
    args = message.text.split(" ", 2)
    if len(args) < 3:
        message.reply_text("Usage: `/filter <movie_name> <file_id>`", parse_mode="markdown")
        return

    movie_name, file_id = args[1].lower(), args[2]
    
    # Store movie details in MongoDB
    movie_collection.insert_one({"name": movie_name, "file_id": file_id})
    message.reply_text(f"✅ Movie '{movie_name}' added successfully!")

# Inline Search Handler
@bot.on_inline_query()
def search_movie(client, inline_query):
    query = inline_query.query.lower()
    if not query:
        return
    
    results = []
    movies = movie_collection.find({"name": {"$regex": query, "$options": "i"}})

    for movie in movies:
        results.append(
            InlineQueryResultDocument(
                title=movie["name"],
                document_file_id=movie["file_id"],
                description="Click to download"
            )
        )
    
    inline_query.answer(results, cache_time=10)

# Monitor New Files in Channels (Auto Indexing)
@bot.on_message(filters.channel & filters.document)
def save_movie(client, message):
    if message.chat.id not in CHANNELS:
        return

    movie_name = message.caption.lower() if message.caption else "Unknown Movie"
    file_id = message.document.file_id

    if movie_collection.find_one({"file_id": file_id}):
        return

    movie_collection.insert_one({"name": movie_name, "file_id": file_id})
    logger.info(f"New movie indexed: {movie_name}")

# Run the bot
if __name__ == "__main__":
    bot.run()