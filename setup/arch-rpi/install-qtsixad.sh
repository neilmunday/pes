#!/bin/bash

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2015 Neil Munday (neil@mundayweb.com)
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

setupDir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ ! -e $setupDir/functions.sh ]; then
	echo "Error! $setupDir/functions does not exist!"
	exit 1
fi

source $setupDir/functions.sh

qtsixaTar=$baseDir/src/QtSixA-1.5.1-src.tar.gz
qtsixaDir=$buildDir/QtSixA-1.5.1
sixadPatchDir=$baseDir/src/sixad-patches

checkDir $sixadPatchDir

header "Downloading sixad..."

run cd $baseDir/src

if [ ! -e $qtsixaTar ]; then
	echo "Downloading QTSixA..."
	run wget http://sourceforge.net/projects/qtsixa/files/QtSixA%201.5.1/QtSixA-1.5.1-src.tar.gz
fi

checkFile $qtsixaTar

if [ -e $qtsixaDir ]; then
	echo "Removing previously used source..."
	run rm -rvf $qtsixaDir
fi
run cd $buildDir
run tar xvfz $qtsixaTar
run cd $qtsixaDir/sixad

header "Patching sixad..."

for p in $sixadPatchDir/*.patch; do
	echo "Applying patch ${p}..."
	patch < $p
done

run make
run sudo cp -v bins/* /usr/sbin/
run sudo cp -v sixad /usr/sbin/
run sudo chmod 0755 /usr/sbin/sixad

header "Enabling sixad at boot time..."

run sudo bash -c "cat > /etc/systemd/system/sixad.service" << 'EOF'
[Unit]
Description=sixad daemon
After=sys-subsystem-bluetooth-devices-hci0.device

[Service]
ExecStartPre=/usr/bin/hciconfig hci0 pscan
ExecStart=/usr/bin/nohup /usr/sbin/sixad --start

[Install]
WantedBy=multi-user.target
EOF

run sudo systemctl enable sixad.service

header "Installing pairing utility..."
run cd $qtsixaDir/utils
run gcc -lusb -o sixpair sixpair.c
run sudo cp sixpair /usr/sbin/sixpair

header "Enabling auto pairing..."

run sudo bash -c "cat > /etc/udev/rules.d/97-sixpair.rules" << 'EOF'
SUBSYSTEM=="usb", ATTRS{idVendor}=="054c", ENV{idProduct}="0268", RUN+="/usr/sbin/sixpair"
EOF

header "QtSixAd installation complete!"

exit 0
