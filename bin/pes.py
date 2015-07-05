#!/usr/bin/env python2

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2015 Neil Munday (neil@mundayweb.com)
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

import os
import sys
import argparse
import ConfigParser
import logging
import pygame
from pygame.locals import *
import peslib

def handleCecEvent(event, *args):
	global pes
	if pes:
		pes.handleCecEvent(event, args)

if __name__ == "__main__":
	global pes

	scriptDir = os.path.dirname(os.path.realpath(__file__)) # the absolute path of the directory containing pes.py
	commandFile = scriptDir + os.sep + 'commands.sh'

	parser = argparse.ArgumentParser(description='Launch the Pi Entertainment System (PES)', add_help=True)
	parser.add_argument('-w', '--window', help='Run PES in a window', dest='window', action='store_true')
	parser.add_argument('-v', '--verbose', help='Turn on debug messages', dest='verbose', action='store_true')
	parser.add_argument('-l', '--log', help='File to log messages to', type=str, dest='logfile')
	args = parser.parse_args()

	peslib.verbose = args.verbose

	logLevel = logging.INFO
	if args.verbose:
		logLevel = logging.DEBUG

	if args.logfile:
		logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=logLevel, filename=args.logfile)
	else:
		logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=logLevel)

	try:
		# and so begins some rubbish code to handle CEC events
		# it would seem that trying to add the CEC event handler to a method of a Python object is a no go :-(	
		baseDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)) + os.sep + '../')
		confFile= baseDir + os.sep + 'conf.d' + os.sep + 'pes' + os.sep + 'pes.ini'
		if not os.path.exists(confFile) or not os.path.isfile(confFile):
			msg = "%s does not exist or is not a file!" % confFile
			logging.error(msg)
			print msg
			sys.exit(1)
		
		cecEnabled = False
		configParser = ConfigParser.ConfigParser()
		configParser.read(confFile)
		try:
			cecEnabled = configParser.getboolean('pes', 'hdmi-cec')
		except ConfigParser.NoOptionError, e:
			logging.error("could not find hdmi-cec option in %s" % confFile)
		
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

		pygame.init()

		logging.debug("script dir is: %s" % scriptDir)
		logging.info("loading GUI...")
		pes = peslib.PES(args.window, commandFile)
		if cecEnabled:
			try:
				cec.init()
				logging.debug("adding CEC callback...")
				cec.add_callback(handleCecEvent, cec.EVENT_KEYPRESS)
			except Exception, e:
				cecEnabled = False
				logging.error("CEC module initilisation failed, disabling CEC functions")
		command = pes.run()

		launchArgs = ''
		if peslib.verbose:
			launchArgs += ' -v '
		if args.window:
			launchArgs += ' -w '
		if args.logfile:
			launchArgs += ' -l %s' % args.logfile

		with open(commandFile, 'w') as f:
			if command:
				execLog = baseDir + os.sep + 'log/exec.log'
				f.write("echo running %s\n" % command)
				f.write("echo see %s for console output\n" % execLog)
				f.write("%s &> %s\n" % (command, execLog)) # redirect stdout and stderr to get a frame rate boost
				f.write("exec %s/pes.sh %s\n" % (scriptDir, launchArgs))
			else:
				f.write("exit\n")
		sys.exit(0)
	except Exception, e:
		logging.exception(e)
		sys.exit(1)
