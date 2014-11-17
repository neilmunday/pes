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

echo ""
echo "Before proceeding please be aware that updating PES here will"
echo "will *ONLY* update the PES GUI and its supporting files."
echo ""
echo "The OS and emulators will not be updated"
echo ""
echo "To use the latest PES image, please see http://pes.mundayweb.com"
echo ""
echo "Notes:"
echo -e "\t-any changes you have made to PES files will be overwritten"
echo -e "\t-your ROMs, save game files and cover art will be preserved"
echo -e "\t-you may have to delete $HOME/.pes/pes.db if the update has changed the database structure"
echo -e "\t-always back-up your files if you are unsure"
echo ""

read -p "Are you sure you want to update to the latest version? [y/n]" response
if [ "$response" == "y" ]; then
	echo "Proceeding with update..."
	cd ../
	git fetch --all
	git reset --hard origin/master
	echo "Done!"
else
	echo "Update aborted"
	exit 1
fi

