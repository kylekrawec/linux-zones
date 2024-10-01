#!/bin/bash

# Create virtual environment and install Python dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Compile App
pip install pyinstaller
pyinstaller --name=linuxzones --windowed --add-data "./resources/app.gresource:resources" --add-data "./settings:settings" linuxzones
