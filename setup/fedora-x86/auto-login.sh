#!/bin/bash

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2018 Neil Munday (neil@mundayweb.com)
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

header "Enabling auto-login"

if [ ! -z $DESKTOP_SESSION ]; then
	if [ "$DESKTOP_SESSION" == "LXDE" ]; then
		echo "Desktop is LXDE"
		if [ -e /etc/lxdm/lxdm.conf ]; then
			echo "Enabling auto login for $USER"
			run sudo sed -r -i "s/#[ ]*autologin=[A-Za-z0-9]+/autologin=$USER/" /etc/lxdm/lxdm.conf
		else
			echo "Error: /etc/lxdm/lxdm.conf does not exist!"
		fi
		run mkdir -p ~/.config/lxsession/LXDE
		autostartFile="$HOME/.config/lxsession/LXDE/autostart"
		echo -n "Setting up autostart config for PES... "
		if [ ! -e "$autostartFile" ]; then
			cat > $autostartFile << EOF
@/opt/pes/bin/pes -l ~/pes/log/pes.log
EOF
			echo "Done!"
		else
			if ! grep -q '/opt/pes/bin/pes' $autostartFile; then
				echo "@rm $HOME/pes/log/pes.log" >> $autostartFile
				echo "@/opt/pes/bin/pes -l $HOME/pes/log/pes.log" >> $autostartFile
				echo "Done!"
			else
				echo "No need!"
			fi
		fi
	fi
else
	echo "No action taken!"
fi
