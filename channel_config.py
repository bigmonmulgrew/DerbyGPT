import json

class ChannelConfig:
    watched_channels = {}  # Class variable to hold all channel configurations
    
    def __init__(self, channel_id, context_id, min_delay, max_delay, min_delay2, max_delay2):
        self.channel_id = channel_id
        self.context_id = context_id
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.min_delay2 = min_delay2
        self.max_delay2 = max_delay2

    def to_dict(self):
        return {
            "channel_id": self.channel_id,
            "context_id": self.context_id,
            "min_delay": self.min_delay,
            "max_delay": self.max_delay,
            "min_delay2": self.min_delay2,
            "max_delay2": self.max_delay2
        }

    @classmethod
    def load_config(cls, file_path):
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                cls.watched_channels = {int(channel): cls(**config) for channel, config in data.items()}
        except FileNotFoundError:
            cls.watched_channels = {}

    @classmethod
    def save_config(cls, file_path):
        with open(file_path, 'w') as file:
            json.dump({channel: config.to_dict() for channel, config in cls.watched_channels.items()}, file, indent=4)

    @classmethod
    def remove_channel(cls, channel_id):
        if channel_id in cls.watched_channels:
            del cls.watched_channels[channel_id]
            cls.save_config('watched_channels.json')

    @classmethod
    def list_channels(cls, bot):
        if cls.watched_channels:
            response = "Currently watched channels:\n"
            for channel_id, config in cls.watched_channels.items():
                channel = bot.get_channel(channel_id)
                channel_name = channel.name if channel else f"Unknown Channel (ID: {channel_id})"
                response += (f"- {channel_name} (ID: {channel_id}) "
                             f"| Context: {config.context_id} "
                             f"| Min Delay: {config.min_delay} - {config.min_delay2} "
                             f"| Max Delay: {config.max_delay} - {config.max_delay2}\n")
            return response
        else:
            return "No channels are currently being watched."