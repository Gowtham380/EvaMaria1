import asyncio
from telethon import TelegramClient, events

# Replace with your actual API credentials
API_ID = 21953115  # Replace with your API ID
API_HASH = edfd34085e9ba51303155f75d77b09ae
BOT_TOKEN = 6546811614:AAEbnyecTpv_3fs7VRj_uLWb8bmr12NzSK4

# Initialize the bot client
client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Event handler for new messages
@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.respond("Hello! Your bot is running.")

async def main():
    print("Bot is running...")
    await client.run_until_disconnected()  # Keeps the bot running

# Start the bot
with client:
    client.loop.run_until_complete(main())