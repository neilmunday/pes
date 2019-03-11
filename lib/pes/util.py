#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2019 Neil Munday (neil@mundayweb.com)
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
from Levenshtein import *
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

def getIPAddress(ifname): 
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
	return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', ifname[:15]))[20:24])

# workaround for http://bugs.python.org/issue22273
# thanks to https://github.com/GreatFruitOmsk/py-sdl2/commit/e9b13cb5a13b0f5265626d02b0941771e0d1d564
def getJoystickGUIDString(guid):
	s = ''
	for g in guid.data:
		s += "{:x}".format(g >> 4)
		s += "{:x}".format(g & 0x0F)
	return s

def getJoystickDeviceInfoFromGUID(guid):
	vendorId = guid[8:12]
	productId = guid[16:20]
	# swap from big endian to little endian and covert to an int
	vendorId = int(vendorId.decode('hex')[::-1].encode('hex'), 16)
	productId = int(productId.decode('hex')[::-1].encode('hex'), 16)
	return (vendorId, productId)

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
		logging.debug("creating directory: %s" % path)
		os.mkdir(path)
		return True
	elif not os.path.isdir(path):
		pesExit("Error: %s is not a directory!" % path, True)
	elif not os.access(path, os.W_OK):
		pesExit("Error: %s is not writeable!" % path, True)
	# did not have to make directory so return false
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
	
def scaleImage((ix, iy), (bx,by)):
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

#
#	StringMatcher class sourced from https://github.com/ztane/python-Levenshtein/blob/master/StringMatcher.py
#	Author: Antti Haapala <antti@haapala.name>
#
class StringMatcher:
	"""A SequenceMatcher-like class built on the top of Levenshtein"""
	def _reset_cache(self):
		self._ratio = self._distance = None
		self._opcodes = self._editops = self._matching_blocks = None
	def __init__(self, seq1='', seq2=''):
		self._str1, self._str2 = seq1, seq2
		self._reset_cache()
	def set_seqs(self, seq1, seq2):
		self._str1, self._str2 = seq1, seq2
		self._reset_cache()
	def set_seq1(self, seq1):
		self._str1 = seq1
		self._reset_cache()
	def set_seq2(self, seq2):
		self._str2 = seq2
		self._reset_cache()
	def get_opcodes(self):
		if not self._opcodes:
			if self._editops:
				self._opcodes = opcodes(self._editops, self._str1, self._str2)
			else:
				self._opcodes = opcodes(self._str1, self._str2)
		return self._opcodes
	def get_editops(self):
		if not self._editops:
			if self._opcodes:
				self._editops = editops(self._opcodes, self._str1, self._str2)
			else:
				self._editops = editops(self._str1, self._str2)
		return self._editops
	def get_matching_blocks(self):
		if not self._matching_blocks:
			self._matching_blocks = matching_blocks(self.get_opcodes(), self._str1, self._str2)
		return self._matching_blocks
	def ratio(self):
		if not self._ratio:
			self._ratio = ratio(self._str1, self._str2)
		return self._ratio
	def quick_ratio(self):
		# This is usually quick enough :o)
		if not self._ratio:
			self._ratio = ratio(self._str1, self._str2)
		return self._ratio
	def real_quick_ratio(self):
		len1, len2 = len(self._str1), len(self._str2)
		return 2.0 * min(len1, len2) / (len1 + len2)
	def distance(self):
		if not self._distance:
			self._distance = distance(self._str1, self._str2)
		return self._distance
	