#!/usr/bin/env python2

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

#
#	This script will automatically create the /data partition for the
#	PES ArchLinux Raspberry Pi images.
#	It is intended to be called at boot time.
#

import os
import sys
import argparse
import logging
from reparted import *
from pwd import getpwnam
import subprocess
from fstab import *

def die(msg):
	logging.error(msg)
	exit(1)

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description='Automatically create /data partition for PES', add_help=True)
	parser.add_argument('-v', '--verbose', help='Turn on debug messages', dest='verbose', action='store_true')
	parser.add_argument('-d', '--device', help='Device to operate on', type=str, dest='device', required=True)
	args = parser.parse_args()

	logLevel = logging.INFO
	if args.verbose:
		logLevel = logging.DEBUG
		
	logging.basicConfig(format='%(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=logLevel)
	
	logging.debug("checking for existence of %s" % args.device)
	if not os.path.exists(args.device):
		die("%s does not exist" % args.device)
	
	fstabFile = '/etc/fstab'
	fsType = 'ext4'
	label = "data"
	mountPoint = os.sep + label
	romsDir = mountPoint + os.sep + "roms"
	coverartDir = mountPoint + os.sep + "coverart"
	user = 'pi'
	
	# look for existing "roms" partition - uses disk label to see if we have already made it or not
	logging.debug("looking for existing \"%s\" partition" % label)
	labelDir = '/dev/disk/by-label'
	if not os.path.exists(labelDir):
		die("%s does not exist" % labelDir)
	
	if not os.path.isdir(labelDir):
		die("%s is not a directory" % labelDir)
		exit(1)
	
	for l in os.listdir(labelDir):
		logging.debug("found disk with label: %s" % l)
		if l == label:
			logging.info("found %s partition - no need to continue." % label)
			sys.exit(0)
	
	logging.debug("could not find disk with \"%s\" label... continuing" % label)
	
	dataDevice = None
	
	try:
		device = Device(args.device)
		disk = Disk(device)	
		freeSpace = disk.usable_free_space
		logging.debug("will use %s space to create %s partition" % (mountPoint, freeSpace))
		partition = Partition(disk, freeSpace)
		disk.add_partition(partition)
		dataDevice = "%sp%s" % (args.device, partition.num)
		disk.commit()
		logging.debug("new partition at: %s" % dataDevice)
	except Exception, e:
		logging.exception(e)
		sys.exit(1)
	
	logging.info("partition created")
	command = "mkfs -L %s -t %s %s" % (label, fsType, dataDevice)
	logging.debug("now formatting using command: %s" % command)
	process = subprocess.Popen(command.split(' '), stdout=subprocess.PIPE, bufsize=1)
	with process.stdout:
		for line in iter(process.stdout.readline, b''):
			logging.debug(line)
	rtn = process.wait()
	
	if rtn != 0:
		die("%s returned non zero!" % command)
		
	logging.info("partition formatted")
	
	if not os.path.exists(mountPoint):
		logging.debug("creating mount point: %s" % mountPoint)
		os.mkdir(mountPoint)
	elif not os.path.isdir(mountPoint):
		die("%s is not a valid mount point" % mountPoint)
	
	fstab = Fstab()
	fstab.read(fstabFile)
	foundDataMount = False
	for l in fstab.lines:
		if l.directory == mountPoint:
			foundDataMount = True
			
	if not foundDataMount:
		logging.info("adding entry to %s" % fstabFile)
		fstab.lines.append(Line("%s  %s           %s    defaults        0       0" % (dataDevice, mountPoint, fsType)))
		fstab.write(fstabFile)
	
	logging.debug("attempting to mount")
	rtn = subprocess.call(["mount", mountPoint])
	if rtn != 0:
		die("unable to mount %s" % mountPoint)
	logging.info("mounted %s" % mountPoint)
	logging.info("setting owner to the %s user" % user)
	userAttrs = getpwnam(user)
	os.chown(mountPoint, userAttrs.pw_uid, userAttrs.pw_gid)
	logging.debug("making %s" % romsDir)
	os.mkdir(romsDir)
	os.chown(romsDir, userAttrs.pw_uid, userAttrs.pw_gid)
	logging.debug("making %s" % coverartDir)
	os.mkdir(coverartDir)
	os.chown(coverartDir, userAttrs.pw_uid, userAttrs.pw_gid)
	logging.info("operations completed successfully")
	sys.exit(0)
