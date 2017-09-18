#!/usr/bin/env python3

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

import argparse
import atexit
import cProfile
import logging
import os
import pstats
import shutil
import signal
import io
import sys
from PyQt5.QtWidgets import QApplication
from pes import *
from pes.common import checkDir, checkFile, initConfig, mkdir
from pes.data import Settings
from pes.gui import PESWindow

def exitHandler():
	global profile, profileObj
	
	if profile and profileObj != None:
		profileObj.disable()
		# dump stats
		s = io.StringIO()
		ps = pstats.Stats(profileObj, stream=s).sort_stats('cumulative')
		ps.print_stats()
		logging.info("Profile Stats:")
		logging.info(s.getvalue())

def signalHandler(sig, frame):
	global window, profile, profileObj
	
	if sig == signal.SIGINT:
		logging.debug("signalHandler: SIGINT")
		window.close()
	elif sig == signal.SIGHUP:
		if profile:
			logging.info("disabling profiling")
			# profiling is on, so turn it off
			if profileObj != None:
				profileObj.disable()
				# dump stats
				s = StringIO.StringIO()
				ps = pstats.Stats(profileObj, stream=s).sort_stats('cumulative')
				ps.print_stats()
				logging.info("Profile Stats:")
				logging.info(s.getvalue())
			profile = False
		else:
			logging.info("enabling profiling")
			# profiling is not on, so turn it on
			if profileObj == None:
				profileObj = cProfile.Profile()
			profileObj.enable()
			profile = True
	

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Launch the Pi Entertainment System (PES)', add_help=True)
	parser.add_argument('-w', '--window', help='Run PES in a window', dest='window', action='store_true')
	parser.add_argument('-v', '--verbose', help='Turn on debug messages', dest='verbose', action='store_true')
	parser.add_argument('-l', '--log', help='File to log messages to', type=str, dest='logfile')
	parser.add_argument('-p', '--profile', help='Turn on profiling', dest='profile', action='store_true')
	args = parser.parse_args()
	
	profile = args.profile
	
	profileObj = None
	
	if profile:
		profileObj = cProfile.Profile()
		profileObj.enable()
	
	logLevel = logging.INFO
	if args.verbose:
		logLevel = logging.DEBUG

	if args.logfile:
		logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=logLevel, filename=args.logfile)
	else:
		logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=logLevel)
	
	logging.debug("PES %s, date: %s, author: %s" % (VERSION_NUMBER, VERSION_DATE, VERSION_AUTHOR))
	
	try:
		logging.debug("base dir: %s" % baseDir)
		checkDir(baseDir)
		logging.debug("config dir: %s" % confDir)
		checkDir(confDir)
		logging.debug("theme dir: %s" % themeDir)
		checkDir(themeDir)
		logging.debug("user dir: %s" % userDir)
		mkdir(userDir)
		mkdir(userConfDir)
		mkdir(userRetroArchConfDir)
		mkdir(userRetroArchJoysticksConfDir)
		mkdir(userViceConfDir)
		initConfig()
		
		checkFile(userPesConfigFile)
		checkFile(userGamesCatalogueFile)
		checkFile(userConsolesConfigFile)
		checkFile(userGameControllerFile)
		#checkFile(rasumExe)
		
		logging.info("loading settings...")
		checkFile(userPesConfigFile)
		settings = Settings()
		
		logging.info("loading GUI...")
		signal.signal(signal.SIGINT, signalHandler)
		signal.signal(signal.SIGHUP, signalHandler)
		atexit.register(exitHandler)
		
		app = QApplication(sys.argv)
		window = PESWindow(app, settings, not args.window)
		window.run()
		#sys.exit(app.exec_())
		
		
	except Exception as e:
		logging.exception(e)
		sys.exit(1)
