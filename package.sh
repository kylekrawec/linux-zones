#!/bin/bash

build=build
pkg=linuxzones

# Duplicate for safety
cd /
cp -r ~/linux-zones ~/$build
cd ~/$build
echo "Duplicated source files"

# Compile LinuxZones into application
bash build.sh
echo "Compiled application"

# Export required files
mkdir ~/$pkg
mv dist/linuxzones ~/$pkg
mv resources/linuxzones.svg ~/$pkg
mv LICENSE ~/$pkg
mv linuxzones.desktop ~/$pkg
mv README.md ~/$pkg
echo "Prepared Package"

# Clean up
rm -rf ~/$build

