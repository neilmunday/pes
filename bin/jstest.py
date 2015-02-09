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

#
#    Helper program for testing joysticks with PyGame by Neil Munday
#

import sys
import os
import argparse
import signal
from signal import SIGTERM
import pygame
from pygame.locals import *

def stopTest(sig, dummy):
	print "Exiting..."
	sys.exit(0)	

if __name__ == "__main__":

	signal.signal(signal.SIGTERM, stopTest)
	signal.signal(signal.SIGINT, stopTest)

	parser = argparse.ArgumentParser(description='PES joystick detection test code', add_help=True)
	parser.add_argument('-j', '--joystick', help='Joystick number to test', dest='jsNumber', type=int, required=True)
	args = parser.parse_args()

	os.environ["SDL_VIDEODRIVER"] = "dummy"

	pygame.init()
	pygame.joystick.init()

	js = pygame.joystick.Joystick(args.jsNumber)
	if js == None:
		print "Error initialising joystick"
		sys.exit(1)
	js.init()
	initialAxis = []
	for i in range(0, js.get_numaxes()):
		initialAxis.append(0)
	
	print "\nListening for joystick events for joystick %d (%s), press Ctrl + C to exit" % (args.jsNumber, js.get_name())

	stop = False
	initialised = False
	lastAxis = -1
	lastAxisValue = 0
	lastButton = -1

	print "Please press a button once your control pad's axes are in their rest positions"

	while stop == False:

		for event in pygame.event.get():
			if not initialised:
				if event.type == pygame.JOYBUTTONDOWN:
					print "Beginning detection"
					print "Initial values..."
					for i in range(0, js.get_numaxes()):
						value =  js.get_axis(i)
						print "axis %d, value %f" % (i, value)
						if abs(value) > 0.5:
							initialAxis[i] = value
						print initialAxis
					initialised = True
					print "\nListening for button presses...\n"

		if initialised:
			# loop through buttons
			for i in range(0, js.get_numbuttons()):
				if js.get_button(i) and lastButton != i:
					print "joystick %d, button %d pressed" % (args.jsNumber, i)
					lastButton = i

			# loop through axes
			for i in range(0, js.get_numaxes()):
				value = js.get_axis(i)
				if lastAxis != i or (lastAxis == i and ((value < 0 and lastAxisValue > 0) or (value > 0 and lastAxisValue < 0))):
					if abs(value) > 0.9 and abs(value - initialAxis[i]) > 0.5:
						print "joystick %d, axis %d, value: %f" % (args.jsNumber, i, value)
						lastAxis = i
						lastAxisValue = value

			#print "Sleeping..."
			pygame.time.wait(10)
		
	print "Exiting..."
	sys.exit(0)

