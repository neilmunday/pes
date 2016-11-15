#!/bin/bash

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2016 Neil Munday (neil@mundayweb.com)
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

function updateBootCmdline {
	if [ -z $2 ]; then
		if grep -v -q "$1" /boot/cmdline.txt; then
			run sudo sed -i "s/\$/ $1/" /boot/cmdline.txt
		fi
	else
		if grep -v -q "$1" /boot/cmdline.txt; then
			run sudo sed -i "s/\$/ $1=$2/" /boot/cmdline.txt
		else
			run sudo sed -i "s/$1=[[:alnum:]]+/$1=$2/" /boot/cmdline.txt
		fi
	fi
}

cd $buildDir

prj="Plymouth-lite"

header "Compiling $prj"

rmSourceDir "$prj"

run git clone https://github.com/T4d3o/$prj

checkDir "$prj"

cd $prj

run ./configure
run make
run sudo make install

header "Setting up Arch Linux splash image"

# create the splash logo
splashImg="/usr/share/plymouth/pes-splash.png"
tmpSplashImg=$buildDir/pes-splash.png

if [ -e $tmpSplashImg ]; then
	run rm -vf $tmpSplashImg
fi

run $rootDir/setup/arch-common/make-splash-png.py -o $tmpSplashImg

run sudo cp $tmpSplashImg $splashImg

checkFile /usr/lib/initcpio/init

if grep -q ply-image /usr/lib/initcpio/init; then
	echo "No need to modify /usr/lib/initcpio/init"
else
	if [ ! -e /usr/lib/initcpio/init.orig ]; then
		echo "Backing up /usr/lib/initcpio/init"
		run sudo cp -v /usr/lib/initcpio/init /usr/lib/initcpio/init.orig
	fi
	echo "Patching /usr/lib/initcpio/init"
	run sudo sed -i "/run_hookfunctions 'run_hook' 'hook' \$HOOKS/i ply-image $splashImg &> /dev/null" /usr/lib/initcpio/init
fi

echo "Patching /etc/mkinitcpio.conf"
run sudo sed -i 's/BINARIES=".*"/BINARIES="ply-image"/' /etc/mkinitcpio.conf
run sudo sed -i "s#FILES=\".*\"#FILES=\"$splashImg\"#" /etc/mkinitcpio.conf

echo "Creating initrd..."
run sudo mkinitcpio -g /boot/initrd -v

echo "Patching /boot/config.txt"
if egrep -q "^initramfs" /boot/config.txt; then
	run sudo sed -i 's/^initramfs.*$/initramfs initrd 0x00f00000/' /boot/config.txt 
else
	echo 'initramfs initrd 0x00f00000' | sudo tee /boot/config.txt --append /boot/config.txt
fi

echo "Patching /boot/cmdline.txt"

updateBootCmdline "initrd" "0x00f00000"
#updateBootCmdline "quiet"
updateBootCmdline "logo.nologo"
updateBootCmdline "vt.global_cursor_default" "0"
updateBootCmdline "loglevel" "3"

run sudo sed -i "/console=tty[0-9]+/console=tty3/" /boot/cmdline.txt

echo "Creating Plymouth-Lite systemd start-up file"
run sudo bash -c "cat > /etc/systemd/system/plymouth-lite-start.service" << EOF
[Unit]
Description=Show Plymouth-lite Start Screen
DefaultDependencies=no
After=systemd-vconsole-setup.service
Before=sysinit.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/echo 0 > /sys/class/graphics/fbcon/cursor_blink ; /usr/bin/echo 0 > /sys/devices/virtual/graphics/fbcon/cursor_blink ; /usr/bin/chvt 7 ; /usr/bin/ply-image $splashImg
EOF

run sudo ln -sf /etc/systemd/system/plymouth-lite-start.service /usr/lib/systemd/system/sysinit.target.wants/plymouth-lite-start.service

echo "Setting up PES profile script"
run sudo bash -c "cat > /etc/profile.d/pes.sh" << EOF
tput cnorm
EOF

echo "Done!"
