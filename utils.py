# utils.py

DEBUG = False

def set_debug_mode(mode):
    global DEBUG
    DEBUG = mode

def debug(message):
    if DEBUG:
        print(message)
