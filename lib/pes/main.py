#!/usr/bin/env python2

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2021 Neil Munday (neil@mundayweb.com)
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
import ConfigParser
import cProfile
import logging
import os
import pstats
import shutil
import signal
import sqlite3
import StringIO
import sys
from pes import *
from pes.data import Console
from pes.app import PESApp
from pes.config import PESConfig
from pes.util import *

def exitHandler():
	global profile, profileObj

	if profile and profileObj != None:
		profileObj.disable()
		# dump stats
		s = StringIO.StringIO()
		ps = pstats.Stats(profileObj, stream=s).sort_stats('cumulative')
		ps.print_stats()
		logging.info("Profile Stats:")
		logging.info(s.getvalue())

def signalHandler(sig, frame):
	global app, profile, profileObj

	if sig == signal.SIGINT:
		logging.debug("signalHandler: SIGINT")
		app.exit()
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

	dimensions = (0, 0)
	if args.window:
		dimensions = (1024, 768)

	logging.debug("PES %s, date: %s, author: %s" % (VERSION_NUMBER, VERSION_DATE, VERSION_AUTHOR))

	try:
		logging.debug("PES base dir: %s" % baseDir)
		checkDir(baseDir)
		logging.debug("PES config dir: %s" % confDir)
		checkDir(confDir)
		logging.debug("PES user dir: %s" % userDir)
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
		checkFile(gamepadImageFile)
		checkFile(networkImageFile)
		checkFile(remoteImageFile)
		checkFile(rasumExe)

		logging.info("loading settings...")
		checkFile(userPesConfigFile)

		try:
			pesConfig = PESConfig(userPesConfigFile)
		except ConfigParser.NoOptionError as e:
			pesExit("Error parsing config file %s: %s" % (userPesConfigFile, e.message), True)
		except ValueError as e:
			pesExit("Error parsing config file %s: %s" % (userPesConfigFile, e.message), True)

		mkdir(pesConfig.romsDir)
		mkdir(pesConfig.coverartDir)
		mkdir(pesConfig.badgeDir)
		mkdir(pesConfig.biosDir)
		mkdir(userKodiConfDir)
		mkdir(pesConfig.kodiDir)

		# now make kodi sub dirs
		for d in ['Music', 'Movies', 'TV']:
			mkdir(os.path.join(pesConfig.kodiDir, d))

		# create kodi sources file (if it does not already exist)
		kodiUserDataDir = os.path.join(userKodiConfDir, 'userdata')
		mkdir(kodiUserDataDir)
		kodiSourceFile = os.path.join(kodiUserDataDir, 'sources.xml')
		if not os.path.exists(kodiSourceFile):
			logging.info("creating kodi sources file: %s" % kodiSourceFile)

			with open(kodiSourceFile, 'w') as f:
				f.write(
"""<sources>
	<programs>
		<default pathversion="1"></default>
	</programs>
	<video>
		<default pathversion="1"></default>
		<source>
			<name>TV</name>
			<path pathversion="1">%s/TV/</path>
			<allowsharing>true</allowsharing>
		</source>
		<source>
			<name>Movies</name>
			<path pathversion="1">%s/Movies/</path>
			<allowsharing>true</allowsharing>
		</source>
	</video>
	<music>
		<default pathversion="1"></default>
		<source>
			<name>Music</name>
			<path pathversion="1">%s/Music</path>
			<allowsharing>true</allowsharing>
		</source>
	</music>
	<pictures>
		<default pathversion="1"></default>
	</pictures>
	<files>
		<default pathversion="1"></default>
	</files>
</sources>""" % (pesConfig.kodiDir, pesConfig.kodiDir, pesConfig.kodiDir))
		else:
			logging.debug("%s already exists, no need to create it" % kodiSourceFile)

		checkFile(pesConfig.fontFile)

		if pesConfig.cecEnabled:
			pesConfig.cecEnabled = False
			try:
				import cec
				logging.info("CEC module enabled")
				pesConfig.cecEnabled = True
			except ImportError as e:
				logging.info("CEC module not found, disabling CEC functions")
		else:
			logging.debug("CEC disabled in pes.ini")

		app = PESApp(dimensions, pesConfig)

		if pesConfig.cecEnabled:
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
			except Exception as e:
				pesConfig.cecEnabled = False
				logging.error("CEC module initilisation failed, disabling CEC functions")
				logging.error(e)

		app.setCecEnabled(pesConfig.cecEnabled)

		logging.info("loading GUI...")
		signal.signal(signal.SIGINT, signalHandler)
		signal.signal(signal.SIGHUP, signalHandler)
		atexit.register(exitHandler)
		app.run()
	except Exception as e:
		logging.exception(e)
		sys.exit(1)
