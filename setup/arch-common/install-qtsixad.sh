#!/bin/bash

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2014-2021 Neil Munday (neil@mundayweb.com)
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

cd $buildDir

installDir=/opt/qtsixa
run sudo mkdir -p $installDir/sbin

rmSourceDir "qtsixa"

# need bluez-utils-compat from the AUR as this provides (now deprecated tools) from Bluez
# that qtsixad relies upon

if ! pacman -Q bluez-utils-compat > /dev/null 2>&1; then
	header "Installing bluez-utils-compat from the AUR"
	run yaourt -A --m-arg --skipchecksums --m-arg --skippgpcheck -S bluez-utils-compat
fi

header "Downloading qtsixad"

run git clone git://github.com/falkTX/qtsixa

checkDir "qtsixa"
cd qtsixa
checkDir "sixad"
cd sixad

# apply patches
patchDir="$rootDir/src/qtsixa-patches"
checkDir $patchDir
for p in $patchDir/*.patch; do
	echo "Applying patch ${p}..."
	patch < $p
done

run make -j

run sudo cp -v bins/* $installDir/sbin/
run sudo cp -v sixad $installDir/sbin/
run sudo chmod 0755 $installDir/sbin/sixad

sudo sed -r -i "s#/usr/sbin/sixad-bin#/$installDir/sbin/sixad-bin#" /opt/qtsixa/sbin/sixad

header "Enabling sixad at boot time..."

run sudo bash -c "cat > /etc/systemd/system/sixad.service" << EOF
[Unit]
Description=sixad daemon
After=sys-subsystem-bluetooth-devices-hci0.device
Requires=sys-subsystem-bluetooth-devices-hci0.device

[Service]
ExecStart=/usr/bin/nohup $installDir/sbin/sixad --start
ExecStop=$installDir/sbin/sixad --stop

[Install]
WantedBy=multi-user.target
EOF

run sudo systemctl stop bluetooth.service
run sudo systemctl disable bluetooth.service
run sudo systemctl enable sixad.service
run sudo systemctl start sixad.service

header "Enabling bluetooth adapter at boot time..."

run sudo bash -c "cat > /opt/sbin/start-bt.sh" << 'EOF'
#!/bin/bash
/usr/bin/btmgmt power on
/usr/bin/btmgmt connectable on
EOF

run sudo chmod 700 /opt/sbin/start-bt.sh

run sudo bash -c "cat > /etc/udev/rules.d/10-local.rules" << 'EOF'
ACTION=="add", KERNEL=="hci[0-9]", RUN+="/opt/sbin/start-bt.sh"
EOF

header "Installing pairing utility..."
run cd ../utils
run gcc -lusb -o sixpair sixpair.c
run sudo cp sixpair $installDir/sbin/sixpair

header "Enabling auto pairing..."

run sudo bash -c "cat > /etc/udev/rules.d/97-sixpair.rules" << EOF
SUBSYSTEM=="usb", ATTRS{idVendor}=="054c", ENV{idProduct}="0268", RUN+="$installDir/sbin/sixpair"
SUBSYSTEM=="input", ATTR{name}=="PLAYSTATION(R)3 Controller*", RUN+="$installDir/sbin/sixpair"
EOF

header "QtSixAd installation complete!"

exit 0
