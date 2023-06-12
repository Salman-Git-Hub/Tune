import asyncio
import logging
import logging.handlers
import os
import time
import discord
from discord.ext import commands
from utils.cache import clear_cache
from utils.env import TOKEN

client = commands.Bot(command_prefix="'",
                      help_command=None,
                      intents=discord.Intents.all())
logger = logging.getLogger("discord")
logger.propagate = False
logger.setLevel(logging.DEBUG)
logging.getLogger('discord.http').setLevel(logging.INFO)
handler = logging.handlers.RotatingFileHandler(
    filename='discord.log',
    encoding='utf-8',
    maxBytes=10 * 1024 * 1024,  # 10 MiB
    backupCount=2
)
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
logger.addHandler(handler)

try:
    os.mkdir("tmp")
except FileExistsError:
    pass


# on ready
@client.event
async def on_ready():
    # Listening activity
    activity = discord.Activity(type=discord.ActivityType.listening, name="Tune")
    await client.change_presence(status=discord.Status.online, activity=activity)
    print("Bot is ready\n" + " " * 50)


# Loading cogs
async def load_ext():
    val = 0
    cogs = [file[:-3] for file in os.listdir("./cogs") if file.endswith(".py")]
    for cog in cogs:
        await client.load_extension(f'cogs.{cog}')
        val += 1
        print(f"Loading cogs: {(val / len(cogs)) * 100:.2f} % ({cog}.py)" + " " * 8, end='\r')
        time.sleep(0.2)
    print(" " * 120, end='\r')


print("\nStarting Tune!")
asyncio.run(load_ext())
client.run(TOKEN, log_handler=None)
print("Shutting down!!")
clear_cache()
