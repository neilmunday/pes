#!/bin/bash

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2014 Neil Munday (neil@mundayweb.com)
#
#    PES is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    PES is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with PES.  If not, see <http://www.gnu.org/licenses/>.
#

source /home/pi/pes/setup/arch-rpi2/functions.sh

romDir=$baseDir/roms

header "Clean Image"

echo "This script will prepare this SD card for imaging and for release into the public domain"
echo ""

echo "WARNING: Answering yes to the following question will perform the following operations:"
echo -e "\t-Delete all ROMs from $romDir including any game saves"
echo -e "\t-Delete any BIOSes installed in $baseDir/emulators/BIOS"
echo -e "\t-Delete PES user preferences and cover art cache from $userDir/.pes"
echo -e "\t-Delete PES and PESPad logs"
echo -e "\t-Delete pi user RetroArch config"
echo -e "\t-Delete all cached packages from pacman"
echo -e "\t-Delete command history for root and pi users"
echo -e "\t-Delete SSH known_hosts files for root and pi users"
echo -e "\t-Delete $baseDir/build contents"
echo ""

read -p "Are you sure you want to proceed? [y/n]" response
if [ "$response" == "y" ]; then
	echo "Beginning purge..."
	echo ""
	echo "Stopping PESPad..."
	run sudo systemctl stop pespad.service
	echo ""
	echo "Removing cached packages..."
	run sudo pacman -Scc
	echo ""
	echo "Deleting ROMs..."
	run rm -rfv $baseDir/roms/GameBoy/* $baseDir/roms/GameBoy\ Color/* $baseDir/roms/GameGear/* $baseDir/roms/MasterSystem/* $baseDir/roms/Mega\ CD $baseDir/roms/MegaDrive/* $baseDir/roms/N64/* $baseDir/roms/NES/* $baseDir/roms/PSX/* $baseDir/roms/SNES/*
	echo ""
	echo "Deleting BIOSes..."
	run rm -fv $baseDir/emulators/BIOS/*.bin
	echo ""
	echo "Deleting PES build dir contents..."
	run rm -rfv $baseDir/build/*
	echo ""
	echo "Deleting PES user configs and image cache for pi user..."
	run rm -rfv $userDir/.pes
	echo ""
	echo "Deleting RetroArch config for pi user..."
	run rm -rfv $userDir/.config/retroarch
	echo "Deleting PES and PESPad logs..."
	run sudo rm -fv /var/log/pespad.log $baseDir/log/*
	echo ""
	echo "Deleting root bash history..."
	run sudo rm -fv /root/.bash_history
	echo ""
	echo "Deleting root SSH known hosts..."
	run sudo rm -fv /root/.ssh/known_hosts
	echo ""
	echo "Deleting pi user bash history..."
	run rm -fv $userDir/.bash_history
	echo ""
	echo "Deleting pi user SSH known hosts..."
	run rm -fv $userDir/.ssh/known_hosts
	echo ""
	echo "Done"
else
	echo "No changes made"
fi

