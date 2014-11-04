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

import sys
import pygame
from pygame.locals import *

if __name__ == "__main__":
	pygame.init()
	pygame.joystick.init()
	joystickTotal = pygame.joystick.get_count()
	print "Found %d joysticks" % joystickTotal
	for i in range(0, joystickTotal):
		js = pygame.joystick.Joystick(i)
		js.init()
		print "Joystick %d: %s" % (i, js.get_name())
	

