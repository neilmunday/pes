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

from ctypes import c_char_p, c_void_p, cast
import logging
import sdl2

EVENT_TYPE = None

# PES Events
EVENT_DB_UPDATE = 1
EVENT_RESOURCES_LOADED = 2
EVENT_ACHIEVEMENTS_UPDATE = 3

def decodePesEvent(event):
	data1 = cast(event.user.data1, c_char_p)
	data2 = cast(event.user.data2, c_char_p)
	return (event.user.code, data1.value, data2.value)

def pushPesEvent(eventType, data1="", data2=""):
	global EVENT_TYPE
	if EVENT_TYPE == None:
		logging.error("pushPesEvent: PES Event Type has not been registered!")
		return False
	pesEvent = sdl2.SDL_Event()
	pesEvent.type = EVENT_TYPE
	pesEvent.user.code = eventType
	pesEvent.user.data1 = cast(c_char_p(data1), c_void_p)
	pesEvent.user.data2 = cast(c_char_p(data2), c_void_p)
	logging.debug("pushPesEvent: pushing event (%d, %s, %s)" % (eventType, data1, data2))
	sdl2.SDL_PushEvent(pesEvent)
	return True

def registerPesEventType():
	global EVENT_TYPE
	EVENT_TYPE = sdl2.SDL_RegisterEvents(1)
	if EVENT_TYPE == -1:
		return False
	return True
