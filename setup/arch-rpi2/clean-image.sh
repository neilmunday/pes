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
coverartDir=$baseDir/coverart
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

header "Clean Image"

echo "This script will prepare this SD card for imaging and for release into the public domain"
echo ""

echo "WARNING: Answering yes to the following question will perform the following operations:"
echo -e "\t-Delete all ROMs from $romDir including any game saves"
echo -e "\t-Delete all cover art from $coverartDir"
echo -e "\t-Delete any BIOSes installed in $baseDir/emulators/BIOS"
echo -e "\t-Delete PES user preferences and cover art cache from $userDir/.pes"
echo -e "\t-Delete PES and PESPad logs"
echo -e "\t-Delete pi user RetroArch config"
echo -e "\t-Delete all cached packages from pacman"
echo -e "\t-Delete command history for root and pi users"
echo -e "\t-Delete pip cache"
echo -e "\t-Delete SSH known_hosts files for root and pi users"
echo -e "\t-Delete $baseDir/build contents"
echo -e "\t-Remove unnecessary packages, including compilation utilities"
echo ""

read -p "Are you sure you want to proceed? [y/n]" response
if [ "$response" == "y" ]; then
	echo "Beginning purge..."
	echo ""
	#echo "Stopping PESPad..."
	#run sudo systemctl stop pespad.service
	echo ""
	echo "Removing cached packages..."
	run sudo pacman -Scc
	echo ""
	echo "Deleting ROMs from $romDir ..."
	run rm -rfv $romDir/*
	echo ""
	echo "Deleting covert art from $coverartDir ..."
	run rm -rfv $coverartDir/*
	echo ""
	echo "Deleting BIOSes..."
	run rm -fv $baseDir/emulators/BIOS/*.bin
	echo ""
	echo "Deleting PES build dir contents..."
	run sudo rm -rfv $baseDir/build/*
	echo ""
	echo "Deleting PES user configs and image cache for pi user..."
	run rm -rfv $userDir/.pes
	echo ""
	echo "Deleting RetroArch config for pi user..."
	run rm -rfv $userDir/.config/retroarch
	echo ""
	echo "Deleting PES and PESPad logs..."
	run sudo rm -fv /var/log/pespad.log $baseDir/log/*
	echo ""
	echo "Removing unnecessary packages..."
	run sudo $DIR/remove-packages.sh
	echo ""
	echo "Deleting root bash history..."
	run sudo rm -fv /root/.bash_history
	echo ""
	echo "Deleting pip cache..."
	run sudo rm -rfv /root/.cache/pip
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

