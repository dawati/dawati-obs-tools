import os
import sys

config_file = os.path.join(os.environ['HOME'], '.dawati-obsrc')
config_keys = ('name', 'email')
config = {}

def load():
    try:
        execfile(config_file, config)
    except:
        print("Could not load %s" % config_file)
        sys.exit(1)

def get(key):
    return config[key]
