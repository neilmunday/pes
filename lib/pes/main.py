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
import ConfigParser
import logging
import os
import shutil
import sqlite3
import sys
from pes import *
from pes.data import Console
from pes.app import PESApp
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
		checkFile(gamepadImageFile)
		checkFile(networkImageFile)
		checkFile(remoteImageFile)
		
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
		cecEnabled = False
		screenSaverTimeout = 0
		
		userHome = os.path.expanduser('~')
		
		retroAchievementsUserName = None
		retroAchievementsPassword = None
		retroAchievementsApiKey = None
		
		try:
			# pes settings
			cecEnabled = configParser.getboolean('settings', 'hdmi-cec')
			fontFile = configParser.get('settings', 'fontFile').replace('%%BASE%%', baseDir)
			romsDir = configParser.get('settings', 'romsDir').replace('%%HOME%%', userHome).replace('%%USERDIR%%', userDir)
			coverartDir = configParser.get('settings', 'coverartDir').replace('%%HOME%%', userHome).replace('%%USERDIR%%', userDir)
			biosDir = configParser.get('settings', 'biosDir').replace('%%HOME%%', userHome).replace('%%USERDIR%%', userDir)
			screenSaverTimeout = configParser.getint('settings', 'screenSaverTimeout')
			mkdir(romsDir)
			mkdir(coverartDir)
			mkdir(biosDir)
			checkFile(fontFile)
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
			# coverart settings
			coverartSize = configParser.getfloat('settings', 'coverartSize')
			coverartCacheLen = configParser.getint('settings', 'coverartCacheLen')
			# command settings
			shutdownCommand = configParser.get("commands", "shutdown")
			rebootCommand = configParser.get("commands", "reboot")
			listTimezonesCommand = configParser.get("commands", "listTimezones")
			setTimezoneCommand = configParser.get("commands", "setTimezone")
			getTimezoneCommand = configParser.get("commands", "getTimezone")
			# RetroAchievements settings
			if configParser.has_section("RetroAchievements"):
				retroAchievementsUserName = configParser.get("RetroAchievements", "username")
				retroAchievementsPassword = configParser.get("RetroAchievements", "password")
				retroAchievementsApiKey = configParser.get("RetroAchievements", "apiKey")
		except ConfigParser.NoOptionError, e:
			pesExit("Error parsing config file %s: %s" % (userPesConfigFile, e.message), True)
		except ValueError, e:
			pesExit("Error parsing config file %s: %s" % (userPesConfigFile, e.message), True)
			
		mkdir(romsDir)
		mkdir(coverartDir)
		
		if cecEnabled:
			cecEnabled = False
			try:
				import cec
				logging.info("CEC module enabled")
				cecEnabled = True
			except ImportError, e:
				logging.info("CEC module not found, disabling CEC functions")
		else:
			logging.debug("CEC disabled in pes.ini")
		
		app = PESApp(dimensions, fontFile, romsDir, coverartDir, coverartSize, coverartCacheLen, backgroundColour, menuBackgroundColour, headerBackgroundColour, lineColour, textColour, menuTextColour, menuSelectedTextColour, shutdownCommand, rebootCommand, listTimezonesCommand, getTimezoneCommand, setTimezoneCommand)
		
		if cecEnabled:
			# set-up CEC
			try:
				logging.debug("creating CEC config...")
				cecconfig = cec.libcec_configuration()
				cecconfig.strDeviceName   = "PES"
				cecconfig.bActivateSource = 0
				cecconfig.deviceTypes.Add(cec.CEC_DEVICE_TYPE_RECORDING_DEVICE)
				cecconfig.clientVersion = cec.LIBCEC_VERSION_CURRENT
				logging.debug("adding CEC callback...")
				cecconfig.SetKeyPressCallback(app.processCecEvent)
				lib = cec.ICECAdapter.Create(cecconfig)
				logging.debug("looking for CEC adapters...")
				adapters = lib.DetectAdapters()
				adapterCount = len(adapters)
				if adapterCount == 0:
					logging.warning("could not find any CEC adapters!")
				else:
					logging.debug("found %d CEC adapters, attempting to open first adapter..." % adapterCount)
					if lib.Open(adapters[0].strComName):
						logging.info("CEC adapter opened")
					else:
						logging.error("unable to open CEC adapter!")
			except Exception, e:
				cecEnabled = False
				logging.error("CEC module initilisation failed, disabling CEC functions")
				logging.error(e)
		
		app.setCecEnabled(cecEnabled)
		app.setScreenSaverTimeout(screenSaverTimeout)
		
		if retroAchievementsApiKey != None and retroAchievementsUserName != None and retroAchievementsPassword != None and len(retroAchievementsUserName) > 0 and len(retroAchievementsPassword) > 0 and len(retroAchievementsApiKey) > 0:
			app.setRetroAchievements(retroAchievementsUserName, retroAchievementsPassword, retroAchievementsApiKey)
		
		logging.info("loading GUI...")
		app.run()
	except Exception, e:
		logging.exception(e)
		sys.exit(1)
