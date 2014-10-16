#!/bin/bash

source /home/pi/pes/setup/arch/functions.sh

cd $buildDir

installDir="/opt/pespad"

header "Downloading PESPad"

git clone git://github.com/neilmunday/pespad

checkDir pespad

run cd pespad

checkFile systemd/pespad.service

if [ ! -e $pespad ]; then
	header "Making $installDir"
	run sudo mkdir -v /opt/pespad
fi

header "Copying files"

run cp -rv pespad.py web $installDir

header "Adding service"

run cp -v systemd/pespad.service /etc/systemd/system/pespad.service

run sudo systemctl enable pespad.service

header "Starting service"

run sudo systemctl start pespad.service

