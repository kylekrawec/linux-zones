#!/bin/bash
sudo apt install libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-4.0 python3-pip python3-venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# install linux-zones startup file
mkdir -p ~/.config/autostart
cp "$HOME"/linux-zones/linux-zones.desktop ~/.config/autostart/

# make linux-zones executable
chmod +x "$HOME"/linux-zones/linux-zones
