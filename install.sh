#!/bin/bash
sudo apt install libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-4.0
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
