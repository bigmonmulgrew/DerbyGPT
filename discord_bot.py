import asyncio
import random
import discord
import os
from channel_config import ChannelConfig

from discord.ext import commands
#splitting imports from config into groups for for readability
from config import DISCORD_TOKEN as TOKEN, BOT_USER_ID
from config import BOT_CHECK_TIME
from config import STATUS_LIST, STATUS_UPDATE_CHANCE
from contexts import HISTORY_COUNT_GENERAL, HISTORY_COUNT_ACADEMIC
from openai_interface import ask_openai, ask_openai_with_history
from utils import debug
from datetime import datetime
from contexts import context_manager as CONTEXT

# Initial loading of the configuration
ChannelConfig.load_config('watched_channels.json')

# Define the intents
intents = discord.Intents.default()
intents.messages = True  # If you need to handle messages
intents.message_content = True  # Add this line
intents.members = True  # Enable members intent

bot = commands.Bot(command_prefix='!', intents=intents)

#Called when the bot has booted up to report in the console whats happening
@bot.event
async def on_ready():
    debug(f'We have logged in as {bot.user}')

    for guild in bot.guilds:
        debug(f"Member of - {guild.name} (ID: {guild.id})")

    # Start the response loop, one for each guild
    for guild in bot.guilds:
        debug(f"Starting task to watch - {guild.name} (ID: {guild.id})")
        ChannelConfig.guild_tasks[guild.id] = bot.loop.create_task(check_channels(guild.id))

    await set_status(bot)

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

    # Check if the bot is mentioned in the message to trigger a faster response
    if bot.user in message.mentions:
        debug(f'Someone called me {bot.user}')
        await tagged_me(message)
    
    # When a message is sent trigger a faster response
    await get_attention(message)

# Privacy Command
@bot.command()
async def privacy(ctx):
    # Check if the user is allowed to use the command
    if not await command_allowed(ctx, access_level=0):
        return
    
    msg = "Privacy policy and data handling practices.\n"
    msg += "This bot is experimental and as such the below may be inaccurate, although best effort is made to ensure accuracy.\n"
    msg += "Data may be captured in an anonymised form, or you may opt in to remain identified.\n"
    msg += "Data captured is stored ina github repository here: <https://github.com/bigmonmulgrew/DerbyGPT>\n"
    msg += "This bot uses OpenAI to generate responses and Discord, their own policies will also apply.\n"
    msg += "Discord: <https://discord.com/privacy>\n"
    msg += "OpenAI: <https://openai.com/enterprise-privacy>\n"
    msg += "A key point from the OpenAI privacy policy, after March 1st 2023 data from the APi isn't used to train the model, its also retained for 30 days for abuse monitoring."
    await ctx.send(msg)

@bot.command()
async def general(ctx):
    # Check if the user is allowed to use the command
    if not await command_allowed(ctx, access_level=1):
        return
    
    # Add or update the channel configuration
    msg = f"Channel {ctx.channel} is now marked as a general channel and being watched."
    await add_channel_watch(ctx, msg)

# Academic Command
@bot.command()
async def academic(ctx):
    # Check if the user is allowed to use the command
    if not await command_allowed(ctx, access_level=1):
        return
    
    # Add or update the channel configuration
    msg = f"Channel {ctx.channel} is now marked as a academic help channel and being watched."
    await add_channel_watch(ctx, msg, context_id = 1)

@bot.command()
async def list_channels(ctx):
    # Check if the user is allowed to use the command
    if not await command_allowed(ctx, access_level=1):
        return
    
    #List channels the bot watches
    response = ChannelConfig.list_channels(bot)
    await ctx.send(response)

@bot.command()
async def unwatch(ctx):
    # Check if the user is allowed to use the command
    if not await command_allowed(ctx, access_level=1):
        return
    
    guild_id = ctx.guild.id
    channel_id = ctx.channel.id
    if guild_id in ChannelConfig.watched_channels and channel_id in ChannelConfig.watched_channels[guild_id]:
        ChannelConfig.remove_channel(guild_id, channel_id)
        await ctx.send(f"Channel {ctx.channel} has been unwatched.")
    else:
        await ctx.send("This channel is not being watched.")

# Config Command
@bot.command()
async def config(ctx, *, args=None):
    # Ensure the user is allowed to use the command
    if not await command_allowed(ctx, access_level=1):
        return

    guild_id = ctx.guild.id
    channel_id = ctx.channel.id

    # Check if the channel is being watched
    if guild_id not in ChannelConfig.watched_channels or channel_id not in ChannelConfig.watched_channels[guild_id]:
        await ctx.send("This channel is not currently being watched so has no configuration.")
        return

    channel_config = ChannelConfig.watched_channels[guild_id][channel_id]

    # If no arguments are provided, display the current configuration
    if args is None:
        await list_config(ctx,channel_config)
        return

    # Parse arguments and update configuration
    await parse_command_arguments(ctx, channel_config, args)

    # Save updated configuration
    ChannelConfig.save_config('watched_channels.json')
    await ctx.send("Configuration updated.")

async def list_config(ctx,channel_config):
    config_msg = f"Current configuration for {ctx.channel}:\n"
    config_msg += "```\n"  # Start of code block
    config_msg += f"min_response_time:      {channel_config.min_response_time}   # Minimum time before the bot can respond in that channel\n"
    config_msg += f"max_response_time:      {channel_config.max_response_time}   # Time before response probability (due to time) maxes out\n"
    config_msg += f"min_response_time_cap:  {channel_config.min_response_time_cap}  # Response times will increase with inactivity, this limits its growth\n"
    config_msg += f"max_response_time_cap:  {channel_config.max_response_time_cap}  # Response times will increase with inactivity, this limits its growth\n"
    config_msg += f"idle_growth_factor:     {channel_config.idle_growth_factor}  # The rate at which response times will increase while inactive\n"
    config_msg += f"attention_factor:       {channel_config.attention_factor}    # Factor to increase response probability based on pings\n"
    config_msg += "```\n"  # End of code block
    # ... include other settings ...
    await ctx.send(config_msg)
            
async def parse_command_arguments(ctx, channel_config, args):
    settings_map = {
        "min_response_time": "min_response_time",
        "max_response_time": "max_response_time",
        "min_response_time_cap": "min_response_time_cap",
        "max_response_time_cap": "max_response_time_cap",
        "idle_growth_factor": "idle_growth_factor",
        "attention_factor": "attention_factor",
        # ... other mappings ...
    }

    updated_settings = []

    for arg in args.split():
        if '=' not in arg:
            await ctx.send(f"Invalid format for argument '{arg}'. Expected format: key=value")
            continue

        key, value = arg.split('=', 1)
        if key in settings_map:
            try:
                setattr(channel_config, settings_map[key], int(value))
                updated_settings.append(f"{key} set to {value}")
            except ValueError:
                await ctx.send(f"Invalid value for {key}. Expected an integer.")
        else:
            await ctx.send(f"Invalid config key: {key}")

    # Summarize changes made
    if updated_settings:
        await ctx.send("Updated settings:\n" + "\n".join(updated_settings))
    else:
        await ctx.send("No valid settings were provided to update.")


def run_bot():    
    #Run the bot
    bot.run(TOKEN)    

def generate_delay_steps(total_delay):
    debug("Generate delay steps, Total delay:" + str(total_delay))
    total_delay = round(total_delay)
    factors = []
    for i in range(1, int(total_delay**0.5) + 1):
        if total_delay % i == 0:
            factors.append(i)
            if i != total_delay // i:
                factors.append(total_delay // i)

    debug("Generate delay steps, factors:" + str(factors))
    factors.sort()

    # Picking a factor from two-thirds the way along the list
    index = len(factors) * 2 // 3
    part_delay = factors[index]

    # Calculating the second factor
    iterations = total_delay // part_delay

    return part_delay, iterations

async def command_allowed(ctx, access_level = 1):
    """
    Check if a user should have access to a command.
    access_level = 0, no special access required, return true.
    access_level = 1, default behaviour, must be server owner.
    access_level = 2, not implemented, must havbe assigned mod role.
    """
    if access_level == 0:
        return True
    if access_level == 1:
        test = ctx.guild is not None and ctx.author == ctx.guild.owner 
        
        if not test:
            await ctx.send("Sorry, you don't have permission to use this command.")
        return test
        
    # Catch all for incorrect usage
    debug(f"Incorrect usage of command_allowed with access level: {access_level}")
    return False

async def add_channel_watch(ctx, msg, context_id = 0):
    guild_id = ctx.guild.id
    channel_id = ctx.channel.id

    # Check if the guild is new
    if guild_id not in ChannelConfig.watched_channels:
        ChannelConfig.watched_channels[guild_id] = {}
        # Start a new task for the new guild
        ChannelConfig.guild_tasks[guild_id] = bot.loop.create_task(check_channels(guild_id))

    # Add or update the channel configuration
    if channel_id not in ChannelConfig.watched_channels[guild_id]:
        ChannelConfig.watched_channels[guild_id][channel_id] = ChannelConfig(guild_id, channel_id, context_id=context_id)
        ChannelConfig.save_config('watched_channels.json')
        await ctx.send(msg)
    else:
        await ctx.send(f"Channel {ctx.channel} is already being watched.")

async def respond_to_channel(c, history_count=HISTORY_COUNT_GENERAL, context_string=CONTEXT(0)):
    global last_general_message_time

    # Ensure the channel is a text channel where message history is available
    channel = bot.get_channel(c)
    if isinstance(channel, discord.TextChannel):
        messages = [message async for message in channel.history(limit=history_count)]
        if messages and (messages[0].author.id != BOT_USER_ID):
            last_general_message_time = datetime.utcnow()
            messages.reverse()

            # Set typing indicator
            async with channel.typing():
                openai_response = ask_openai_with_history(messages, context=context_string)

            # Check if the response is too long and split if necessary
            if len(openai_response) > 2000:
                # Split the response at newline characters near the 2000 character mark
                responses = split_response(openai_response)
                for response_part in responses:
                    async with channel.typing():
                        await asyncio.sleep(10)
                    await channel.send(response_part)
                    # Wait and show typing indicator between messages                    
            else:
                await channel.send(openai_response)

            # % chance to update the status
            if random.random() < STATUS_UPDATE_CHANCE:
                await set_status(bot)

def split_response(response, limit=2000, delimiter='\n'):
    """
    Splits a long string into parts, each with a maximum length of 'limit'.
    Tries to split at 'delimiter' to avoid breaking words.
    """
    parts = []
    while response:
        if len(response) <= limit:
            parts.append(response)
            break
        else:
            # Find nearest delimiter to the limit
            split_index = response.rfind(delimiter, 0, limit)
            if split_index == -1:  # No delimiter found, hard split at the limit
                split_index = limit

            parts.append(response[:split_index])
            response = response[split_index:].lstrip(delimiter)  # Remove leading delimiter from next part

    return parts

async def check_channels(guild_id):
    while True:
        # Wait a random amount of time between checking channels
        cycle_delay = random.uniform(1, BOT_CHECK_TIME)
        debug(f"Checking channels in guild {guild_id} after delay: {cycle_delay:.2f}")
        await asyncio.sleep(cycle_delay)

        # Loop through the channels of the specified guild
        channels = ChannelConfig.watched_channels.get(guild_id, {})
        for channel_id, channel_config in channels.items():
            debug(f"Checking channel: {channel_id} in guild: {guild_id}")

            if not channel_config.respond_now():
                continue

            # Bot decides to send a response
            history = HISTORY_COUNT_GENERAL if channel_config.context_id == 0 else HISTORY_COUNT_ACADEMIC
            await respond_to_channel(channel_id, history_count = history ,  context_string=CONTEXT(channel_config.context_id))

async def tagged_me(message):
    # Reduces the chat delay when theb bot is tagged
    # For example, modifying delay or sending a response
    # Example: print(f"I was tagged in a message by {message.author.display_name}")

    # Retrieve the channel and guild IDs from the message
    guild_id = message.guild.id
    channel_id = message.channel.id

    # Check if the channel configuration exists
    if guild_id in ChannelConfig.watched_channels and channel_id in ChannelConfig.watched_channels[guild_id]:
        channel_config = ChannelConfig.watched_channels[guild_id][channel_id]
        channel_config.register_ping()

async def get_attention(message):
    # When users chat it should reduce the delay time of the bot.

    # Retrieve the channel and guild IDs from the message
    guild_id = message.guild.id
    channel_id = message.channel.id

    # Check if the channel configuration exists and register the message
    if guild_id in ChannelConfig.watched_channels and channel_id in ChannelConfig.watched_channels[guild_id]:
        channel_config = ChannelConfig.watched_channels[guild_id][channel_id]
        channel_config.register_message()

async def set_status(bot):
    # List of potential statuses
    statuses = STATUS_LIST

    # Randomly choose a status
    activity_type, name = random.choice(statuses)

    # Map the string to the actual Discord activity type
    if activity_type == "Playing":
        activity = discord.Game(name=name)
    elif activity_type == "Listening to":
        activity = discord.Activity(type=discord.ActivityType.listening, name=name)
    elif activity_type == "Watching":
        activity = discord.Activity(type=discord.ActivityType.watching, name=name)

    # Set the bot's status
    await bot.change_presence(activity=activity)

    