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

import argparse
import logging
import os
import shutil
import sqlite3
import sys
from pes import *
from pes.data import Console
from pes.gui import *
from pes.util import *

def processColour(colour):
	if len(colour) != 3:
		logging.error("processColour: colour array does not contain 3 elements!")
		return None
	rtn = []
	for c in colour:
		try:
			rtn.append(int(c))
		except ValueError, e:
			logging.error("processColour: %s is not an integer!" % c)
			return None
	return rtn

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Launch the Pi Entertainment System (PES)', add_help=True)
	parser.add_argument('-w', '--window', help='Run PES in a window', dest='window', action='store_true')
	parser.add_argument('-v', '--verbose', help='Turn on debug messages', dest='verbose', action='store_true')
	parser.add_argument('-l', '--log', help='File to log messages to', type=str, dest='logfile')
	args = parser.parse_args()
	
	logLevel = logging.INFO
	if args.verbose:
		logLevel = logging.DEBUG

	if args.logfile:
		logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=logLevel, filename=args.logfile)
	else:
		logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=logLevel)
		
	dimensions = (0, 0)
	if args.window:
		dimensions = (900, 600)
	
	logging.debug("PES %s, date: %s, author: %s" % (VERSION_NUMBER, VERSION_DATE, VERSION_AUTHOR))
	
	try:
		logging.debug("PES base dir: %s" % baseDir)
		checkDir(baseDir)
		logging.debug("PES config dir: %s" % confDir)
		checkDir(confDir)
		logging.debug("PES user dir: %s" % userDir)
		
		mkdir(userDir)
		mkdir(userConfDir)
		initConfig()
		
		checkFile(userPesConfigFile)
		checkFile(userGamesCatalogueFile)
		checkFile(userConsolesConfigFile)
		checkFile(userGameControllerFile)
		
		logging.info("loading settings...")
		checkFile(userPesConfigFile)
		configParser = ConfigParser.ConfigParser()
		configParser.read(userPesConfigFile)
		
		if not configParser.has_section("colours"):
			pesExit("%s has no \"colours\" section!" % userPesConfigFile)
		
		romsDir = None
		coverartDir = None
		fontFile = None
		backgroundColour = None
		menuBackgroundColour = None
		headerBackgroundColour = None
		lineColour = None
		textColour = None
		
		userHome = os.path.expanduser('~')
		
		try:
			# pes settings
			fontFile = configParser.get('settings', 'fontFile').replace('%%BASE%%', baseDir)
			romsDir = configParser.get('settings', 'romsDir').replace('%%HOME%%', userHome)
			coverartDir = configParser.get('settings', 'coverartDir').replace('%%HOME%%', userHome)
			# colour settings
			backgroundColour = processColour(configParser.get("colours", "background").split(','))
			if backgroundColour == None:
				pesExit("invalid background colour in %s" % userPesConfigFile)
			menuBackgroundColour = processColour(configParser.get("colours", "menuBackground").split(','))
			headerBackgroundColour = processColour(configParser.get("colours", "headerBackground").split(','))
			lineColour = processColour(configParser.get("colours", "line").split(','))
			menuTextColour = processColour(configParser.get("colours", "menuText").split(','))
			menuSelectedTextColour = processColour(configParser.get("colours", "menuSelectedText").split(','))
			textColour = processColour(configParser.get("colours", "text").split(','))
		except ConfigParser.NoOptionError, e:
			pesExit("Error parsing config file %s: %s" % (userPesConfigFile, e.message), True)
			
		mkdir(romsDir)
		mkdir(coverartDir)
		
		logging.info("loading GUI...")
		app = PESApp(dimensions, fontFile, romsDir, coverartDir, backgroundColour, menuBackgroundColour, headerBackgroundColour, lineColour, textColour, menuTextColour, menuSelectedTextColour)
		app.run()
	except Exception, e:
		logging.exception(e)
		sys.exit(1)
