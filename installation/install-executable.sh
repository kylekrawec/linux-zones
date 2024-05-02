#!/bin/bash

# install linux-zones startup file
mkdir -p ~/.config/autostart
cp "$HOME"/linux-zones/installation/linux-zones.desktop ~/.config/autostart/

# make linux-zones executable
chmod +x "$HOME"/linux-zones/installation/linux-zones
