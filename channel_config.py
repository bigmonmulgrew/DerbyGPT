import json, random, math
from config import CHANNEL_DEFAULTS as DEFAULTS, RESPONSE_RATE_RANDOMNESS as RRR, GLOBAL_RESPONSE_MULTIPLIER, MIN_GLOBAL_MULTIPLIER
from datetime import datetime
from utils import clamp, debug

class ChannelConfig:
    watched_channels = {}  # Class variable to hold all channel configurations, Now a dictionary of dictionaries keyed by guild ID
    guild_tasks = {}  # New dictionary to keep track of tasks for each guild
    last_global_response = {}  # Now a dictionary mapping guild IDs to last response times
    guild_pings = {}  # Track global pings per guild
    guild_messages = {}  # Track global messages per guild

    def __init__(self, guild_id, channel_id, context_id=0, 
                 min_response_time=DEFAULTS["min_response_time"],
                 max_response_time=DEFAULTS["max_response_time"],
                 min_response_time_cap=DEFAULTS["min_response_time_cap"],
                 max_response_time_cap=DEFAULTS["max_response_time_cap"],
                 idle_growth_factor=DEFAULTS["idle_growth_factor"],
                 attention_factor=DEFAULTS["attention_factor"]):
        
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.context_id = context_id
        self.min_response_time = min_response_time
        self.max_response_time = max_response_time
        self.min_response_time_cap = min_response_time_cap
        self.max_response_time_cap = max_response_time_cap
        self.idle_growth_factor = idle_growth_factor
        self.attention_factor = attention_factor
        self.channel_pings = 0  # Track pings for this channel
        self.channel_messages = 0  # Track messages for this channel
        self.last_response = None   # Initialized as None
        self.adjusted_min_response_time = self.min_response_time
        self.adjusted_max_response_time = self.max_response_time

    def to_dict(self):
        return {
            "channel_id": self.channel_id,
            "context_id": self.context_id,
            "min_response_time": self.min_response_time,
            "max_response_time": self.max_response_time,
            "min_response_time_cap": self.min_response_time_cap,
            "max_response_time_cap": self.max_response_time_cap,
            "idle_growth_factor": self.idle_growth_factor,
            "attention_factor": self.attention_factor
        }
    
    def respond_probability(self):
        """
        Calculate the probability to respond based on the elapsed time.
        Linearly scales from 0 to 1 as time moves from min_response_time to max_response_time.
        """
        min_time = self.adjusted_min_response_time
        max_time = self.adjusted_max_response_time

        elapsed_time = self.elapsed_time()
        time_range = max_time - min_time

        # Calculate linear probability
        debug(f"time range: {time_range}, elapsed time: {elapsed_time}, max: {max_time}, min: {min_time}")
        linear = max((elapsed_time - min_time) / time_range, 0) if time_range > 0 else 0
        pbty = linear
           
        # Multiply by a random factor, e.g., between 0.9 and 1.1, using config RESPONSE_RATE_RANDOMNESS
        random_fact = random.uniform(1 - RRR, 1 + RRR)
        pbty *= random_fact

        # Multiply by a global activity scale making response more likely when other channels have a lot of activity
        global_fact = self.calculate_global_factor()
        pbty *= global_fact

        # modify the probability based on pings
        ping_fact = self.ping_factor()
        pbty *=  ping_fact

        # Modify the probability based on messages
        message_fact = self.message_factor()
        pbty *= message_fact
        
        msg  = f"Calculating probability in {self.channel_id}\nResponse probability: {pbty}\n"
        msg += f"linear: {linear}\n"
        msg += f"random_fact: {random_fact}\n"
        msg += f"global_fact: {global_fact}\n"
        msg += f"ping_fact: {ping_fact}\n"
        msg += f"message_fact: {message_fact}"
        
        debug(msg)

        return clamp(pbty, 0, 1)

    def calculate_global_factor(self):
        """
        Calculate a probability modifier based on the time since there was a response in any channel
        """

        min_time = self.min_response_time
        max_time = self.max_response_time
        elapsed_time = self.elapsed_time_global(self.guild_id)
        time_range = max_time - min_time

        # Invert the calculation: High factor for low elapsed time, and vice versa
        global_factor = GLOBAL_RESPONSE_MULTIPLIER - ((elapsed_time - min_time) / time_range) * (GLOBAL_RESPONSE_MULTIPLIER - MIN_GLOBAL_MULTIPLIER)

        return clamp(global_factor, MIN_GLOBAL_MULTIPLIER, GLOBAL_RESPONSE_MULTIPLIER)  # Ensure it never goes below the minimum
    
    def ping_factor(self):
        a = self.attention_factor
        channel_pings = self.channel_pings
        guild_pings = ChannelConfig.guild_pings.get(self.guild_id, 0)

        # Exponential increase in probability based on pings
        return (a ** guild_pings + a ** channel_pings) / 2

    def message_factor(self):
        channel_messages = self.channel_messages  # Assuming this tracks the number of messages in the channel
        guild_messages = ChannelConfig.guild_messages.get(self.guild_id, 0)  # Assuming a similar structure for guild messages

        # Calculate the logarithmic factors, ensuring a minimum value of 1
        log_guild = math.log1p(guild_messages) + 1
        log_channel = math.log1p(channel_messages) + 1

        # Logarithmic increase in probability based on messages
        # Add 1 to message counts to handle log(0) and ensure a minimum factor of 1
        return (log_guild + log_channel) / 2

    def respond_now(self):
        # If last_response is None, use random chance to decide
        if self.last_response is None: 
            if random.random() < 0.25:
                self.update_on_response()
                return True  # 25% chance to return True
            else:
                return False
        
        if self.respond_probability() < 1:
            return False
        
        self.update_on_response()
        return True

    def elapsed_time(self):
        """
        Calculate and return the elapsed time in seconds since the last response.
        """
        if self.last_response is None:
            return 0  # If there hasnt been a response 

        return (datetime.now() - self.last_response).total_seconds()

    def update_adjusted_response_times(self):
        # Increase the adjusted times based on the idle growth factor
        self.adjusted_min_response_time = min(self.adjusted_min_response_time * self.idle_growth_factor, self.min_response_time_cap)
        self.adjusted_max_response_time = min(self.adjusted_max_response_time * self.idle_growth_factor, self.max_response_time_cap)

    def update_on_response(self):
        self.last_response = datetime.now()
        ChannelConfig.last_global_response[self.guild_id] = self.last_response
        self.adjusted_min_response_time = self.min_response_time
        self.adjusted_max_response_time = self.max_response_time

        self.remove_pings()
        self.remove_messages()
    
    def register_ping(self):
        self.channel_pings += 1
        if self.guild_id in ChannelConfig.guild_pings:
            ChannelConfig.guild_pings[self.guild_id] += 1
        else:
            ChannelConfig.guild_pings[self.guild_id] = 1

    def remove_pings(self):
        # Decrease the guild's global ping count by this channel's pings
        if self.guild_id in ChannelConfig.guild_pings:
            ChannelConfig.guild_pings[self.guild_id] = max(0, ChannelConfig.guild_pings[self.guild_id] - self.channel_pings)

        # Reset this channel's ping count to 0
        self.channel_pings = 0

    def register_message(self):
        self.channel_messages += 1
        if self.guild_id in ChannelConfig.guild_messages:
            ChannelConfig.guild_messages[self.guild_id] += 1
        else:
            ChannelConfig.guild_messages[self.guild_id] = 1

    def remove_messages(self):
        # Decrease the guild's global message count by this channel's messages
        if self.guild_id in ChannelConfig.guild_messages:
            ChannelConfig.guild_messages[self.guild_id] = max(0, ChannelConfig.guild_messages[self.guild_id] - self.channel_messages)

        # Reset this channel's message count to 0
        self.channel_messages = 0

    @classmethod
    def elapsed_time_global(cls, guild_id):
        """
        Calculate and return the elapsed time in seconds since the last global response for the specified guild.
        """
        if guild_id not in cls.last_global_response:
            return 30  # Default value if no response has been recorded

        return (datetime.now() - cls.last_global_response[guild_id]).total_seconds()
    
    @classmethod
    def load_config(cls, file_path):
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                for guild_id, channels in data.items():
                    cls.watched_channels[int(guild_id)] = {int(channel_id): cls(guild_id=int(guild_id), **config) for channel_id, config in channels.items()}
        except FileNotFoundError:
            cls.watched_channels = {}

    @classmethod
    def save_config(cls, file_path):
        with open(file_path, 'w') as file:
            data = {guild_id: {channel_id: config.to_dict() for channel_id, config in channels.items()} for guild_id, channels in cls.watched_channels.items()}
            json.dump(data, file, indent=4)

    @classmethod
    def remove_channel(cls, guild_id, channel_id):
        if guild_id in cls.watched_channels and channel_id in cls.watched_channels[guild_id]:
            # Remove the channel
            del cls.watched_channels[guild_id][channel_id]
            cls.save_config('watched_channels.json')

            # If no more channels in this guild, cancel the task and remove it
            if not cls.watched_channels[guild_id]:
                if guild_id in cls.guild_tasks and cls.guild_tasks[guild_id]:
                    cls.guild_tasks[guild_id].cancel()
                    del cls.guild_tasks[guild_id]

    @classmethod
    def list_channels(cls, bot):
        response = "Currently watched channels:\n"
        for guild_id, channels in cls.watched_channels.items():
            for channel_id, config in channels.items():
                channel = bot.get_channel(channel_id)
                channel_name = channel.name if channel else f"Unknown Channel (ID: {channel_id})"
                response += (f"- Guild ID: {guild_id}, {channel_name} (ID: {channel_id}) "
                            f"| Context: {config.context_id} "
                            f"| Min Response Time: {config.min_response_time} "
                             f"| Max Response Time: {config.max_response_time} "
                             f"| Min Response Time Cap: {config.min_response_time_cap} "
                             f"| Max Response Time Cap: {config.max_response_time_cap} "
                             f"| Idle Growth Factor: {config.idle_growth_factor} "
                             f"| Attention Factor: {config.attention_factor}\n"
                            )
        return response if cls.watched_channels else "No channels are currently being watched."