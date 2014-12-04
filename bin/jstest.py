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
import signal
from signal import SIGTERM
import pygame
from pygame.locals import *

def stopTest(sig, dummy):
	print "Exiting..."
	sys.exit(0)	

if __name__ == "__main__":

	AXIS_PRESSED = 1
	AXIS_RELEASED = 2

	signal.signal(signal.SIGTERM, stopTest)
	signal.signal(signal.SIGINT, stopTest)

	pygame.init()
	pygame.joystick.init()
	joystickTotal = pygame.joystick.get_count()
	print "Found %d joysticks" % joystickTotal
	for i in range(0, joystickTotal):
		js = pygame.joystick.Joystick(i)
		js.init()
		print "Joystick %d: %s" % (i, js.get_name())
	
	print "Listening for joystick events..."

	stop = False

	axisHistory = {}

	while stop == False:

		for event in pygame.event.get():
			if event.type == pygame.JOYBUTTONDOWN:
				print "joystick %d, button pressed: %d" % (event.joy, event.button)
			elif event.type == pygame.JOYBUTTONUP:
				print "joystick %d, button released: %d" % (event.joy, event.button)
			elif event.type == pygame.JOYAXISMOTION:
				if event.value >= 0.5 or event.value <= -0.5:
					print "joystick %d, axis: %d, value: %f" % (event.joy, event.axis, event.value)
					if not axisHistory.has_key(event.joy):
						axisHistory[event.joy] = {}

					if not axisHistory[event.joy].has_key(event.axis):
						axisHistory[event.joy][event.axis] = AXIS_PRESSED
					
					if axisHistory[event.joy][event.axis] == AXIS_RELEASED:
						axisHistory[event.joy][event.axis] = AXIS_PRESSED
						print "joystick %d, axis: %d ACTIVATED" % (event.joy, event.axis)
				else:
					if not axisHistory.has_key(event.joy):
						axisHistory[event.joy] = {}

					if not axisHistory[event.joy].has_key(event.axis):
						axisHistory[event.joy][event.axis] = AXIS_RELEASED

					if axisHistory[event.joy][event.axis] == AXIS_PRESSED:
						axisHistory[event.joy][event.axis] = AXIS_RELEASED
						print "joystick %d, axis: %d DEACTIVATED" % (event.joy, event.axis)

		
	print "Exiting..."
	sys.exit(0)

