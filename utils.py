# utils.py

DEBUG = False

def set_debug_mode(mode):
    global DEBUG
    DEBUG = mode

def debug(message):
    if DEBUG:
        print(message)

def clamp(value, min_value, max_value):
    """Ensure that 'value' is between 'min_value' and 'max_value'."""
    return max(min_value, min(value, max_value))
