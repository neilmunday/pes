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

from pes import *
#from Levenshtein import *
import csv
import fcntl
import socket
import struct

def checkDir(dir):
	if not os.path.exists(dir):
		pesExit("Error: %s does not exist!" % dir, True)
	if not os.path.isdir(dir):
		pesExit("Error: %s is not a directory!" % dir, True)

def checkFile(file):
	if not os.path.exists(file):
		pesExit("Error: %s does not exist!" % file, True)
	if not os.path.isfile(file):
		pesExit("Error: %s is not a file!" % file, True)
		
def getDefaultInterface(): 
	f = open('/proc/net/route') 
	for i in csv.DictReader(f, delimiter="\t"): 
		if long(i['Destination'], 16) == 0: 
			return i['Iface'] 
	f.close()
	return None

def getIpAddress(ifname): 
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
	return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', ifname[:15]))[20:24])

def initConfig():
	logging.debug("initialising config...")
	checkDir(userConfDir)
	for root, dirs, files in os.walk(confDir):		
		userRoot = root.replace(baseDir, userDir)
		for d in dirs:
			dest = userRoot + os.sep + d
			if not os.path.exists(dest):
				mkdir(dest)
				
		for f in files:
			dest = userRoot + os.sep + f
			source = root + os.sep + f
			if not os.path.exists(dest):
				logging.debug("copying %s to %s" % (source, dest))
				shutil.copy(source, dest)

def mkdir(path):
	if not os.path.exists(path):
		logging.debug("mkdir: directory: %s" % path)
		os.mkdir(path)
		return True
	elif not os.path.isdir(path):
		pesExit("Error: %s is not a directory!" % path, True)
	elif not os.access(path, os.W_OK):
		pesExit("Error: %s is not writeable!" % path, True)
	# did not have to make directory so return false
	logging.debug("mkdir: %s already exists" % path)
	return False
		
def pesExit(msg = None, error = False):
	if error:
		if msg:
			logging.error(msg)
		else:
			logging.error("Unrecoverable error occurred, exiting!")
		sys.exit(1)
	if msg:
		logging.info(msg)
	else:
		logging.info("Exiting...")
	sys.exit(0)
	
def scaleImage(ix, iy, bx, by):
	"""
	Original author: Frank Raiser (crashchaos@gmx.net)
	URL: http://www.pygame.org/pcr/transform_scale
	Modified by Neil Munday
	"""
	if ix > iy:
		# fit to width
		scale_factor = bx/float(ix)
		sy = scale_factor * iy
		if sy > by:
			scale_factor = by/float(iy)
			sx = scale_factor * ix
			sy = by
		else:
			sx = bx
	else:
		# fit to height
		scale_factor = by/float(iy)
		sx = scale_factor * ix
		if sx > bx:
			scale_factor = bx/float(ix)
			sx = bx
			sy = scale_factor * iy
		else:
			sy = by
	return (int(sx),int(sy))
