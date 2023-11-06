import asyncio
import random
import discord

from discord.ext import commands
from config import DISCORD_TOKEN as TOKEN, MY_USER_ID, MY_GUILD_ID, BOT_USER_ID
from config import MIN_RESPONSE_DELAY, MAX_MIN_RESPONSE_DELAY, MAX_RESPONSE_DELAY, MAX_MAX_RESPONSE_DELAY
from contexts import HISTORY_COUNT, DEFAULT_CONTEXT
from openai_interface import ask_openai, ask_openai_with_history
from utils import debug
from datetime import datetime, timedelta

# Last message time
last_message_time = datetime.utcnow() - timedelta(minutes=30)

#List of channels to check for messages
channel_list = {
  #1170789197393703003: DEFAULT_CONTEXT  # Debugging channel
  1156585342007251042: DEFAULT_CONTEXT  # General Chat
}

# Define the intents
intents = discord.Intents.default()
intents.messages = True  # If you need to handle messages
intents.message_content = True  # Add this line

bot = commands.Bot(command_prefix='!', intents=intents)

#Called when the bot has booted up to report in the console whats happening
@bot.event
async def on_ready():
    debug(f'We have logged in as {bot.user}')
    # Start the response loop
    bot.loop.create_task(respond_to_messages())
    for guild in bot.guilds:
        debug(f"- {guild.name} (ID: {guild.id})")

# Reads discord messages
@bot.event
async def on_message(message):
    # Ignore messages sent by the bot itself
    if message.author == bot.user:
        return

    # Process commands first
    await bot.process_commands(message)

    # Check if the message is a command (starts with the command prefix)
    # If it is, return early to prevent further processing
    ctx = await bot.get_context(message)
    if ctx.valid:
        # It's a command, so don't proceed with custom message handling
        return

    # Custom processing for non-command messages
    #if str(message.author.id) == MY_USER_ID:
        #debug(f"{message.channel}: {message.author.display_name}: {message.content}")
        #openai_response = ask_openai(message)
        #await message.channel.send(openai_response)

#Discord Bot command for when !hello is used
@bot.command()
async def hello(ctx):
    await ctx.send('Hello World!')

#discord Bot command for when !pin is used
@bot.command()
async def ping(ctx):
    await ctx.send('Pong')
    
#discord Bot command for testing new code
@bot.command()
async def testing(ctx):
    
    await process_channels()

def run_bot():    
    #Run the bot
    bot.run(TOKEN)    

def weighted_delay(min_delay, max_delay, time_since_last_message):
    # Calculate delay factor based on time since last message
    delay_factor = time_since_last_message / min_delay
    # Calculate weighted delay
    delay = min_delay * delay_factor
    # Make sure the delay is at least the minimum and at most the maximum
    delay = max(min_delay, min(delay, max_delay))
    return delay

async def respond_to_channel(c):
    global last_message_time

    # Ensure the channel is a text channel where message history is available
    channel = bot.get_channel(c)
    if isinstance(channel, discord.TextChannel):
        # Use the history() method to retrieve messages
        messages = [message async for message in channel.history(limit=HISTORY_COUNT)]
        if (messages[0].author.id != BOT_USER_ID):
            last_message_time = datetime.utcnow()
            messages.reverse()
            openai_response = ask_openai_with_history(messages)
            await channel.send(openai_response)
    

async def process_channels():
    for c in channel_list:
        await respond_to_channel(c)

async def respond_to_messages():
    global last_message_time
    while True:
        # Calculate time since last message
        time_since_last_message = (datetime.utcnow() - last_message_time).total_seconds()

        # Determine the current delay based on the time since the last message
        current_min_delay = weighted_delay(MIN_RESPONSE_DELAY, MAX_MIN_RESPONSE_DELAY, time_since_last_message)
        current_max_delay = weighted_delay(MAX_RESPONSE_DELAY, MAX_MAX_RESPONSE_DELAY, time_since_last_message)

        # Wait for a random amount of time within the current delay window
        delay = random.uniform(current_min_delay, current_max_delay)
        debug("OpenAI loop delay:" + str(delay))
        await asyncio.sleep(delay)

        while 0 <= datetime.utcnow().hour < 6:
            await asyncio.sleep(3600)

        await process_channels()
