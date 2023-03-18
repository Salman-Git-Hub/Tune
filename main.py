import os
from discord.ext import commands
import discord
from utils.env import TOKEN
import logging
import asyncio
import time
import climage


client = commands.Bot(command_prefix="'",
                      help_command=None,
                      intents=discord.Intents.all())
handler = logging.FileHandler("discord.log", 'w', 'utf-8')


# on ready
@client.event
async def on_ready():
    # Listening activity
    activity = discord.Activity(type=discord.ActivityType.listening, name="Tune")
    await client.change_presence(status=discord.Status.online, activity=activity)
    print("\nBot is ready\n" + " " * 50)


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
client.run(TOKEN, log_handler=handler, log_level=logging.DEBUG)