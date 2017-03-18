#!/bin/bash

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2017 Neil Munday (neil@mundayweb.com)
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

functions=`realpath $( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/../common/functions.sh`
source $functions || exit 1

pesDataDir="/data/pes"
setupDir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

header "Clean Image"

echo "This script will prepare this SD card for imaging and for release into the public domain"
echo ""

echo "WARNING: Answering yes to the following question will perform the following operations:"
echo -e "\t-Delete all ROMs, coverart, badges, user configs, logs, and PES database from $pesDataDir"
echo -e "\t-Delete all Kodi media including config files"
echo -e "\t-Delete all cached packages from pacman"
echo -e "\t-Delete command history for root and pi users"
echo -e "\t-Delete pip cache"
echo -e "\t-Delete SSH known_hosts files for root and pi users"
echo -e "\t-Delete $buildDir contents"
echo -e "\t-Remove unnecessary packages, including compilation utilities"
echo ""

read -p "Are you sure you want to proceed? [y/n]" response
if [ "$response" == "y" ]; then
	echo "Beginning purge..."
	echo ""
	echo "Removing cached packages..."
	run sudo pacman -Scc
	echo ""
	echo "Deleting PES data from $pesDataDir"
	run rm -rfv $pesDataDir/*
	echo ""
	echo "Deleting PES build dir contents..."
	run sudo rm -rfv $buildDir
	echo ""
	echo "Deleting RetroArch config for pi user..."
	run rm -rfv $userDir/.config/retroarch
	echo "Deleting PPSSPP config for pi user..."
	run rm -rfv $userDir/.config/ppsspp
	echo "Deleting Kodi config files for pi user..."
	run rm -rfv $userDir/.kodi
	echo ""
	echo "Removing unnecessary packages..."
	run $setupDir/remove-packages.sh
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
	echo "Deleting your bash history..."
	run rm -fv ~/.bash_history
	echo ""
	echo "Deleting your SSH known hosts..."
	run rm -fv ~/.ssh/known_hosts
	echo ""
	echo "Done"
else
	echo "No changes made"
fi
