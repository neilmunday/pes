#!/usr/bin/env python2

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2014 Neil Munday (neil@mundayweb.com)
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
import pygame
from pygame.locals import *
import peslib

if __name__ == "__main__":

	scriptDir = os.path.dirname(os.path.realpath(__file__)) # the absolute path of the directory containing pes.py
	commandFile = scriptDir + os.sep + 'commands.sh'

	parser = argparse.ArgumentParser(description='Launch the Pi Entertainment System (PES)', add_help=True)
	parser.add_argument('-w', '--window', help='Run PES in a window', dest='window', action='store_true')
	parser.add_argument('-v', '--verbose', help='Turn on debug messages', dest='verbose', action='store_true')
	args = parser.parse_args()

	peslib.verbose = args.verbose
	
	try:
		import cec
		printMsg("enabling CEC...")
		cec.init()
		printMsg("adding CEC callback...")
		cec.add_callback(handleCecEvent, cec.EVENT_KEYPRESS)
	except ImportError, e:
		peslib.printMsg("CEC module not found, disabling CEC functions")

	pygame.init()

	if not pygame.font: print 'Warning, fonts disabled'
	if not pygame.mixer: print 'Warning, sound disabled'

	pesActive = False

	peslib.printMsg("script dir is: %s" % scriptDir)
	peslib.printMsg("loading GUI...")
	pes = peslib.PES(args.window, commandFile)
	pesActive = True
	command = pes.run()
	pesActive = False

	launchArgs = ''
	if peslib.verbose:
		launchArgs += ' -v '
	if args.window:
		launchArgs += ' -w '

	with open(commandFile, 'w') as f:
		if command:
			f.write("echo running %s\n" % command)
			f.write("%s\n" % command)
			f.write("exec %s/pes.sh %s\n" % (scriptDir, launchArgs))
		else:
			f.write('exit')
	sys.exit(0)
