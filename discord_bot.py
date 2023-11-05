import asyncio
import random
import discord

from discord.ext import commands
from config import DISCORD_TOKEN as TOKEN, MY_USER_ID, MY_GUILD_ID
from config import MIN_RESPONSE_DELAY, MAX_MIN_RESPONSE_DELAY, MAX_RESPONSE_DELAY, MAX_MAX_RESPONSE_DELAY
from openai_interface import ask_openai
from utils import debug
from datetime import datetime, timedelta

# Last message time
last_message_time = datetime.utcnow() - timedelta(minutes=30)

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
    # Ignore messages sent by the bot itself or by any other user that is not you
    if message.author == bot.user or str(message.author.id) != MY_USER_ID:
        return

    # Print message content to console for debugging
    debug(f"{message.channel}: {message.author.display_name}: {message.content}")

    #Send to chatGPT
    openai_response = ask_openai(message)
    await message.channel.send(openai_response)

    # Important: Without this line, commands won't work.
    await bot.process_commands(message)

#Discord Bot command for when !hello is used
@bot.command()
async def hello(ctx):
    await ctx.send('Hello World!')

#discord Bot command for when !pin is used
@bot.command()
async def ping(ctx):
    await ctx.send('Pong')

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
        await asyncio.sleep(delay)

        # Find the debugging channel
        # Note: Replace 'your_guild_id' with the actual ID of your server (guild)
        guild = bot.get_guild(MY_GUILD_ID)
        debugging_channel = discord.utils.get(guild.text_channels, name='debugging')

        if debugging_channel:
            # Generate a random number and send a message based on that
            roll = random.randint(1, 6)
            current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            if roll == 6:
                await debugging_channel.send(f"Test, sent at {current_time}. I detected a message, current delay {delay}")
                # Update the last message time
                last_message_time = datetime.utcnow()
            else:
                await debugging_channel.send(f"Test, sent at {current_time}, no new messages, sleeping, current delay {delay}")

        else:
            print("Debugging channel not found.")
