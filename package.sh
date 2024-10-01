#!/bin/bash

linuxzones=linuxzones

# Duplicate for safety
cd /
cp -r ~/linux-zones ~/$linuxzones
cd ~/$linuxzones
echo "Duplicated source files"

# Compile LinuxZones into application
bash build.sh
echo "Compiled application"

# Keep required files
mkdir ~/$linuxzones
mv dist/linuxzones ~/$linuxzones
mv resources/linuxzones.svg ~/$linuxzones
mv LICENSE ~/$linuxzones
mv linuxzones.desktop ~/$linuxzones
mv README.md ~/$linuxzones
echo "Prepared Package"

