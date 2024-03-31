import os
import json
from box import Box


class Config(object):
    def __init__(self, filename, *path):
        relative_path = os.path.join('settings', filename) if path == () else os.path.join(*path, filename)
        self.filepath = os.path.abspath(relative_path)

    def load(self):
        with open(self.filepath, 'r') as file:
            content = json.load(file)
        return Box(content)
