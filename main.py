import asyncio
import os
import time
import discord
from dotenv import load_dotenv
from discord.ext import commands
from utils.logger import init_discord_logger
from utils.cache import clear_cache


load_dotenv()

init_discord_logger(log_level=os.environ['LOG_LEVEL'])
client = commands.Bot(command_prefix=os.environ['PREFIX'],
                      help_command=None,
                      intents=discord.Intents.all())

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
client.run(os.environ['TOKEN'], log_handler=None)
print("Shutting down!!")
clear_cache()
