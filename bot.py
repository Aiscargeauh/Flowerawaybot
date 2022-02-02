from datetime import datetime
import os
import platform
import random
import sys
import logging
from logging.handlers import TimedRotatingFileHandler

import discord
import yaml
from discord.ext import commands
from discord.ext import tasks
from discord.ext.commands import Bot

"""	
Setup bot intents (events restrictions)
For more information about intents, please go to the following websites:
https://discordpy.readthedocs.io/en/latest/intents.html
https://discordpy.readthedocs.io/en/latest/intents.html#privileged-intents
Default Intents:
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.emojis = True
intents.bans = True
intents.guild_typing = False
intents.typing = False
intents.dm_messages = False
intents.dm_reactions = False
intents.dm_typing = False
intents.guild_messages = True
intents.guild_reactions = True
intents.integrations = True
intents.invites = True
intents.voice_states = False
intents.webhooks = False
Privileged Intents (Needs to be enabled on dev page), please use them only if you need them:
intents.presences = True
intents.members = True
"""

intents = discord.Intents.default()
intents.dm_messages = True
intents.reactions = True
with open("config.yaml") as file:
    config = yaml.load(file, Loader=yaml.FullLoader)
bot = Bot(command_prefix=config["bot_prefix"], intents=intents)

def create_rotating_log():
    """
    Creates a rotating log
    """
    logger = logging.getLogger("GiveawayLogger")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s]|[%(levelname)s]-> %(message)s', "%Y/%m/%d %H:%M")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    # add a rotating handler
    handler = TimedRotatingFileHandler("Logs/command_logs", when='h', interval=1, backupCount=0, encoding=None, delay=False, utc=False, atTime=None)
    #handler.suffix = '%Y%m%d'
    logger.addHandler(handler)

# The code in this even is executed when the bot is ready
@bot.event
async def on_ready():
    logger = logging.getLogger("GiveawayLogger")
    logger.info(f"Logged in as {bot.user.name}")
    logger.info(f"Discord.py API version: {discord.__version__}")
    logger.info(f"Python version: {platform.python_version()}")
    logger.info(f"Running on: {platform.system()} {platform.release()} ({os.name})")
    logger.info("-------------------")
    #if not status_task.is_running():
    status_task.start()


# Setup the game status task of the bot
@tasks.loop(minutes=1.0)
async def status_task():
    with open("config.yaml") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
    statuses = [f"{config['bot_prefix']}help triggers me",
        '"Lol every now and then I have to throw it on the table and measure" - Nick Doliner',
        "FLOWER POWER!",
        "floweraway1 on twitter!",
        "Profile pic by Takashi Murakami",
        '"I was going to do a giveaway, but gaissa won before I even announced it :pepewat:" - Achaean',
        "Foxtrot Lima Oscar Whiskey Echo Romeo Papa Alpha Tango Charlie Hotel",
        "[flɑʊəpætʃ]"]
    await bot.change_presence(activity=discord.Game(random.choice(statuses)))

# Create log file
create_rotating_log()
# Removes the default help command of discord.py to be able to create our custom help command.
bot.remove_command("help")

if __name__ == "__main__":
    for file in os.listdir("./cogs"):
        if file.endswith(".py"):
            logger = logging.getLogger("GiveawayLogger")
            extension = file[:-3]
            try:
                bot.load_extension(f"cogs.{extension}")
                logger.info(f"Loaded extension '{extension}'")
            except Exception as e:
                exception = f"{type(e).__name__}: {e}"
                logger.info(f"Failed to load extension {extension}\n{exception}")


# The code in this event is executed every time someone sends a message, with or without the prefix
@bot.event
async def on_message(message):
    # Ignores if a command is being executed by a bot or by the bot itself
    if message.author == bot.user or message.author.bot:
        return

    if "flowers are not securities" in message.content.lower():
        await message.add_reaction(emoji="👍")
        
    if "flowers are securities" in message.content.lower():
        await message.add_reaction(emoji="👎")
        

    # Ignores if a command is being executed by a blacklisted user
    with open("config.yaml") as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    if message.author.id in config["blacklist"]:
        return
    await bot.process_commands(message)


# The code in this event is executed every time a command has been *successfully* executed
@bot.event
async def on_command_completion(ctx):
    fullCommandName = ctx.command.qualified_name
    logger = logging.getLogger("GiveawayLogger")
    logger.info(f"Executed {fullCommandName} command at {datetime.now()}, by {ctx.message.author.display_name} (ID: {ctx.message.author.id}))")


# The code in this event is executed every time a valid commands catches an error
@bot.event
async def on_command_error(context, error):
    if isinstance(error, commands.CommandOnCooldown):
        minutes, seconds = divmod(error.retry_after, 60)
        hours, minutes = divmod(minutes, 60)
        hours = hours % 24
        embed = discord.Embed(
            title="Hey, please slow down!",
            description=f"You can use this command again in {f'{round(hours)} hours' if round(hours) > 0 else ''} {f'{round(minutes)} minutes' if round(minutes) > 0 else ''} {f'{round(seconds)} seconds' if round(seconds) > 0 else ''}.",
        )
        await context.send(embed=embed)
    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="Error!",
            description="You are missing the permission `" + ", ".join(
                error.missing_perms) + "` to execute this command!",
        )
        await context.send(embed=embed)
    raise error

# Run the bot with the token
bot.run(os.getenv("discord_token"))