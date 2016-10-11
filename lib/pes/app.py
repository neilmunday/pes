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

from ctypes import c_int, c_char, c_char_p, c_uint32, c_void_p, byref, cast
from datetime import datetime
from pes import *
from pes.data import *
from pes.dbupdate import *
from pes.gamecontrollerdb import GameControllerDb
from pes.retroachievements import *
from pes.ui import *
import pes.event
from pes.util import *
from PIL import Image
from collections import OrderedDict
from subprocess import Popen, PIPE
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
import glob
import logging
import math
import ConfigParser
import pes.event
import random
import re
import sdl2
import sdl2.ext
import sdl2.sdlimage
import sdl2.joystick
import sdl2.video
import sdl2.render
import sdl2.sdlgfx
import sdl2.sdlttf
import sdl2.timer
import sqlite3
import sys
import threading
import time
import urllib
import urllib2
try:
	import cec
except ImportError:
	pass

CONSOLE_TEXTURE_ALPHA = 50
JOYSTICK_AXIS_MIN = -32766
JOYSTICK_AXIS_MAX = 32766

logging.getLogger("PIL").setLevel(logging.WARNING)

def mapAxisToKey(axis, value):
	if axis == sdl2.SDL_CONTROLLER_AXIS_LEFTY:
		if value > 0:
			return sdl2.SDLK_DOWN
		return sdl2.SDLK_UP
	return None

def mapButtonToKey(button):
	if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
		return sdl2.SDLK_DOWN
	if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:
		return sdl2.SDLK_UP
	if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
		return sdl2.SDLK_LEFT
	if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:
		return sdl2.SDLK_RIGHT
	if button == sdl2.SDL_CONTROLLER_BUTTON_A:
		return sdl2.SDLK_RETURN
	if button == sdl2.SDL_CONTROLLER_BUTTON_B:
		return sdl2.SDLK_BACKSPACE
	if button == sdl2.SDL_CONTROLLER_BUTTON_BACK: # select button
		return sdl2.SDLK_s
	if button == sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER:
		return sdl2.SDLK_PAGEUP
	if button == sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER:
		return sdl2.SDLK_PAGEDOWN
	if button == sdl2.SDL_CONTROLLER_BUTTON_GUIDE:
		return sdl2.SDLK_HOME
	return None

def mapRemoteButtonEvent(button):
	key = None
	if button == cec.CEC_USER_CONTROL_CODE_UP:
		key = sdl2.SDLK_UP
	elif button == cec.CEC_USER_CONTROL_CODE_DOWN:
		key = sdl2.SDLK_DOWN
	elif button == cec.CEC_USER_CONTROL_CODE_LEFT:
		key = sdl2.SDLK_LEFT
	elif button == cec.CEC_USER_CONTROL_CODE_RIGHT:
		key = sdl2.SDLK_RIGHT
	elif button == cec.CEC_USER_CONTROL_CODE_SELECT:
		key = sdl2.SDLK_RETURN
	elif button == cec.CEC_USER_CONTROL_CODE_UP:
		key = sdl2.SDLK_UP
	elif button == cec.CEC_USER_CONTROL_CODE_AN_RETURN:
		key = sdl2.SDLK_BACKSPACE
	else:
		return
	e = sdl2.SDL_Event()
	e.type = sdl2.SDL_KEYDOWN
	e.key.keysym.sym = key
	return e

def mapControlPadAxisEvent(event, eventType):
	key = mapAxisToKey(event.caxis.axis, event.caxis.value)
	if key:
		e = sdl2.SDL_Event()
		e.type = eventType
		e.key.keysym.sym = key
		return e
	return None

def mapControlPadButtonEvent(event, eventType):
	key = mapButtonToKey(event.cbutton.button)
	if key:
		e = sdl2.SDL_Event()
		e.type = eventType
		e.key.keysym.sym = key
		return e
	return None

class PESApp(object):
	
	__CONTROL_PAD_BUTTON_REPEAT = 150 # delay in ms between firing events for button holds
	__ICON_WIDTH = 32
	__ICON_HEIGHT = 32
	
	def __del__(self):
		logging.debug("PESApp.del: deleting object")
		if getattr(self, "__window", None):
			logging.debug("PESApp.del: window destroyed")
			sdl2.video.SDL_DestroyWindow(self.__window)
			self.__window = None

	#def __init__(self, dimensions, fontFile, romsDir, coverartDir, coverartSize, coverartCacheLen, iconCacheLen, badgeDir, backgroundColour, menuBackgroundColour, headerBackgroundColour, lineColour, textColour, menuTextColour, menuSelectedTextColour, lightBackgroundColour, shutdownCommmand, rebootCommand, listTimezonesCommand, getTimezoneCommand, setTimezoneCommand):
	def __init__(self, dimensions, pesConfig):
		super(PESApp, self).__init__()
		self.__dimensions = dimensions
		self.__shutdownCommand = pesConfig.shutdownCommand
		self.__rebootCommand = pesConfig.rebootCommand
		self.listTimezonesCommand = pesConfig.listTimezonesCommand
		self.getTimezoneCommand = pesConfig.getTimezoneCommand
		self.setTimezoneCommand = pesConfig.setTimezoneCommand
		self.timezones = []
		self.currentTimezone = None
		self.fontFile = pesConfig.fontFile
		self.romsDir = pesConfig.romsDir
		self.coverartDir = pesConfig.coverartDir
		self.badgeDir = pesConfig.badgeDir
		
		self.__screenSaverTimeout = pesConfig.screenSaverTimeout
		
		self.__fontSizes = pesConfig.fontSizes
		
		ConsoleTask.SCALE_WIDTH = pesConfig.coverartSize
		Thumbnail.CACHE_LEN = pesConfig.coverartCacheLen
		Icon.CACHE_LEN = pesConfig.iconCacheLen
		
		self.coverartCacheLen = pesConfig.coverartCacheLen
		self.consoles = []
		self.consoleSurfaces = {}
		self.__uiObjects = [] # list of UI objects created so we can destroy them upon exit
		
		self.lineColour = sdl2.SDL_Color(pesConfig.lineColour[0], pesConfig.lineColour[1], pesConfig.lineColour[2])
		self.backgroundColour = sdl2.SDL_Color(pesConfig.backgroundColour[0], pesConfig.backgroundColour[1], pesConfig.backgroundColour[2])
		self.headerBackgroundColour = sdl2.SDL_Color(pesConfig.headerBackgroundColour[0], pesConfig.headerBackgroundColour[1], pesConfig.headerBackgroundColour[2])
		self.menuBackgroundColour = sdl2.SDL_Color(pesConfig.menuBackgroundColour[0], pesConfig.menuBackgroundColour[1], pesConfig.menuBackgroundColour[2])
		self.menuTextColour = sdl2.SDL_Color(pesConfig.menuTextColour[0], pesConfig.menuTextColour[1], pesConfig.menuTextColour[2])
		self.menuSelectedTextColour = sdl2.SDL_Color(pesConfig.menuSelectedTextColour[0], pesConfig.menuSelectedTextColour[1], pesConfig.menuSelectedTextColour[2])
		self.menuSelectedBgColour = self.lineColour
		self.textColour = sdl2.SDL_Color(pesConfig.textColour[0], pesConfig.textColour[1], pesConfig.textColour[2])
		self.lightBackgroundColour = sdl2.SDL_Color(pesConfig.lightBackgroundColour[0], pesConfig.lightBackgroundColour[1], pesConfig.lightBackgroundColour[2])
		
		self.__headerHeight = pesConfig.headerHeight
		self.__footerHeight = 0

		self.doJsToKeyEvents = True
		self.__screenSaverTimeout = screenSaverTimeout
		self.__cecEnabled = False
		self.retroAchievementConn = None
		self.achievementUser = None
		
		if pesConfig.retroAchievementsUserName != None and pesConfig.retroAchievementsPassword != None and pesConfig.retroAchievementsApiKey != None:
			#self.__setRetroAchievements(self, pesConfig.retroAchievementsUserName, pesConfig.retroAchievementsPassword, pesConfig.retroAchievementsApiKey):
			logging.debug("PESApp.__init__: RetroAchievements user = %s, apiKey = %s" % (pesConfig.retroAchievementsUserName, pesConfig.retroAchievementsApiKey))
			self.retroAchievementConn = RetroAchievementConn(pesConfig.retroAchievementsUserName, pesConfig.retroAchievementsApiKey)
			self.__retroAchievementsPassword = pesConfig.retroAchievementsPassword
			self.setUpRetroAchievementUser()
		
	def exit(self, rtn=0, confirm=False):
		if confirm:
			self.showMessageBox("Are you sure?", self.exit, rtn, False)
		else:
			# tidy up
			logging.debug("PESApp.exit: stopping screens...")
			for s in self.screens:
				self.screens[s].stop()
			logging.debug("PESApp.exit: purging cached surfaces...")
			for console, surface in self.consoleSurfaces.iteritems():
				logging.debug("PESApp.exit: unloading surface for %s..." % console)
				sdl2.SDL_FreeSurface(surface)
			logging.debug("PESApp.exit: tidying up...")
			self.__gamepadIcon.destroy()
			self.__remoteIcon.destroy()
			self.__networkIcon.destroy()
			if self.__screenSaverLabel:
				self.__screenSaverLabel.destroy()
			if self.__msgBox:
				self.__msgBox.destroy()
			Thumbnail.destroyTextures()
			Icon.destroyTextures()
			for o in self.__uiObjects:
				o.destroy()
			sdl2.sdlttf.TTF_CloseFont(self.headerFont)
			sdl2.sdlttf.TTF_CloseFont(self.bodyFont)
			sdl2.sdlttf.TTF_CloseFont(self.menuFont)
			sdl2.sdlttf.TTF_CloseFont(self.titleFont)
			sdl2.sdlttf.TTF_CloseFont(self.splashFont)
			sdl2.sdlttf.TTF_Quit()
			sdl2.sdlimage.IMG_Quit()
			sdl2.SDL_Quit()
			logging.info("PESApp.exit: exiting...")
			sys.exit(rtn)
			
	def getGameTotal(self):
		# get number of games
		try:
			con = sqlite3.connect(userPesDb)
			con.row_factory = sqlite3.Row
			cur = con.cursor()
			cur.execute('SELECT COUNT(*) AS `total` FROM `games`;')
			row = cur.fetchone()
			if row == None or row['total'] == 0:
				return 0
			return int(row['total'])
		except sqlite3.Error, e:
			pesExit("Error: %s" % e.args[0], True)
		finally:
			if con:
				con.close()
			
	@staticmethod
	def getMupen64PlusConfigAxisValue(controller, axis, positive=True, both=False):
		bind = sdl2.SDL_GameControllerGetBindForAxis(controller, axis)
		if bind:
			if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_AXIS:
				if both:
					return "axis(%d-,%d+)" % (bind.value.axis, bind.value.axis)
				if positive:
					return "axis(%d+)" % bind.value.axis
				return "axis(%d-)" % bind.value.axis
			if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_BUTTON:
				return "button(%d)" % bind.value.button
		return "\"\""
			
	@staticmethod
	def getMupen64PlusConfigButtonValue(controller, button, coreEvent=False):
		bind = sdl2.SDL_GameControllerGetBindForButton(controller, button)
		if bind:
			if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_BUTTON:
				if coreEvent:
					return "B%d" % bind.value.button
				return "button(%d)" % bind.value.button
			if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_HAT:
				if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:
					return "hat(%d Up)" % bind.value.hat.hat
				if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
					return "hat(%d Down)" % bind.value.hat.hat
				if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
					return "hat(%d Left)" % bind.value.hat.hat
				if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:
					return "hat(%d Right)" % bind.value.hat.hat
		return "\"\""
	
	@staticmethod
	def getRetroArchConfigAxisValue(param, controller, axis, both=False):
		bind = sdl2.SDL_GameControllerGetBindForAxis(controller, axis)
		if bind:
			if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_AXIS:
				if both:
						return "%s_plus_axis = \"+%d\"\n%s_minus_axis = \"-%d\"\n" % (param, bind.value.axis, param, bind.value.axis)
				return "%s_axis = \"+%d\"\n" % (param, bind.value.axis)
			if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_BUTTON:
				return "%s_btn = \"%d\"\n" % (param, bind.value.button)
				
		if both:
			return "%s_plus_axis = \"nul\"\n%s_minus_axis = \"nul\"\n" % (param, param)
		return "%s = \"nul\"\n" % param
	
	@staticmethod
	def getRetroArchConfigButtonValue(param, controller, button):
		bind = sdl2.SDL_GameControllerGetBindForButton(controller, button)
		if bind:			
			if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_BUTTON:
				return "%s_btn = \"%d\"\n" % (param, bind.value.button)
			if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_AXIS:
				#return PESApp.getRetroArchConfigAxisValue(param, controller, bind.value.axis)
				if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP or button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
					return "%s_axis = \"-%d\"\n" % (param, bind.value.axis)
				return "%s_axis = \"+%d\"\n" % (param, bind.value.axis)
			if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_HAT:
				if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:
					return "%s_btn = \"h%d%s\"\n" % (param, bind.value.hat.hat, "up")
				if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
					return "%s_btn = \"h%d%s\"\n" % (param, bind.value.hat.hat, "down")
				if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
					return "%s_btn = \"h%d%s\"\n" % (param, bind.value.hat.hat, "left")
				if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:
					return "%s_btn = \"h%d%s\"\n" % (param, bind.value.hat.hat, "right")
		return "%s = \"nul\"\n" % param
	
	@staticmethod
	def getViceButtonValue(controller, joyIndex, button, pin):
		bind = sdl2.SDL_GameControllerGetBindForButton(controller, button)
		if bind:
			if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_BUTTON:
				if pin >= 0:
					return "%d 1 %d 1 0 %d\n" % (joyIndex, bind.value.button, pin)
				return "%d 1 %d %d\n" % (joyIndex, bind.value.button, abs(pin))
			elif bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_HAT:
				# NOTE: not sure this is the correct way to generate hat mappings, works for XBOX 360 at least
				if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:
					return "%d 2 0 1 0 %d\n" % (joyIndex, abs(pin))
				if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
					return "%d 2 1 1 0 %d\n" % (joyIndex, abs(pin))
				if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
					return "%d 2 2 1 0 %d\n" % (joyIndex, abs(pin))
				if button == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:
					return "%d 2 3 1 0 %d\n" % (joyIndex, abs(pin))
		return "# error: could not generate binding for button: %d\n" % button
	
	def goBack(self):
		logging.debug("PESApp.goBack: adding backspace event to event queue...")
		self.screens[self.screenStack[-1]].setMenuActive(False)
		e = sdl2.SDL_Event()
		e.type = sdl2.SDL_KEYDOWN
		e.key.keysym.sym = sdl2.SDLK_BACKSPACE
		sdl2.SDL_PushEvent(e)
	
	def initScreens(self):
		logging.debug("PESApp.initScreens: initialising screens...")
		self.screens["Home"] = HomeScreen(self, self.renderer, self.menuRect, self.screenRect)
		self.screens["Settings"] = SettingsScreen(self, self.renderer, self.menuRect, self.screenRect)
		self.screens["Play"] = PlayScreen(self, self.renderer, self.menuRect, self.screenRect, None)
		consoleScreens = 0
		for c in self.consoles:
			if c.getGameTotal() > 0:
				self.screens["Console %s" % c.getName()] = ConsoleScreen(self, self.renderer, self.menuRect, self.screenRect, c)
				consoleScreens += 1
		logging.debug("PESApp.initScreens: initialised %d screens of which %d are console screens" % (len(self.screens), consoleScreens))
		self.screenStack = ["Home"]
	
	def initSurfaces(self, refreshConsoles=False):
		logging.debug("PESApp.initSurfaces: pre-loading console images...")
		for c in self.consoles:
			if refreshConsoles:
				c.refresh()
			consoleName = c.getName()
			if c.getGameTotal() > 0 and consoleName not in self.consoleSurfaces:
				image = c.getImg()
				surface = sdl2.sdlimage.IMG_Load(image)
				if surface == None:
					logging.error("PESApp.initSurfaces: failed to load image: %s" % image)
					self.exit(1)
				self.consoleSurfaces[consoleName] = surface
				logging.debug("PESApp.initSurfaces: pre-loaded %s surface from %s" % (consoleName, image))
			
	def playGame(self, game):
		emulator = game.getConsole().getEmulator()
		logging.debug("PESApp.playGame: emulator is %s" % emulator)
		if emulator == "RetroArch":
			# note: RetroArch uses a SNES control pad button layout, SDL2 uses XBOX 360 layout!
			# check joystick configs
			joystickTotal = sdl2.joystick.SDL_NumJoysticks()
			if joystickTotal > 0:
				for i in xrange(joystickTotal):
					if sdl2.SDL_IsGameController(i):
						c = sdl2.SDL_GameControllerOpen(i)
						if sdl2.SDL_GameControllerGetAttached(c):
							# get joystick name
							j = sdl2.SDL_GameControllerGetJoystick(c)
							jsName = sdl2.SDL_JoystickName(j)
							jsConfig = os.path.join(userRetroArchJoysticksConfDir, "%s.cfg" % jsName)
							logging.debug("PESApp.playGame: checking for \"%s\" config..." % jsConfig)
							logging.debug("PESApp.playGame: creating configuration file %s for %s" % (jsConfig, jsName))
							vendorId, productId = getJoystickDeviceInfoFromGUID(getJoystickGUIDString(sdl2.SDL_JoystickGetDeviceGUID(i)))
							with open(jsConfig, 'w') as f:
								# control pad id etc.
								f.write("input_device = \"%s\"\n" % jsName)
								f.write("input_vendor_id = \"%s\"\n" % vendorId)
								f.write("input_product_id = \"%s\"\n" % productId)
								#f.write("input_driver = \"udev\"\n")
								# buttons
								f.write(self.getRetroArchConfigButtonValue("input_a", c, sdl2.SDL_CONTROLLER_BUTTON_B))
								f.write(self.getRetroArchConfigButtonValue("input_b", c, sdl2.SDL_CONTROLLER_BUTTON_A))
								f.write(self.getRetroArchConfigButtonValue("input_x", c, sdl2.SDL_CONTROLLER_BUTTON_Y))
								f.write(self.getRetroArchConfigButtonValue("input_y", c, sdl2.SDL_CONTROLLER_BUTTON_X))
								f.write(self.getRetroArchConfigButtonValue("input_start", c, sdl2.SDL_CONTROLLER_BUTTON_START))
								f.write(self.getRetroArchConfigButtonValue("input_select", c, sdl2.SDL_CONTROLLER_BUTTON_BACK))
								# shoulder buttons
								f.write(self.getRetroArchConfigButtonValue("input_l", c, sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER))
								f.write(self.getRetroArchConfigButtonValue("input_r", c, sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER))
								f.write(self.getRetroArchConfigAxisValue("input_l2", c, sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT))
								f.write(self.getRetroArchConfigAxisValue("input_r2", c, sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT))
								# L3/R3 buttons
								f.write(self.getRetroArchConfigButtonValue("input_l3", c, sdl2.SDL_CONTROLLER_BUTTON_LEFTSTICK))
								f.write(self.getRetroArchConfigButtonValue("input_r3", c, sdl2.SDL_CONTROLLER_BUTTON_RIGHTSTICK))
								# d-pad buttons
								f.write(self.getRetroArchConfigButtonValue("input_up", c, sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP))
								f.write(self.getRetroArchConfigButtonValue("input_down", c, sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN))
								f.write(self.getRetroArchConfigButtonValue("input_left", c, sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT))
								f.write(self.getRetroArchConfigButtonValue("input_right", c, sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT))
								# axis
								f.write(self.getRetroArchConfigAxisValue("input_l_x", c, sdl2.SDL_CONTROLLER_AXIS_LEFTX, True))
								f.write(self.getRetroArchConfigAxisValue("input_l_y", c, sdl2.SDL_CONTROLLER_AXIS_LEFTY, True))
								f.write(self.getRetroArchConfigAxisValue("input_r_x", c, sdl2.SDL_CONTROLLER_AXIS_RIGHTX, True))
								f.write(self.getRetroArchConfigAxisValue("input_r_y", c, sdl2.SDL_CONTROLLER_AXIS_RIGHTY, True))
								# hot key buttons
								bind = sdl2.SDL_GameControllerGetBindForButton(c, sdl2.SDL_CONTROLLER_BUTTON_GUIDE)
								if bind:
									f.write(self.getRetroArchConfigButtonValue("input_enable_hotkey", c, sdl2.SDL_CONTROLLER_BUTTON_GUIDE))
								else:
									f.write(self.getRetroArchConfigButtonValue("input_enable_hotkey", c, sdl2.SDL_CONTROLLER_BUTTON_BACK))
								f.write(self.getRetroArchConfigButtonValue("input_exit_emulator", c, sdl2.SDL_CONTROLLER_BUTTON_START))
								f.write(self.getRetroArchConfigButtonValue("input_save_state", c, sdl2.SDL_CONTROLLER_BUTTON_A))
								f.write(self.getRetroArchConfigButtonValue("input_load_state", c, sdl2.SDL_CONTROLLER_BUTTON_B))
								f.write("input_pause_toggle = \"nul\"\n")
						sdl2.SDL_GameControllerClose(c)
			# now set-up RetroAchievements
			s = "# THIS FILE IS AUTOMATICALLY GENERATED BY PES!\n"
			if self.retroAchievementConn == None:
				s += "cheevos_enable = false\n"
			else:
				s += "cheevos_username = %s\n" % self.retroAchievementConn.getUsername()
				s += "cheevos_password = %s\n" % self.__retroAchievementsPassword
				s += "cheevos_enable = true\n"
			with open(userRetroArchCheevosConfFile, "w") as f:
				f.write(s)
		elif emulator == "Mupen64Plus":
			joystickTotal = sdl2.joystick.SDL_NumJoysticks()
			if joystickTotal > 0:
				if not os.path.exists(userMupen64PlusConfFile):
					logging.error("PESApp.playGame: could not open %s" % userMupen64PlusConfFile)
					self.exit(1)
				configParser = ConfigParser.SafeConfigParser()
				configParser.optionxform = str # make options case sensitive
				configParser.read(userMupen64PlusConfFile)
				bind = sdl2.SDL_GameControllerGetBindForButton(self.__controlPad, sdl2.SDL_CONTROLLER_BUTTON_GUIDE)
				if bind:
					hotkey = self.getMupen64PlusConfigButtonValue(self.__controlPad, sdl2.SDL_CONTROLLER_BUTTON_GUIDE, True)
				else:
					hotkey = self.getMupen64PlusConfigButtonValue(self.__controlPad, sdl2.SDL_CONTROLLER_BUTTON_BACK, True)
				if configParser.has_section('CoreEvents'):
					configParser.set('CoreEvents', 'Joy Mapping Stop', 'J%d%s/%s' % (self.__controlPadIndex, hotkey, self.getMupen64PlusConfigButtonValue(self.__controlPad, sdl2.SDL_CONTROLLER_BUTTON_START, True)))
					configParser.set('CoreEvents', 'Joy Mapping Save State', 'J%d%s/%s' % (self.__controlPadIndex, hotkey, self.getMupen64PlusConfigButtonValue(self.__controlPad, sdl2.SDL_CONTROLLER_BUTTON_A, True)))
					configParser.set('CoreEvents', 'Joy Mapping Load State', 'J%d%s/%s' % (self.__controlPadIndex, hotkey, self.getMupen64PlusConfigButtonValue(self.__controlPad, sdl2.SDL_CONTROLLER_BUTTON_B, True)))
					
				# loop through each joystick that is connected and save to button config file
				# note: max of 4 control pads for this emulator
				joystickTotal = sdl2.joystick.SDL_NumJoysticks()
				if joystickTotal > 0:
					counter = 1
					for i in xrange(joystickTotal):
						if sdl2.SDL_IsGameController(i):
							c = sdl2.SDL_GameControllerOpen(i)
							if sdl2.SDL_GameControllerGetAttached(c):
								j = sdl2.SDL_GameControllerGetJoystick(c)
								jsName = sdl2.SDL_JoystickName(j)
								logging.debug("PESApp.playGame: generating Mupen64Plus config for joystick %d: %s" % (i, jsName))
								section = 'Input-SDL-Control%d' % (i + 1)
								if configParser.has_section(section):
									configParser.set(section, 'device', "%d" % i)
									configParser.set(section, 'name', '"%s"' % jsName)
									configParser.set(section, 'plugged', 'True')
									configParser.set(section, 'mouse', 'False')
									configParser.set(section, 'mode', '0') # this must be set to 0 for the following values to take effect
									configParser.set(section, 'DPad R', self.getMupen64PlusConfigButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT))
									configParser.set(section, 'DPad L', self.getMupen64PlusConfigButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT))
									configParser.set(section, 'DPad D', self.getMupen64PlusConfigButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN))
									configParser.set(section, 'DPad U', self.getMupen64PlusConfigButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP))
									configParser.set(section, 'Start', self.getMupen64PlusConfigButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_START))
									configParser.set(section, 'Z Trig', self.getMupen64PlusConfigButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER))
									configParser.set(section, 'B Button', self.getMupen64PlusConfigButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_B))
									configParser.set(section, 'A Button', self.getMupen64PlusConfigButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_A))
									configParser.set(section, 'C Button R', self.getMupen64PlusConfigAxisValue(c, sdl2.SDL_CONTROLLER_AXIS_RIGHTX, positive=True))
									configParser.set(section, 'C Button L', self.getMupen64PlusConfigAxisValue(c, sdl2.SDL_CONTROLLER_AXIS_RIGHTX, positive=False))
									configParser.set(section, 'C Button D', self.getMupen64PlusConfigAxisValue(c, sdl2.SDL_CONTROLLER_AXIS_RIGHTY, positive=True))
									configParser.set(section, 'C Button U', self.getMupen64PlusConfigAxisValue(c, sdl2.SDL_CONTROLLER_AXIS_RIGHTY, positive=False))
									configParser.set(section, 'L Trig', self.getMupen64PlusConfigAxisValue(c, sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT))
									configParser.set(section, 'R Trig', self.getMupen64PlusConfigAxisValue(c, sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT))
									configParser.set(section, 'X Axis', self.getMupen64PlusConfigAxisValue(c, sdl2.SDL_CONTROLLER_AXIS_LEFTX, both=True))
									configParser.set(section, 'Y Axis', self.getMupen64PlusConfigAxisValue(c, sdl2.SDL_CONTROLLER_AXIS_LEFTY, both=True))
							sdl2.SDL_GameControllerClose(c)
						counter += 1
						if counter == 4:
							break
				
				logging.debug("PESApp.playGame: writing Mupen64Plus config to %s" % userMupen64PlusConfFile)
				with open(userMupen64PlusConfFile, 'wb') as f:
					configParser.write(f)
				
				widthRe = re.compile("((window|framebuffer)[ ]+width[ ]*)=[ ]*[0-9]+")
				heightRe = re.compile("((window|framebuffer)[ ]+height[ ]*)=[ ]*[0-9]+")
				# now update gles2n64.conf file to use current resolution
				output = ""
				with open(userGles2n64ConfFile, 'r') as f:
					for line in f:
						result = re.sub(widthRe, r"\1=%d" % self.__dimensions[0], line)
						if result != line:
							output += result
						else:
							result = re.sub(heightRe, r"\1=%d" % self.__dimensions[1], line)
							if result != line:
								output += result
							else:
								output += line
				logging.debug("PESApp.playGame: writing gles2n64 config to %s" % userGles2n64ConfFile)
				with open(userGles2n64ConfFile, 'w') as f:
					f.write(output)
		elif emulator == "vice":
			joystickTotal = sdl2.joystick.SDL_NumJoysticks()
			if joystickTotal > 0:
				logging.debug("PESApp.playGame: creating SDL joystick mapping %s" % userViceJoystickConfFile)
				with open(userViceJoystickConfFile, 'w') as f:
					f.write("# THIS FILE IS AUTOMATICALLY GENERATED BY PES!\n")
					f.write("!CLEAR\n")
					for i in xrange(joystickTotal):
						if sdl2.SDL_IsGameController(i):
							c = sdl2.SDL_GameControllerOpen(i)
							if sdl2.SDL_GameControllerGetAttached(c):
								j = sdl2.SDL_GameControllerGetJoystick(c)
								jsName = sdl2.SDL_JoystickName(j)
								f.write("# %s\n" % jsName)
								# joynum inputtype inputindex action
								f.write(self.getViceButtonValue(c, i, sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT, 8))
								f.write(self.getViceButtonValue(c, i, sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT, 4))
								f.write(self.getViceButtonValue(c, i, sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP, 1))
								f.write(self.getViceButtonValue(c, i, sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN, 2))
								f.write(self.getViceButtonValue(c, i, sdl2.SDL_CONTROLLER_BUTTON_A, 16))
								f.write(self.getViceButtonValue(c, i, sdl2.SDL_CONTROLLER_BUTTON_BACK, -4))
								f.write(self.getViceButtonValue(c, i, sdl2.SDL_CONTROLLER_BUTTON_GUIDE, -4))
								
								#if r != None:
								#	f.write("%d 1 %d 1 0 8\n" % (i, r))
								#r = self.getViceButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT)
								#if r != None:
								#	f.write("%d 1 %d 1 0 4\n" % (i, r))
								#r = self.getViceButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP)
								#if r != None:
								#	f.write("%d 1 %d 1 0 1\n" % (i, r))
								#r = self.getViceButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN)
								#if r != None:
								#	f.write("%d 1 %d 1 0 2\n" % (i, r))
								#r = self.getViceButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_A)
								#if r != None:
								#	f.write("%d 1 %d 1 0 16\n" % (i, r))
								#r = self.getViceButtonValue(c, sdl2.SDL_CONTROLLER_BUTTON_GUIDE)
								#if r != None:
								#	f.write("%d 1 %d 4" % (i, r))
					
		
		logging.info("loading game: %s" % game.getName())
		game.setPlayCount()
		game.setLastPlayed()
		game.save()
		launchString = game.getCommand()
		logging.debug("PESApp.playGame: launch string: %s" % launchString)
		self.runCommand(launchString)
	
	def processCecEvent(self, btn, dur):
		if dur > 0:
			logging.debug("PESApp.processCecEvent")
			e = mapRemoteButtonEvent(btn)
			if e:
				sdl2.SDL_PushEvent(e)
	
	def reboot(self, confirm=True):
		if confirm:
			self.showMessageBox("Are you sure?", self.reboot, False)
		else:
			logging.info("PES is rebooting...")
			self.runCommand(self.__rebootCommand)
			
	def reload(self, confirm=True):
		if confirm:
			self.showMessageBox("Are you sure?", self.reload, False)
		else:
			logging.info("PES is reloading...")
			self.runCommand("sleep 1")
		
	def resetConfig(self, confirm=True):
		if confirm:
			self.showMessageBox("Are you sure?", self.resetConfig, False)
		else:
			logging.info("PES is resetting its config...")
			for root, dirs, files in os.walk(userConfDir, topdown=False):
				for name in files:
					path = os.path.join(root, name)
					logging.debug("PESApp.resetConfig: deleting file %s" % path)
					os.remove(path)
				for name in dirs:
					path = os.path.join(root, name)
					logging.debug("PESApp.resetConfig: deleting directory %s" % path)
					os.rmdir(path)
			self.runCommand("sleep 1")
		
	def resetDatabase(self, confirm=True):
		if confirm:
			self.showMessageBox("Are you sure?", self.resetDatabase, False)
		else:
			logging.info("PES is resetting its database...")
			logging.debug("PESApp.resetDatabase: deleting %s" % userPesDb)
			os.remove(userPesDb)
			self.runCommand("sleep 1")
        
	def run(self):
		if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_GAMECONTROLLER) != 0:
			pesExit("Failed to inialise SDL!", True)
		sdl2.SDL_ShowCursor(0)
		sdl2.sdlttf.TTF_Init()
		imgFlags = sdl2.sdlimage.IMG_INIT_JPG | sdl2.sdlimage.IMG_INIT_PNG
		initted = sdl2.sdlimage.IMG_Init(imgFlags)
		if initted != imgFlags:
			pesExit("Failed to inialise SDL_Image!", True)
		videoMode = sdl2.video.SDL_DisplayMode()
		if sdl2.video.SDL_GetDesktopDisplayMode(0, videoMode) != 0:
			pesExit("PESApp.run: unable to get current video mode!")
			
		logging.debug("PESApp.run: video mode (%d, %d), refresh rate: %dHz" % (videoMode.w, videoMode.h, videoMode.refresh_rate))
		
		# register PES event type
		if pes.event.registerPesEventType():
			logging.debug("PESApp.run: PES event type registered in SDL2: %s" % pes.event.EVENT_TYPE)
		else:
			logging.error("PESApp.run: could not register PES event type in SDL2!")
			self.exit(1)
		
		if self.__dimensions[0] == 0 or self.__dimensions == 0:
			# assume full screen
			logging.debug("PESApp.run: running fullscreen")
			self.__dimensions = (videoMode.w, videoMode.h)
			self.__window = sdl2.video.SDL_CreateWindow('PES', sdl2.video.SDL_WINDOWPOS_UNDEFINED, sdl2.video.SDL_WINDOWPOS_UNDEFINED, self.__dimensions[0], self.__dimensions[1], sdl2.video.SDL_WINDOW_FULLSCREEN_DESKTOP)
		else:
			# windowed
			logging.debug("PESApp.run: running windowed")
			self.__window = sdl2.video.SDL_CreateWindow('PES', sdl2.video.SDL_WINDOWPOS_UNDEFINED, sdl2.video.SDL_WINDOWPOS_UNDEFINED, self.__dimensions[0], self.__dimensions[1], 0)
		
		self.menuWidth = 200
		self.menuHeight = self.__dimensions[1] - self.__footerHeight - self.__headerHeight
		
		self.menuRect = [0, self.__headerHeight + 1, self.menuWidth, self.__dimensions[1] - self.__headerHeight + 1]
		self.screenRect = [self.menuWidth + 1, self.__headerHeight + 1, self.__dimensions[0] - self.menuWidth + 1, self.__dimensions[1] - self.__headerHeight + 1]
		
		logging.debug("PESApp.run: window dimensions: (%d, %d)" % (self.__dimensions[0], self.__dimensions[1]))
		
		self.splashFont = sdl2.sdlttf.TTF_OpenFont(self.fontFile, self.__fontSizes['splash'])
		self.menuFont = sdl2.sdlttf.TTF_OpenFont(self.fontFile, self.__fontSizes['menu'])
		self.headerFont = sdl2.sdlttf.TTF_OpenFont(self.fontFile, self.__fontSizes['header'])
		self.titleFont = sdl2.sdlttf.TTF_OpenFont(self.fontFile, self.__fontSizes['title'])
		self.bodyFont = sdl2.sdlttf.TTF_OpenFont(self.fontFile, self.__fontSizes['body'])
		self.smallBodyFont = sdl2.sdlttf.TTF_OpenFont(self.fontFile, self.__fontSizes['smallBody'])
		
		self.renderer = sdl2.SDL_CreateRenderer(self.__window, -1, sdl2.render.SDL_RENDERER_ACCELERATED)
		
		# pre-initialise screens
		self.screens = {}
		
		headerLabel = Label(self.renderer, 5, 0, "Pi Entertainment System", self.headerFont, self.textColour)
		self.__uiObjects.append(headerLabel)
		dateLabel = Label(self.renderer, 0, 0, "00:00:00 00/00/0000", self.headerFont, self.textColour)
		dateLabel.x = self.__dimensions[0] - dateLabel.width - 5
		self.__uiObjects.append(dateLabel)

		splashLabel = Label(self.renderer, 0, 0, "Pi Entertainment System", self.splashFont, self.textColour)
		splashLabel.x = int((self.__dimensions[0] - splashLabel.width) / 2)
		splashLabel.y = ((self.__dimensions[1]) / 2) - splashLabel.height
		
		running = True
		loading = True
		
		lastTick = sdl2.timer.SDL_GetTicks()
		splashTextureAlpha = 25
		progressBarWidth = splashLabel.width
		progressBarHeight = 40
		progressBarX = splashLabel.x
		progressBarY = splashLabel.y + splashLabel.height + 20
		loadingThread = PESLoadingThread(self)
		progressBar = ProgressBar(self.renderer, progressBarX, progressBarY, progressBarWidth, progressBarHeight, self.lineColour, self.menuBackgroundColour)
		statusLabel = Label(self.renderer, 0, 0, loadingThread.status, self.bodyFont, self.textColour)
		statusLabel.x = int((self.__dimensions[0] - statusLabel.width) / 2)
		statusLabel.y = progressBarY + progressBarHeight + 2
		
		# load joystick database
		sdl2.SDL_GameControllerAddMappingsFromFile(userGameControllerFile)
		
		self.__gamepadIcon = Icon(self.renderer, dateLabel.x, dateLabel.y, self.__ICON_WIDTH, self.__ICON_HEIGHT, gamepadImageFile, False)
		self.__gamepadIcon.setVisible(False)
		
		self.__remoteIcon = Icon(self.renderer, dateLabel.x, dateLabel.y, self.__ICON_WIDTH, self.__ICON_HEIGHT, remoteImageFile, False)
		self.__remoteIcon.setVisible(self.__cecEnabled)
		
		self.__networkIcon = Icon(self.renderer, dateLabel.x - 42, dateLabel.y, self.__ICON_WIDTH, self.__ICON_HEIGHT, networkImageFile, False)
		self.ip = None
		defaultInterface = getDefaultInterface()
		if defaultInterface:
			self.ip = getIPAddress(defaultInterface)
			logging.debug("PESApp.run: default interface: %s, IP address: %s" % (defaultInterface, self.ip))
		else:
			logging.warning("PESApp.run: default network interface not found!")
			self.__networkIcon.setVisible(False)
			
		self.__msgBox = None
		
		self.__controlPad = None
		self.__controlPadIndex = None
		self.__dpadAsAxis = False
		joystickTick = sdl2.timer.SDL_GetTicks()
		downTick = joystickTick
		screenSaverTick = joystickTick
		screenSaverActive = False
		self.__screenSaverLabel = None
		
		while running:
			
			if self.__screenSaverTimeout > 0 and not screenSaverActive and sdl2.timer.SDL_GetTicks() - screenSaverTick  > self.__screenSaverTimeout * 60000: # milliseconds per minute
				logging.debug("PESApp.run: activating screen saver")
				screenSaverActive = True
				screenSaverLastTick = screenSaverTick
				if self.__screenSaverLabel == None:
					self.__screenSaverLabel = Label(self.renderer, 0, 0, "Pi Entertainment System", self.splashFont, self.textColour)
				self.__screenSaverLabel.setCoords(random.randint(0, self.__dimensions[0] - self.__screenSaverLabel.width), random.randint(0, self.__dimensions[1] - self.__screenSaverLabel.height))
			
			events = sdl2.ext.get_events()
			for event in events:
				if self.doJsToKeyEvents:
					if (event.type == sdl2.SDL_CONTROLLERBUTTONDOWN or event.type == sdl2.SDL_CONTROLLERBUTTONUP) and self.__controlPad and event.cbutton.which == self.__controlPadIndex and (not self.__dpadAsAxis or (self.__dpadAsAxis and event.cbutton.button != sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP and event.cbutton.button != sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN and event.cbutton.button != sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT and event.cbutton.button != sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT)):
						if event.type == sdl2.SDL_CONTROLLERBUTTONDOWN:
							logging.debug("PESApp.run: player 1 button \"%s\" pressed" % sdl2.SDL_GameControllerGetStringForButton(event.cbutton.button))
							downTick = sdl2.timer.SDL_GetTicks() + (self.__CONTROL_PAD_BUTTON_REPEAT * 2)
							e = mapControlPadButtonEvent(event, sdl2.SDL_KEYDOWN)
							if e:
								sdl2.SDL_PushEvent(e)
						elif event.type == sdl2.SDL_CONTROLLERBUTTONUP:
							e = mapControlPadButtonEvent(event, sdl2.SDL_KEYUP)
							if e:
								sdl2.SDL_PushEvent(e)
					elif event.type == sdl2.SDL_CONTROLLERAXISMOTION and self.__controlPad and event.cbutton.which == self.__controlPadIndex:
						if event.caxis.value < JOYSTICK_AXIS_MIN or event.caxis.value > JOYSTICK_AXIS_MAX:
							logging.debug("PESApp.run: player 1 axis \"%s\" activated" % sdl2.SDL_GameControllerGetStringForAxis(event.caxis.axis))
							downTick = sdl2.timer.SDL_GetTicks() + (self.__CONTROL_PAD_BUTTON_REPEAT * 2)
							e = mapControlPadAxisEvent(event, sdl2.SDL_KEYDOWN)
							if e:
								sdl2.SDL_PushEvent(e)
						else:
							e = mapControlPadAxisEvent(event, sdl2.SDL_KEYUP)
							if e:
								sdl2.SDL_PushEvent(e)
					elif event.type == sdl2.SDL_JOYAXISMOTION and self.__controlPad and self.__controlPadIndex == event.jaxis.which:
						if self.__dpadAsAxis:
							# and so begins some really horrible code to work around the SDL2 game controller API mapping axis to dpad buttons
							for b in [sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN, sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT]:
								bind = sdl2.SDL_GameControllerGetBindForButton(c, b)
								if bind:
									if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_AXIS:
										if bind.value.axis == event.jaxis.axis:
											btn = b
											if event.jaxis.value < JOYSTICK_AXIS_MIN:
												if b == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
													btn = sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP
												else:
													btn = sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT
											key = mapButtonToKey(btn)
											if event.jaxis.value < JOYSTICK_AXIS_MIN or event.jaxis.value > JOYSTICK_AXIS_MAX:
												downTick = sdl2.timer.SDL_GetTicks() + (self.__CONTROL_PAD_BUTTON_REPEAT * 2)
												if key:
													e = sdl2.SDL_Event()
													e.type = sdl2.SDL_KEYDOWN
													e.key.keysym.sym = key
													sdl2.SDL_PushEvent(e)
											else:
												if key:
													e = sdl2.SDL_Event()
													e.type = sdl2.SDL_KEYUP
													e.key.keysym.sym = key
													sdl2.SDL_PushEvent(e)
											break
										
				if event.type == pes.event.EVENT_TYPE:
					(t, d1, d2) = pes.event.decodePesEvent(event)
					logging.debug("PESApp.run: trapping PES Event")
					if not loading and t == pes.event.EVENT_DB_UPDATE:
						self.initSurfaces(True) # calls refresh method of all consoles
						for c in self.consoles:
							screenName = "Console %s" % c.getName()
							if c.getGameTotal() > 0:
								if screenName in self.screens:
									self.screens[screenName].refresh()
								else:
									logging.debug("PESApp.run adding ConsoleScreen for %s following database update" % c.getName())
									self.screens[screenName] = ConsoleScreen(self, self.renderer, self.menuRect, self.screenRect, c)
								
						self.screens["Home"].refreshMenu()
						Thumbnail.destroyTextures()
						
						if screenSaverActive:
							screenSaverActive = False
							screenSaverTick = sdl2.timer.SDL_GetTicks()
					elif not loading and t == pes.event.EVENT_ACHIEVEMENTS_UPDATE:
						logging.debug("PESApp.run: achievements have been updated")
						self.setUpRetroAchievementUser()
						self.screens["Home"].updateRecentBadges()
					#elif t == pes.event.EVENT_RESOURCES_LOADED:
					#	pass
					

				if screenSaverActive:
					if event.type == sdl2.SDL_KEYDOWN:
						screenSaverActive = False
						screenSaverTick = sdl2.timer.SDL_GetTicks()
				else:
					if not loading:
						# keyboard events
						if event.type == sdl2.SDL_KEYDOWN:
							screenSaverTick = sdl2.timer.SDL_GetTicks()
							if event.key.keysym.sym == sdl2.SDLK_BACKSPACE:
								logging.debug("PESApp.run: trapping backspace key event")
								if self.__msgBox and self.__msgBox.isVisible():
									self.__msgBox.setVisible(False)
								if self.screens[self.screenStack[-1]].menuActive:
									# pop the screen
									screenStackLen = len(self.screenStack)
									logging.debug("PESApp.run: popping screen stack, current length: %d" % screenStackLen)
									if screenStackLen > 1:
										self.screenStack.pop()
										self.setScreen(self.screenStack[-1], False)
								else:
									self.screens[self.screenStack[-1]].setMenuActive(True)
							elif event.key.keysym.sym == sdl2.SDLK_HOME:
								logging.debug("PESApp.run: trapping home key event")
								if self.__msgBox and self.__msgBox.isVisible():
									self.__msgBox.setVisible(False)
								# pop all screens and return home
								if not self.screens[self.screenStack[-1]].isBusy():
									while len(self.screenStack) > 1:
										s = self.screenStack.pop()
										self.screens[s].setMenuActive(False)
										self.screens[s].processEvent(event)
									self.setScreen("Home", False)
									self.screens["Home"].setMenuActive(True)
									self.screens["Home"].menu.setSelected(0)
									self.screens["Home"].update()
							if self.__msgBox and self.__msgBox.isVisible():
								self.__msgBox.processEvent(event)
							else:
								self.screens[self.screenStack[-1]].processEvent(event)
						elif event.type == sdl2.SDL_KEYUP or event.type == sdl2.SDL_JOYBUTTONUP or event.type == sdl2.SDL_JOYAXISMOTION or event.type == sdl2.SDL_JOYHATMOTION:
							self.screens[self.screenStack[-1]].processEvent(event)
								
				if event.type == sdl2.SDL_KEYDOWN and event.key.keysym.sym == sdl2.SDLK_ESCAPE:
					logging.debug("PESApp.run: trapping escape key event")
					running = False
					break
					
				# joystick events
				if event.type == sdl2.SDL_QUIT:
					running = False
					break
			
			if loading:
				sdl2.SDL_SetRenderDrawColor(self.renderer, self.backgroundColour.r, self.backgroundColour.g, self.backgroundColour.b, 255)
				sdl2.SDL_RenderClear(self.renderer)
				if not loadingThread.started:
					loadingThread.start()
				joystickTick = sdl2.timer.SDL_GetTicks()
				if splashTextureAlpha < 255 and joystickTick - lastTick > 100:
					splashTextureAlpha += 25
					if splashTextureAlpha > 255:
						splashTextureAlpha = 255
					lastTick = joystickTick
				splashLabel.setAlpha(splashTextureAlpha)
				splashLabel.draw()
				if loadingThread.done and splashTextureAlpha >= 255:
					loading = False
					splashLabel.destroy()
					statusLabel.destroy()
					self.screens["Home"].loadTextures()
				else:
					progressBar.setProgress(loadingThread.progress)
					progressBar.draw()
					if statusLabel.setText(loadingThread.status):
						statusLabel.x = int((self.__dimensions[0] - statusLabel.width) / 2)
					statusLabel.draw()
			elif screenSaverActive:
				sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 0, 0, 255)
				sdl2.SDL_RenderClear(self.renderer)
				# x, y, text, font, colour, bgColour=None, fixedWidth=0, fixedHeight=0, autoScroll=False, bgAlpha=255
				if sdl2.SDL_GetTicks() - screenSaverLastTick > 10000: # move label every 10s
					logging.debug("PESApp.run: moving screen saver label")
					screenSaverLastTick = sdl2.SDL_GetTicks()
					self.__screenSaverLabel.setCoords(random.randint(0, self.__dimensions[0] - self.__screenSaverLabel.width), random.randint(0, self.__dimensions[1] - self.__screenSaverLabel.height))
				self.__screenSaverLabel.draw()
			else:
				sdl2.SDL_SetRenderDrawColor(self.renderer, self.backgroundColour.r, self.backgroundColour.g, self.backgroundColour.b, 255)
				sdl2.SDL_RenderClear(self.renderer)
				sdl2.sdlgfx.boxRGBA(self.renderer, 0, 0, self.__dimensions[0], self.__headerHeight, self.headerBackgroundColour.r, self.headerBackgroundColour.g, self.headerBackgroundColour.b, 255) # header bg
				headerLabel.draw()
				
				self.screens[self.screenStack[-1]].draw()
			
				now = datetime.now()
				dateLabel.setText(now.strftime("%H:%M:%S %d/%m/%Y"))
				dateLabel.draw()
				
				iconX = dateLabel.x - 42
				
				if self.__networkIcon.visible:
					self.__networkIcon.x = iconX
					self.__networkIcon.draw()
					iconX -= 37
					
				if self.__gamepadIcon.visible:
					self.__gamepadIcon.x = iconX
					self.__gamepadIcon.draw()
					iconX -= 37
					
				if self.__remoteIcon.visible:
					self.__remoteIcon.x = iconX
					self.__remoteIcon.draw()
				
				sdl2.sdlgfx.rectangleRGBA(self.renderer, 0, self.__headerHeight, self.__dimensions[0], self.__headerHeight, self.lineColour.r, self.lineColour.g, self.lineColour.b, 255) # header line
			
			if not loading:
				# detect joysticks
				if self.__controlPad and not sdl2.SDL_GameControllerGetAttached(self.__controlPad):
					logging.debug("PESApp.run: player 1 control pad no longer attached!")
					sdl2.SDL_GameControllerClose(self.__controlPad)
					self.__controlPad = None
					self.__controlPadIndex = None
					self.__gamepadIcon.setVisible(False)
				elif self.doJsToKeyEvents:
					# is the user holding down a button?
					# note: we only care about directional buttons
					if self.__dpadAsAxis:
						bind = sdl2.SDL_GameControllerGetBindForButton(self.__controlPad, sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN)
						if bind and bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_AXIS:
							js = sdl2.SDL_GameControllerGetJoystick(self.__controlPad)
							axisValue = sdl2.SDL_JoystickGetAxis(js, bind.value.axis)
							if axisValue < JOYSTICK_AXIS_MIN or axisValue > JOYSTICK_AXIS_MAX:
								if sdl2.timer.SDL_GetTicks() - downTick > self.__CONTROL_PAD_BUTTON_REPEAT:
									downTick = sdl2.timer.SDL_GetTicks()
									btn = sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN
									if axisValue < JOYSTICK_AXIS_MIN:
										btn = sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP
									key = mapButtonToKey(btn)
									if key:
										e = sdl2.SDL_Event()
										e.type = sdl2.SDL_KEYDOWN
										e.key.keysym.sym = key
										sdl2.SDL_PushEvent(e)
					else:
						for b in [sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN, sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP]:
							if sdl2.SDL_GameControllerGetButton(self.__controlPad, b):
								if sdl2.timer.SDL_GetTicks() - downTick > self.__CONTROL_PAD_BUTTON_REPEAT:
									downTick = sdl2.timer.SDL_GetTicks()
									key = mapButtonToKey(b)
									if key:
										e = sdl2.SDL_Event()
										e.type = sdl2.SDL_KEYDOWN
										e.key.keysym.sym = key
										sdl2.SDL_PushEvent(e)
					
					# is the user holding down an axis?
					# note: at the moment we only care about the left axis in the Y plane
					for a in [sdl2.SDL_CONTROLLER_AXIS_LEFTY]:
						value = sdl2.SDL_GameControllerGetAxis(self.__controlPad, a)
						if value < JOYSTICK_AXIS_MIN or value > JOYSTICK_AXIS_MAX:
							if sdl2.timer.SDL_GetTicks() - downTick > self.__CONTROL_PAD_BUTTON_REPEAT:
								downTick = sdl2.timer.SDL_GetTicks()
								key = mapAxisToKey(a, value)
								if key:
									e = sdl2.SDL_Event()
									e.type = sdl2.SDL_KEYDOWN
									e.key.keysym.sym = key
									sdl2.SDL_PushEvent(e)
				
				if sdl2.timer.SDL_GetTicks() - joystickTick > 1000:
					tick = sdl2.timer.SDL_GetTicks()
					joystickTotal = sdl2.joystick.SDL_NumJoysticks()
					if joystickTotal > 0:
						#logging.debug("PESApp.run: found %d control pads" % joystickTotal)
						for i in xrange(joystickTotal):
							if sdl2.SDL_IsGameController(i):
								close = True
								c = sdl2.SDL_GameControllerOpen(i)
								if sdl2.SDL_GameControllerGetAttached(c):
									#logging.debug("PESApp.run: %s is attached at %d" % (sdl2.SDL_GameControllerNameForIndex(i), i))
									if self.__controlPad == None:
										logging.debug("PESApp.run: switching player 1 to control pad #%d: %s (%s)" % (i, sdl2.SDL_GameControllerNameForIndex(i), getJoystickGUIDString(sdl2.SDL_JoystickGetDeviceGUID(i))))
										self.__controlPadIndex = i
										self.__controlPad = c
										self.updateControlPad(self.__controlPadIndex)
										close = False
										self.__gamepadIcon.setVisible(True)
										if screenSaverActive:
											screenSaverActive = False
											screenSaverTick = sdl2.timer.SDL_GetTicks()
										#print sdl2.SDL_GameControllerMapping(c)
								if close:
									sdl2.SDL_GameControllerClose(c)
									
			if self.__msgBox and self.__msgBox.isVisible():
				self.__msgBox.draw()
			
			sdl2.SDL_RenderPresent(self.renderer)
			
		self.exit(0)
		
	def runCommand(self, command):
		logging.debug("PESApp.runCommand: about to write to: %s" % scriptFile)
		logging.debug("PESApp.runCommand: command: %s" % command)
		execLog = os.path.join(userLogDir, "exec.log")
		with open(scriptFile, 'w') as f:
			f.write("echo running %s\n" % command)
			f.write("echo see %s for console output\n" % execLog)
			f.write("%s &> %s\n" % (command, execLog))
			f.write("exec %s %s\n" % (os.path.join(baseDir, 'bin', 'pes') , ' '.join(sys.argv[1:])))
		self.exit(0)
		
	def setCecEnabled(self, enabled):
		self.__cecEnabled = enabled
		
	def setScreen(self, screen, doAppend=True):
		if not screen in self.screens:
			logging.warning("PESApp.setScreen: invalid screen selection \"%s\"" % screen)
		else:
			logging.debug("PESApp.setScreen: setting current screen to \"%s\"" % screen)
			logging.debug("PESApp.setScreen: adding screen \"%s\" to screen stack" % screen)
			if doAppend:
				self.screenStack.append(screen)
			self.screens[screen].setMenuActive(True)
		
	def setUpRetroAchievementUser(self):
		if self.retroAchievementConn:
			if self.achievementUser:
				logging.debug("PESApp.setUpRetroAchievementUser: refreshing user object...")
				self.achievementUser.refresh()
			else:
				logging.debug("PESApp.setUpRetroAchievementUser: setting up user object...")
				# look up user in database
				con = None
				try:
					con = sqlite3.connect(userPesDb)
					con.row_factory = sqlite3.Row
					cur = con.cursor()
					cur.execute("SELECT `user_id` FROM `achievements_user` WHERE `user_name` = '%s';" % self.retroAchievementConn.getUsername().replace("'", "''"))
					row = cur.fetchone()
					if row:
						self.achievementUser = AchievementUser(userPesDb, row['user_id'])
				except sqlite3.Error, e:
					logging.error(e)
					if con:
						con.rollback()
					self.__endTime = time.time()
					self.__success = False
					return
				finally:
					if con:
						con.close()
			
	def showMessageBox(self, text, callback, *callbackArgs):
		if self.__msgBox:
			self.__msgBox.destroy()
		self.__msgBox = MessageBox(self.renderer, text, self.bodyFont, self.textColour, self.menuBackgroundColour, self.lineColour, callback, *callbackArgs)
		self.__msgBox.setVisible(True)
			
	def shutdown(self, confirm=True):
		if confirm:
			self.showMessageBox("Are you sure?", self.shutdown, False)
		else:
			logging.info("PES is shutting down...")
			self.runCommand(self.__shutdownCommand)
			
	def updateControlPad(self, jsIndex):
		if jsIndex == self.__controlPadIndex:
			# hack for instances where a dpad is an axis
			bind = sdl2.SDL_GameControllerGetBindForButton(self.__controlPad, sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP)
			if bind:			
				if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_AXIS:
					self.__dpadAsAxis = True
					logging.debug("PESApp.run: enabling dpad as axis hack")
				else:
					self.__dpadAsAxis = False
			
class PESLoadingThread(threading.Thread):
	def __init__(self, app):
		super(PESLoadingThread, self).__init__()
		self.app = app
		self.progress = 0
		self.started = False
		self.done = False
		self.status = "Initialising"
		
	def run(self):
		self.started = True
		
		# create database (if needed)
		con = None
		logging.debug('PESLoadingThread.run: connecting to database: %s' % userPesDb)
		try:
			self.status = "Checking database..."
			con = sqlite3.connect(userPesDb)
			con.row_factory = sqlite3.Row
			cur = con.cursor()
			cur.execute('CREATE TABLE IF NOT EXISTS `games`(`game_id` INTEGER PRIMARY KEY, `thegamesdb_id` INT, `exists` INT, `console_id` INT, `name` TEXT, `cover_art` TEXT, `game_path` TEXT, `overview` TEXT, `released` INT, `last_played` INT, `added` INT, `favourite` INT(1), `play_count` INT, `size` INT, `rasum` TEXT, `achievement_api_id` INT )')
			cur.execute('CREATE INDEX IF NOT EXISTS "games_index" on games (game_id ASC)')
			cur.execute('CREATE TABLE IF NOT EXISTS `consoles`(`console_id` INTEGER PRIMARY KEY, `thegamesdb_api_id` INT, `achievement_api_id` INT, `name` TEXT)')
			cur.execute('CREATE INDEX IF NOT EXISTS "console_index" on consoles (console_id ASC)')
			cur.execute('CREATE INDEX IF NOT EXISTS "console_achievement_index" on consoles (achievement_api_id ASC)')
			cur.execute('CREATE INDEX IF NOT EXISTS "console_thegamesdb_index" on consoles (thegamesdb_api_id ASC)')
			cur.execute('CREATE TABLE IF NOT EXISTS `games_catalogue` (`short_name` TEXT, `full_name` TEXT)')
			cur.execute('CREATE INDEX IF NOT EXISTS "games_catalogue_index" on games_catalogue (short_name ASC)')
			cur.execute('CREATE TABLE IF NOT EXISTS `achievements_user`(`user_id` INTEGER PRIMARY KEY, `user_name` TEXT, `rank` INT, `total_points` INT, `total_truepoints` INT)')
			cur.execute('CREATE INDEX IF NOT EXISTS "achievements_user_index" on achievements_user (user_id ASC)')
			cur.execute('CREATE TABLE IF NOT EXISTS `achievements_games`(`game_id` INTEGER PRIMARY KEY, `console_id` INT, `achievement_total` INT, `score_total` INT)')
			cur.execute('CREATE INDEX IF NOT EXISTS "achievements_game_index" on achievements_games (game_id ASC)')
			cur.execute('CREATE TABLE IF NOT EXISTS `achievements_badges`(`badge_id` INTEGER PRIMARY KEY, `title` TEXT, `game_id` INT, `description` TEXT, `points` INT, `badge_path` TEXT, `badge_locked_path` TEXT)')
			cur.execute('CREATE INDEX IF NOT EXISTS "achievements_badge_index" on achievements_badges (badge_id ASC)')
			cur.execute('CREATE TABLE IF NOT EXISTS `achievements_earned`(`user_id` INT, `badge_id` INT, `date_earned` INT, PRIMARY KEY (user_id, badge_id))')
			cur.execute('CREATE INDEX IF NOT EXISTS "achievements_earned_index" on achievements_earned (user_id ASC, badge_id ASC)')
			
			self.progress = 16
			
			# is the games catalogue populated?
			cur.execute('SELECT COUNT(*) AS `total` FROM `games_catalogue`')
			row = cur.fetchone()
			if row['total'] == 0:
				self.status = "Populating games catalogue..."
				logging.info("PESLoadingThread.run: populating games catalogue using file: %s" % userGamesCatalogueFile)
				catalogueConfigParser = ConfigParser.ConfigParser()
				catalogueConfigParser.read(userGamesCatalogueFile)
				sections = catalogueConfigParser.sections()
				sectionTotal = float(len(sections))
				
				i = 0.0
				insertValues = []
				for section in sections:
					if catalogueConfigParser.has_option(section, 'full_name'):
						fullName = catalogueConfigParser.get(section, 'full_name')
						#logging.debug("PESLoadingThread.run: inserting game into catalogue: %s -> %s" % (section, fullName))
						#cur.execute('INSERT INTO `games_catalogue` (`short_name`, `full_name`) VALUES ("%s", "%s");' % (section, fullName))
						insertValues.append('("%s", "%s")' % (section, fullName))
					else:
						logging.error("PESLoadingThread.run: games catalogue section \"%s\" has no \"full_name\" option!" % section)
					i += 1.0
					self.progress = 16 + (16 * (i / sectionTotal))
				if len(insertValues) > 0:
					cur.execute('INSERT INTO `games_catalogue` (`short_name`, `full_name`) VALUES %s;' % ','.join(insertValues))
						
			con.commit()
		except sqlite3.Error, e:
			pesExit("Error: %s" % e.args[0], True)
		finally:
			if con:
				con.close()
				
		self.progress = 32
		self.status = "Loading consoles..."
		
		# load consoles
		configParser = ConfigParser.ConfigParser()
		configParser.read(userConsolesConfigFile)
		supportedConsoles = configParser.sections()
		supportedConsoleTotal = float(len(supportedConsoles))
		supportedConsoles.sort()
		i = 0
		for c in supportedConsoles:
			# check the console definition from the config file
			try:
				consolePath = self.app.romsDir + os.sep + c
				mkdir(consolePath)
				consoleCoverartDir = self.app.coverartDir + os.sep + c
				mkdir(consoleCoverartDir)
				extensions = configParser.get(c, 'extensions').split(' ')
				command = configParser.get(c, 'command').replace('%%BASE%%', baseDir)
				consoleImg = configParser.get(c, 'image').replace('%%BASE%%', baseDir)
				emulator = configParser.get(c, 'emulator')
				checkFile(consoleImg)
				nocoverart = configParser.get(c, 'nocoverart').replace('%%BASE%%', baseDir)
				checkFile(nocoverart)
				thegamesdbApiId = configParser.getint(c, 'thegamesdb_id')
				consoleId = None
				# have we already saved this console to the database?
				try:
					con = sqlite3.connect(userPesDb)
					con.row_factory = sqlite3.Row
					cur = con.cursor()
					cur.execute('SELECT `console_id` FROM `consoles` WHERE `name` = "%s";' % c)
					row = cur.fetchone()
					if row:
						consoleId = int(row['console_id'])
				except sqlite3.Error, e:
					pesExit("Error: %s" % e.args[0], True)
				finally:
					if con:
						con.close()
				
				console = Console(c, consoleId, thegamesdbApiId, extensions, consolePath, command, userPesDb, consoleImg, nocoverart, consoleCoverartDir, emulator)
				if configParser.has_option(c, 'ignore_roms'):
					for r in configParser.get(c, 'ignore_roms').split(','):
						console.addIgnoreRom(r.strip())
				if configParser.has_option(c, 'achievement_id'):
					console.setAchievementApiId(configParser.get(c, 'achievement_id'))
				if console.isNew():
					console.save()
				self.app.consoles.append(console)
				i += 1
				self.progress = 32 + (16 * (i / supportedConsoleTotal))
			except ConfigParser.NoOptionError as e:
				logging.error('PESLoadingThread.run: error parsing config file %s: %s' % (userConsolesConfigFile, e.message))
				self.done = True
				self.app.exit(1)
				return
			except ValueError as e:
				logging.error('PESLoadingThread.run: error parsing config file %s: %s' % (userConsolesConfigFile, e.message))
				self.done = True
				self.app.exit(1)
				return
		
		
		self.progress = 48
		self.status = "Loading timezone info..."
		process = Popen(self.app.listTimezonesCommand, stdout=PIPE, stderr=PIPE, shell=True)
		stdout, stderr = process.communicate()
		if process.returncode != 0:
			logging.error("PESLoadingThread.run: could not get time zones")
			logging.error(stderr)
		else:
			for l in stdout.split("\n")[:-1]:
				self.app.timezones.append(l)
			logging.debug("PESLoadingThread.run: loaded %d timezones" % len(self.app.timezones))
				
			process = Popen(self.app.getTimezoneCommand, stdout=PIPE, stderr=PIPE, shell=True)
			stdout, stderr = process.communicate()
			if process.returncode != 0:
				logging.error("PESLoadingThread.run: could not get current time zone!")
				logging.error(stderr)
			else:
				self.app.currentTimezone = stdout[:-1]
				logging.debug("PESLoadingThread.run: current timezone is: %s" % self.app.currentTimezone)
			
		self.progress = 64
		self.status = "Loading surfaces..."
		self.app.initSurfaces()
		self.progress = 80
		self.status = "Preparing screens..."
		self.app.initScreens()
		self.progress = 100
		self.status = "Complete!"
		time.sleep(0.1)
		pes.event.pushPesEvent(pes.event.EVENT_RESOURCES_LOADED)
		logging.debug("PESLoadingThread.run: %d complete" % self.progress)
		self.done = True
		return
		
class Screen(object):
	
	def __init__(self, app, renderer, title, menu, menuRect, screenRect):
		super(Screen, self).__init__()
		self.title = title
		self.app = app
		self.renderer = renderer
		self.menu = menu
		self.menuRect = menuRect
		self.screenRect = screenRect
		self.menuActive = True
		self.justActivated = False
		self.__menuMargin = 5
		self.__menuTopMargin = 10
		self.__menuItemChanged = False
		self.screenMargin = 10
		self.wrap = self.screenRect[2] - (self.screenMargin * 2)
		self.__uiObjects = []
		if self.menu:
			self.menu.setSelected(0)
			self.__menuList = self.addUiObject(List(self.renderer, self.__menuMargin + self.menuRect[0], self.menuRect[1] + self.__menuTopMargin, self.menuRect[2] - (self.__menuMargin * 2), self.menuRect[3] - (self.menuRect[1] + self.__menuTopMargin), self.menu, self.app.menuFont, self.app.menuTextColour, self.app.menuSelectedTextColour, self.app.menuSelectedBgColour, self.app.menuTextColour, List.SCROLLBAR_DISABLED, labelMargin=0))
			self.__menuList.setFocus(True)
		
	def addUiObject(self, o):
		if o not in self.__uiObjects:
			self.__uiObjects.append(o)
		return o
		
	def draw(self):
		if self.menu:
			self.drawMenu()
		self.drawScreen()
		
	def drawMenu(self):
		sdl2.sdlgfx.boxRGBA(self.renderer, self.menuRect[0], self.menuRect[1], self.menuRect[0] + self.menuRect[2], self.menuRect[1] + self.menuRect[3], self.app.menuBackgroundColour.r, self.app.menuBackgroundColour.g, self.app.menuBackgroundColour.b, 255)
		self.__menuList.draw()
	
	def drawScreen(self):
		sdl2.sdlgfx.boxRGBA(self.renderer, self.screenRect[0], self.screenRect[1], self.screenRect[0] + self.screenRect[2], self.screenRect[1] + self.screenRect[3], self.app.backgroundColour.r, self.app.backgroundColour.g, self.app.backgroundColour.b, 255)
		
	def isBusy(self):
		return False
	
	def processEvent(self, event):
		if self.menuActive and event.type == sdl2.SDL_KEYDOWN:
			if event.key.keysym.sym == sdl2.SDLK_RETURN or event.key.keysym.sym == sdl2.SDLK_KP_ENTER:
				self.menu.getSelectedItem().trigger()
				self.setMenuActive(False)
				self.__menuList.setFocus(False)
				self.justActivated = True
			else:
				self.justActivated = False
				self.__menuList.processEvent(event)
		elif not self.menuActive:
			self.justActivated = False
				
	def removeUiObject(self, o):
		if o in self.__uiObjects:
			self.__uiObjects.remove(o)
			
	def select(self, index):
		if self.menu:
			self.menu.setSelected(0, True)
	
	def setMenuActive(self, active):
		if self.menu:
			self.menuActive = active
			self.__menuList.setFocus(active)
			logging.debug("Screen.setMenuActive: \"%s\" activate state is now: %s" % (self.title, self.menuActive))
		
	def stop(self):
		uiObjectLen = len(self.__uiObjects)
		if uiObjectLen > 0:
			logging.debug("Screen.stop: Destroying %d UI objects..." % uiObjectLen)
			for o in self.__uiObjects:
				o.destroy()

class ConsoleScreen(Screen):
	
	def __init__(self, app, renderer, menuRect, screenRect, console):
		super(ConsoleScreen, self).__init__(app, renderer, console.getName(), Menu([
			MenuItem("Favourites"),
			MenuItem("Recently Played"),
			MenuItem("Most Played"),
			MenuItem("Recently Added"),
			MenuItem("Have Badges"),
			MenuItem("All")
		]),
		menuRect, screenRect)
		self.__console = console
		self.__consoleName = console.getName()
		self.menu.setSelected(0)
		self.__thumbXGap = 20
		self.__thumbYGap = 10
		self.__showThumbs = 10
		self.__desiredThumbWidth = int((screenRect[2] - (self.__showThumbs * self.__thumbXGap)) / self.__showThumbs)
		img = Image.open(console.getNoCoverArtImg())
		img.close()
		self.__noCoverArtWidth, self.__noCoverArtHeight = img.size
		self.__thumbRatio = float(self.__noCoverArtHeight) / float(self.__noCoverArtWidth)
		self.__thumbWidth = self.__desiredThumbWidth
		self.__thumbHeight = int(self.__thumbRatio * self.__thumbWidth)
		self.__consoleTexture = None
		self.__titleLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.screenRect[1], "%s: %s" % (self.__consoleName, self.menu.getSelectedItem().getText()),
 self.app.titleFont, self.app.textColour, fixedWidth=self.wrap))
		self.__noGamesFoundLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.__titleLabel.y + (self.__titleLabel.height * 2), "No games found.", self.app.bodyFont, self.app.textColour))
		self.__descriptionLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.__titleLabel.y + (self.__titleLabel.height * 2), " ", self.app.bodyFont, self.app.textColour, fixedWidth=self.wrap))
		self.__allGamesList = None
		self.__recentlyAddedGamesList = None
		self.__favouritesList = None
		self.__recentlyPlayedList = None
		self.__mostPlayedList = None
		self.__achievementsList = None
		self.__gameInfoLabel = None
		self.__gameOverviewLabel = None
		self.__previewThumbnail = None
		self.__listX = self.screenRect[0] + self.screenMargin
		self.__listY = self.__titleLabel.y + (self.__titleLabel.height * 2)
		self.__listWidth = 300
		self.__listHeight = self.screenRect[1] + self.screenRect[3] - self.__listY - self.screenMargin
		self.__previewThumbnailX = self.__listX + self.__listWidth
		self.__previewThumbnailWidth, self.__previewThumbnailHeight = scaleImage((self.__noCoverArtWidth, self.__noCoverArtHeight), (self.screenRect[0] + self.screenRect[2] - self.__previewThumbnailX - 50, int((self.screenRect[3] - self.screenRect[1]) / 2)))
		self.__previewThumbnailX += int((((self.screenRect[0] + self.screenRect[2]) - self.__previewThumbnailX) / 2) - (self.__previewThumbnailWidth / 2))
		self.__previewThumbnailY = self.__listY
		self.__gameInfoLabelX = self.__listX + self.__listWidth + 50
		self.__gameInfoLabelY = self.__previewThumbnailY + self.__previewThumbnailHeight + 10
		self.__gameInfoLabelWidth = self.screenRect[0] + self.screenRect[2] - self.__gameInfoLabelX - 5
		self.__gameInfoLabelHeight = 6 * sdl2.sdlttf.TTF_FontHeight(self.app.bodyFont)
		self.__gameInfoLabel = self.addUiObject(Label(self.renderer, self.__gameInfoLabelX, self.__gameInfoLabelY, " ", self.app.bodyFont, self.app.textColour, fixedWidth=self.__gameInfoLabelWidth,
 fixedHeight=self.__gameInfoLabelHeight, bgColour=self.app.menuTextColour, bgAlpha=50))
		self.__gameOverviewLabelX = self.__gameInfoLabelX
		self.__gameOverviewLabelY = self.__gameInfoLabelY + self.__gameInfoLabelHeight
		self.__gameOverviewLabel = self.addUiObject(Label(self.renderer, self.__gameInfoLabelX, self.__gameOverviewLabelY, " ", self.app.bodyFont, self.app.textColour, fixedWidth=self.__gameInfoLabelWidth, fixedHeight=(self.screenRect[1] + self.screenRect[3] - self.__gameOverviewLabelY - self.screenMargin), autoScroll=True, bgColour=self.app.menuTextColour, bgAlpha=50))
		self.__recentlyAddedThumbPanel = None
		self.__recentlyPlayedThumbPanel = None
		self.__mostPlayedThumbPanel = None
		self.__favouriteThumbPanel = None
		self.__achievementsThumbPanel = None
		self.__allGamesThumbPanel = None
		self.refreshNeeded = True
		#self.refresh()
		logging.debug("ConsoleScreen.init: initialised for %s" % self.__consoleName)
		
	def __createMenu(self, games):
		menu = Menu([])
		for g in games:
			m = GameMenuItem(g, False, True, self.__playGame, g)
			m.toggle(g.isFavourite())
			menu.addItem(m)
		return menu
		
	def __createPreviewThumbnail(self, game):
		if self.__previewThumbnail == None:
			self.__previewThumbnail = self.addUiObject(Thumbnail(self.renderer, self.__previewThumbnailX, self.__previewThumbnailY, self.__previewThumbnailWidth, self.__previewThumbnailHeight, game, self.app.bodyFont, self.app.textColour, False))
		
	def drawScreen(self):
		if self.refreshNeeded:
			self.refresh()
		
		if self.__consoleTexture == None:
			self.__consoleTexture = sdl2.SDL_CreateTextureFromSurface(self.renderer, self.app.consoleSurfaces[self.__consoleName])
			sdl2.SDL_SetTextureAlphaMod(self.__consoleTexture, CONSOLE_TEXTURE_ALPHA)
		sdl2.SDL_RenderCopy(self.renderer, self.__consoleTexture, None, sdl2.SDL_Rect(self.screenRect[0], self.screenRect[1], self.screenRect[2], self.screenRect[3]))
		self.__titleLabel.draw()
		
		selectedText = self.menu.getSelectedItem().getText()
		if self.menuActive:
			if selectedText == "Recently Added":
				self.__recentlyAddedThumbPanel.draw()
			elif selectedText == "Recently Played":
				if self.__recentlyPlayedGamesTotal > 0 and self.__recentlyPlayedThumbPanel:
					self.__recentlyPlayedThumbPanel.draw()
				else:
					self.__noGamesFoundLabel.draw()
			elif selectedText == "Favourites":
				if self.__favouriteGamesTotal > 0 and self.__favouriteThumbPanel:
					self.__favouriteThumbPanel.draw()
				else:
					self.__noGamesFoundLabel.draw()
			elif selectedText == "Have Badges":
				if self.__gamesWithAchievementsTotal > 0 and self.__achievementsThumbPanel:
					self.__achievementsThumbPanel.draw()
				else:
					self.__noGamesFoundLabel.draw()
			elif selectedText == "Most Played":
				if self.__mostPlayedGamesTotal > 0 and self.__mostPlayedThumbPanel:
					self.__mostPlayedThumbPanel.draw()
				else:
					self.__noGamesFoundLabel.draw()
			elif selectedText == "All":
				#self.__descriptionLabel.draw()
				self.__allGamesThumbPanel.draw()
		else:
			if selectedText == "Recently Added":
				self.__recentlyAddedGamesList.draw()
				self.__previewThumbnail.draw()
				self.__gameInfoLabel.draw()
				self.__gameOverviewLabel.draw()
			elif selectedText == "Recently Played":
				if self.__recentlyPlayedGamesTotal > 0:
					self.__recentlyPlayedList.draw()
					self.__previewThumbnail.draw()
					self.__gameInfoLabel.draw()
					self.__gameOverviewLabel.draw()
				else:
					self.__noGamesFoundLabel.draw()
			elif selectedText == "Favourites":
				if self.__favouriteGamesTotal > 0:
					self.__favouritesList.draw()
					self.__previewThumbnail.draw()
					self.__gameInfoLabel.draw()
					self.__gameOverviewLabel.draw()
				else:
					self.__noGamesFoundLabel.draw()
			elif selectedText == "Have Badges":
				if self.__gamesWithAchievementsTotal > 0:
					self.__achievementsList.draw()
					self.__previewThumbnail.draw()
					self.__gameInfoLabel.draw()
					self.__gameOverviewLabel.draw()
				else:
					self.__noGamesFoundLabel.draw()
			elif selectedText == "Most Played":
				if self.__mostPlayedGamesTotal > 0:
					self.__mostPlayedList.draw()
					self.__previewThumbnail.draw()
					self.__gameInfoLabel.draw()
					self.__gameOverviewLabel.draw()
				else:
					self.__noGamesFoundLabel.draw()
			elif selectedText == "All":
				self.__allGamesList.draw()
				self.__previewThumbnail.draw()
				self.__gameInfoLabel.draw()
				self.__gameOverviewLabel.draw()
			
	def __getGameInfoText(self, game):
		lastPlayed = "N/A"
		playCount = game.getPlayCount()
		if playCount > 0:
			lastPlayed = game.getLastPlayed("%d/%m/%Y")
		achievementInfo = "N/A"
		if self.app.retroAchievementConn and self.app.achievementUser and game.hasAchievements():
			achievementGame = self.app.achievementUser.getGame(game.getAchievementApiId())
			achievementInfo = "%d%% complete, %d points" % (achievementGame.getPercentComplete(), achievementGame.getUserPointsTotal())
		return "File name: %s\nReleased: %s\nPlay Count: %d\nLast Played: %s\nSize: %s\nBadges: %s\nOverview:" % (os.path.basename(game.getPath()), game.getReleased("%d/%m/%Y"), playCount, lastPlayed, game.getSize(True), achievementInfo)
	
	def __playGame(self, game):
		if self.app.retroAchievementConn and self.app.achievementUser and game.hasAchievements():
			self.app.screens["Play"].setGame(game)
			self.app.setScreen("Play")
		else:
			self.app.playGame(game)
			
	def processEvent(self, event):
		super(ConsoleScreen, self).processEvent(event)
		if self.menuActive:
			if event.type == sdl2.SDL_KEYDOWN and (event.key.keysym.sym == sdl2.SDLK_UP or event.key.keysym.sym == sdl2.SDLK_DOWN or event.key.keysym.sym == sdl2.SDLK_BACKSPACE):
				selectedText = self.menu.getSelectedItem().getText()
				self.__titleLabel.setText("%s: %s" % (self.__consoleName, selectedText))
				if selectedText == "All":
					self.__descriptionLabel.setText("Browse all %d games." % self.__console.getGameTotal(), True)
				elif selectedText == "Search":
					self.__descriptionLabel.setText("Search for games here.", True)
					if self.__searchLabel:
						self.__searchLabel.setFocus(False)
						self.__searchLabel.setVisible(False)
		else:
			if event.type == sdl2.SDL_KEYUP:
				selectedText = self.menu.getSelectedItem().getText()
				if selectedText == "All" and self.__allGamesList:
					self.__allGamesList.processEvent(event)
				elif selectedText == "Recently Added" and self.__recentlyAddedGamesList:
					self.__recentlyAddedGamesList.processEvent(event)
				elif selectedText == "Most Played" and self.__mostPlayedList:
					self.__mostPlayedList.processEvent(event)
				elif selectedText == "Recently Played" and self.__recentlyPlayedList:
					self.__recentlyPlayedList.processEvent(event)
				elif selectedText == "Favourites" and self.__favouritesList:
					self.__favouritesList.processEvent(event)
				elif selectedText == "Have Badges" and self.__achievementsList:
					self.__achievementsList.processEvent(event)
			elif event.type == sdl2.SDL_KEYDOWN:
				selectedText = self.menu.getSelectedItem().getText()
				if self.justActivated and (event.key.keysym.sym == sdl2.SDLK_RETURN or event.key.keysym.sym == sdl2.SDLK_KP_ENTER):
					if selectedText == "All" and self.__allGamesList == None:
						self.__allGamesList = self.addUiObject(List(self.renderer, self.__listX, self.__listY, self.__listWidth, self.__listHeight, self.__createMenu(self.__allGames), self.app.bodyFont, self.app.textColour, self.app.textColour, self.app.menuSelectedBgColour, self.app.menuTextColour, List.SCROLLBAR_AUTO, True, False))
						self.__allGamesList.setFocus(True)
						self.__allGamesList.addListener(self)
						self.__gameInfoLabel.setText(self.__getGameInfoText(self.__allGames[0]))
						self.__gameOverviewLabel.setText(self.__allGames[0].getOverview())
						self.__createPreviewThumbnail(self.__allGames[0])
					elif selectedText == "Recently Added" and self.__recentlyAddedGamesList == None:
						self.__recentlyAddedGamesList = self.addUiObject(List(self.renderer, self.__listX, self.__listY, self.__listWidth, self.__listHeight, self.__createMenu(self.__recentlyAddedGames), self.app.bodyFont, self.app.textColour, self.app.textColour, self.app.menuSelectedBgColour, self.app.menuTextColour, List.SCROLLBAR_AUTO, True, False))
						self.__recentlyAddedGamesList.setFocus(True)
						self.__recentlyAddedGamesList.addListener(self)
						self.__gameInfoLabel.setText(self.__getGameInfoText(self.__recentlyAddedGames[0]))
						self.__gameOverviewLabel.setText(self.__recentlyAddedGames[0].getOverview())
						self.__createPreviewThumbnail(self.__recentlyAddedGames[0])
					elif selectedText == "Most Played" and self.__mostPlayedList == None:
						if self.__mostPlayedGamesTotal > 0:
							self.__mostPlayedList = self.addUiObject(List(self.renderer, self.__listX, self.__listY, self.__listWidth, self.__listHeight, self.__createMenu(self.__mostPlayedGames), self.app.bodyFont, self.app.textColour, self.app.textColour, self.app.menuSelectedBgColour, self.app.menuTextColour, List.SCROLLBAR_AUTO, True, False))
							self.__mostPlayedList.setFocus(True)
							self.__mostPlayedList.addListener(self)
							self.__gameInfoLabel.setText(self.__getGameInfoText(self.__mostPlayedGames[0]))
							self.__gameOverviewLabel.setText(self.__mostPlayedGames[0].getOverview())
							self.__createPreviewThumbnail(self.__mostPlayedGames[0])
					elif selectedText == "Recently Played" and self.__recentlyPlayedList == None:
						if self.__recentlyPlayedGamesTotal > 0:
							self.__recentlyPlayedList = self.addUiObject(List(self.renderer, self.__listX, self.__listY, self.__listWidth, self.__listHeight, self.__createMenu(self.__recentlyPlayedGames), self.app.bodyFont, self.app.textColour, self.app.textColour, self.app.menuSelectedBgColour, self.app.menuTextColour, List.SCROLLBAR_AUTO, True, False))
							self.__recentlyPlayedList.setFocus(True)
							self.__recentlyPlayedList.addListener(self)
							self.__gameInfoLabel.setText(self.__getGameInfoText(self.__recentlyPlayedGames[0]))
							self.__gameOverviewLabel.setText(self.__recentlyPlayedGames[0].getOverview())
							self.__createPreviewThumbnail(self.__recentlyPlayedGames[0])
					elif selectedText == "Favourites" and self.__favouritesList == None:
						if self.__favouriteGamesTotal > 0:
							self.__favouritesList = self.addUiObject(List(self.renderer, self.__listX, self.__listY, self.__listWidth, self.__listHeight, self.__createMenu(self.__favouriteGames), self.app.bodyFont, self.app.textColour, self.app.textColour, self.app.menuSelectedBgColour, self.app.menuTextColour, List.SCROLLBAR_AUTO, True, False))
							self.__favouritesList.setFocus(True)
							self.__favouritesList.addListener(self)
							self.__gameInfoLabel.setText(self.__getGameInfoText(self.__favouriteGames[0]))
							self.__gameOverviewLabel.setText(self.__favouriteGames[0].getOverview())
							self.__createPreviewThumbnail(self.__favouriteGames[0])
					elif selectedText == "Have Badges" and self.__achievementsList == None:
						if self.__gamesWithAchievementsTotal > 0:
							self.__achievementsList = self.addUiObject(List(self.renderer, self.__listX, self.__listY, self.__listWidth, self.__listHeight, self.__createMenu(self.__gamesWithAchievements), self.app.bodyFont, self.app.textColour, self.app.textColour, self.app.menuSelectedBgColour, self.app.menuTextColour, List.SCROLLBAR_AUTO, True, False))
							self.__achievementsList.setFocus(True)
							self.__achievementsList.addListener(self)
							self.__gameInfoLabel.setText(self.__getGameInfoText(self.__gamesWithAchievements[0]))
							self.__gameOverviewLabel.setText(self.__gamesWithAchievements[0].getOverview())
							self.__createPreviewThumbnail(self.__gamesWithAchievements[0])
				else:
					if selectedText == "All":
						self.__allGamesList.processEvent(event)
					elif selectedText == "Recently Added":
						self.__recentlyAddedGamesList.processEvent(event)
					elif selectedText == "Favourites" and self.__favouritesList:
						self.__favouritesList.processEvent(event)
					elif selectedText == "Most Played" and self.__mostPlayedList:
						self.__mostPlayedList.processEvent(event)
					elif selectedText == "Recently Played" and self.__recentlyPlayedList:
						self.__recentlyPlayedList.processEvent(event)
					elif selectedText == "Have Badges" and self.__achievementsList:
						self.__achievementsList.processEvent(event)
						
	def processListEvent(self, uiList, eventType, item):
		if eventType == List.LISTEN_ITEM_SELECTED:
			if self.__previewThumbnail:
				game = item.getGame()
				self.__previewThumbnail.setGame(game)
				self.__gameInfoLabel.setText(self.__getGameInfoText(game))
				self.__gameOverviewLabel.setText(game.getOverview())
		if eventType == List.LISTEN_ITEM_TOGGLED:
			g = item.getGame()
			g.setFavourite(item.isToggled())
			g.save()
			self.__updateFavourites()
						
	def refresh(self):
		logging.debug("ConsoleScreen.refresh: reloading content for %s..." % self.__consoleName)
		start = time.time()
		# all games
		self.__allGames = self.__console.getGames()
		self.__allGamesTotal = len(self.__allGames)
		if self.__allGamesList:
			self.__allGamesList.setMenu(self.__createMenu(self.__allGames))
		if self.__allGamesThumbPanel:
			self.__allGamesThumbPanel.setGames(self.__allGames[0:self.__showThumbs])
		else:
			self.__allGamesThumbPanel = self.addUiObject(ThumbnailPanel(self.renderer, self.__listX, self.__listY, self.screenRect[2] - self.screenMargin,  self.__allGames[0:self.__showThumbs], self.app.bodyFont, self.app.textColour, self.app.menuSelectedBgColour, self.__thumbXGap, True, self.__showThumbs))
		# recently added
		recentlyAddedGameIds = self.__console.getRecentlyAddedGameIds()
		self.__recentlyAddedGamesTotal = len(recentlyAddedGameIds)
		self.__recentlyAddedGames = []
		for i in recentlyAddedGameIds:
			self.__recentlyAddedGames.append(self.__console.getGame(i))
		if self.__recentlyAddedGamesList:
			self.__recentlyAddedGamesList.setMenu(self.__createMenu(self.__recentlyAddedGames))
		if self.__recentlyAddedThumbPanel:
			self.__recentlyAddedThumbPanel.setGames(self.__recentlyAddedGames[0:self.__showThumbs])
		else:
			self.__recentlyAddedThumbPanel = self.addUiObject(ThumbnailPanel(self.renderer, self.__listX, self.__listY, self.screenRect[2] - self.screenMargin,  self.__recentlyAddedGames[0:self.__showThumbs], self.app.bodyFont, self.app.textColour, self.app.menuSelectedBgColour, self.__thumbXGap, True, self.__showThumbs))
		# most played
		mostPlayedGameIds = self.__console.getMostPlayedGameIds()
		self.__mostPlayedGamesTotal = len(mostPlayedGameIds)
		self.__mostPlayedGames = []
		if self.__mostPlayedGamesTotal > 0:
			for i in mostPlayedGameIds:
				self.__mostPlayedGames.append(self.__console.getGame(i))
			if self.__mostPlayedList:
				self.__mostPlayedList.setMenu(self.__createMenu(self.__mostPlayedGames))
			if self.__mostPlayedThumbPanel:
				self.__mostPlayedThumbPanel.setGames(self.__mostPlayedGames[0:self.__showThumbs])
			else:
				self.__mostPlayedThumbPanel = self.addUiObject(ThumbnailPanel(self.renderer, self.__listX, self.__listY, self.screenRect[2] - self.screenMargin,  self.__mostPlayedGames[0:self.__showThumbs], self.app.bodyFont, self.app.textColour, self.app.menuSelectedBgColour, self.__thumbXGap, True, self.__showThumbs))
		# recently played
		recentlyPlayedGameIds = self.__console.getRecentlyPlayedGameIds()
		self.__recentlyPlayedGamesTotal = len(recentlyPlayedGameIds)
		self.__recentlyPlayedGames = []
		if self.__recentlyPlayedGamesTotal > 0:
			for i in recentlyPlayedGameIds:
				self.__recentlyPlayedGames.append(self.__console.getGame(i))
			if self.__recentlyPlayedList:
				self.__recentlyPlayedList.setMenu(self.__createMenu(self.__recentlyPlayedGames))
			if self.__recentlyPlayedThumbPanel:
				self.__recentlyPlayedThumbPanel.setGames(self.__recentlyPlayedGames[0:self.__showThumbs])
			else:
				self.__recentlyPlayedThumbPanel = self.addUiObject(ThumbnailPanel(self.renderer, self.__listX, self.__listY, self.screenRect[2] - self.screenMargin,  self.__recentlyPlayedGames[0:self.__showThumbs], self.app.bodyFont, self.app.textColour, self.app.menuSelectedBgColour, self.__thumbXGap, True, self.__showThumbs))
		# games with achievements
		gamesWithAchievementIds = self.__console.getGamesWithAchievementIds()
		self.__gamesWithAchievementsTotal = len(gamesWithAchievementIds)
		self.__gamesWithAchievements = []
		if self.__gamesWithAchievementsTotal > 0:
			for i in gamesWithAchievementIds:
				self.__gamesWithAchievements.append(self.__console.getGame(i))
			if self.__achievementsList:
				self.__achievementsList.setMenu(self.__createMenu(self.__gamesWithAchievements))
			if self.__achievementsThumbPanel:
				self.__achievementsThumbPanel.setGames(self.__gamesWithAchievements[0:self.__showThumbs])
			else:
				self.__achievementsThumbPanel = self.addUiObject(ThumbnailPanel(self.renderer, self.__listX, self.__listY, self.screenRect[2] - self.screenMargin,  self.__gamesWithAchievements[0:self.__showThumbs], self.app.bodyFont, self.app.textColour, self.app.menuSelectedBgColour, self.__thumbXGap, True, self.__showThumbs))
		self.__updateFavourites()
		self.refreshNeeded = False
		logging.debug("ConsoleScreen.__refresh: time taken = %0.02fs" % (time.time() - start))
		
	def __updateFavourites(self):
		self.__favouriteGames = []
		favouriteGameIds = self.__console.getFavouriteIds()
		self.__favouriteGamesTotal = len(favouriteGameIds)
		logging.debug("ConsoleScreen.__updateFavourites: favourite total: %d" % self.__favouriteGamesTotal)
		if self.__favouriteGamesTotal > 0:
			for i in favouriteGameIds:
				self.__favouriteGames.append(self.__console.getGame(i))
			if self.__favouritesList:
				self.__favouritesList.setMenu(self.__createMenu(self.__favouriteGames))
			if self.__favouriteThumbPanel:
				self.__favouriteThumbPanel.setGames(self.__favouriteGames[0:self.__showThumbs])
			else:
				self.__favouriteThumbPanel = self.addUiObject(ThumbnailPanel(self.renderer, self.__listX, self.__listY, self.screenRect[2] - self.screenMargin,  self.__favouriteGames[0:self.__showThumbs], self.app.bodyFont, self.app.textColour, self.app.menuSelectedBgColour, self.__thumbXGap, True, self.__showThumbs))
			if self.menu.getSelectedItem().getText() == "Favourites":
				self.__gameInfoLabel.setText(self.__getGameInfoText(self.__favouriteGames[0]))
				self.__gameOverviewLabel.setText(self.__favouriteGames[0].getOverview())
				if self.__previewThumbnail != None:
					self.__previewThumbnail.setGame(self.__favouriteGames[0])
		else:
			if self.__favouritesList:
				self.__favouritesList.destroy()
				self.__favouritesList = None
		
	def stop(self):
		super(ConsoleScreen, self).stop()
		logging.debug("ConsoleScreen.stop: deleting textures for %s..." % self.__consoleName)
		if self.__consoleTexture:
			sdl2.SDL_DestroyTexture(self.__consoleTexture)
	
class HomeScreen(Screen):
	
	def __init__(self, app, renderer, menuRect, screenRect):
		super(HomeScreen, self).__init__(app, renderer, "Home", Menu([MenuItem("Home")]), menuRect, screenRect)
		#super(HomeScreen, self).__init__(app, renderer, "Home", Menu([MenuItem("Achievements", False, False, app.setScreen, "Achievements")]), menuRect, screenRect)
		for c in self.app.consoles:
			if c.getGameTotal() > 0:
				self.menu.addItem(ConsoleMenuItem(c, False, False, self.__loadConsoleScreen, c))
		#self.menu.addItem(MenuItem("Achievements", False, False, self.app.setScreen, "Achievements"))
		self.menu.addItem(MenuItem("Settings", False, False, self.app.setScreen, "Settings"))
		self.menu.addItem(MenuItem("Reload", False, False, self.app.reload))
		self.menu.addItem(MenuItem("Reboot", False, False, self.app.reboot))
		self.menu.addItem(MenuItem("Power Off", False, False, self.app.shutdown))
		self.menu.addItem(MenuItem("Exit", False, False, self.app.exit, 0, True))
		self.__thumbXGap = 20
		self.__thumbYGap = 10
		self.__showThumbs = 10
		self.__desiredThumbWidth = int((screenRect[2] - (self.__showThumbs * self.__thumbXGap)) / self.__showThumbs)
		self.__consoleTexture = None
		self.__consoleSelected = False
		self.__consoleName = None
		self.__headerLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.screenRect[1], "Welcome to PES!", self.app.titleFont, self.app.textColour))
		#self.__headerLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.screenRect[1], "Achievements", self.app.titleFont, self.app.textColour))
		
		self.__gamesAdded = self.app.getGameTotal() > 0
		
		self.__noGamesAddedWelcomeText = "Before you can start playing any games, please add some to PES and then go to \"Update Games\" under the \"Settings\" screen.\n\nNote: if you sign up for an account at www.retroachievements.org and enter your details into your pes.ini file, PES will show your achievements here.\n\nFor help please visit http://pes.mundayweb.com."
		self.__gamesAddedWelcomeText = "Please select an item from the menu on the left.\n\nNote: if you sign up for an account at www.retroachievements.org and enter your details into your pes.ini file, PES will show your achievements here.\n\nFor help please visit http://pes.mundayweb.com."
		
		if self.__gamesAdded:
			self.__welcomeText = self.__gamesAddedWelcomeText
		else:
			self.__welcomeText = self.__noGamesAddedWelcomeText
				
		self.__descriptionLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.__headerLabel.y + (self.__headerLabel.height * 2), self.__welcomeText, self.app.bodyFont, self.app.textColour, fixedWidth=self.wrap))
		#self.__descriptionLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.__headerLabel.y + (self.__headerLabel.height * 2), "BLAH", self.app.bodyFont, self.app.textColour, fixedWidth=self.wrap))
		self.__recentlyAddedText = "Recently Added"
		self.__recentlyAddedLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.__headerLabel.y + (self.__headerLabel.height * 2), self.__recentlyAddedText, self.app.bodyFont, self.app.textColour, fixedWidth=self.wrap))
		self.__recentlyPlayedLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.__headerLabel.y + (self.__headerLabel.height * 2), "Recently Played", self.app.bodyFont, self.app.textColour, fixedWidth=self.wrap))
		
		self.__recentlyAddedThumbPanels = {}
		self.__recentlyPlayedThumbPanels = {}
		
		self.__badgePanels = []
		self.__initBadges = True # hack to make sure badges are not initialised inside the PES loading thread

		logging.debug("HomeScreen.init: initialised")
		
	def __doNothing(self):
		self.setMenuActive(True)
			
	def drawScreen(self):
		super(HomeScreen, self).drawScreen()
		
		self.__headerLabel.draw()
		if self.__consoleSelected:
			sdl2.SDL_RenderCopy(self.renderer, self.__consoleTexture, None, sdl2.SDL_Rect(self.screenRect[0], self.screenRect[1], self.screenRect[2], self.screenRect[3]))
			self.__recentlyAddedLabel.draw()
			if self.__consoleName in self.__recentlyAddedThumbPanels:
				self.__recentlyAddedThumbPanels[self.__consoleName].draw()
			if self.__consoleName in self.__recentlyPlayedThumbPanels:
				self.__recentlyPlayedThumbPanels[self.__consoleName].draw()
			self.__recentlyPlayedLabel.draw()
		elif self.menu.getSelectedItem().getText() == "Home":
			if self.__initBadges:
				self.updateRecentBadges()
				self.__initBadges = False
			self.__descriptionLabel.draw()
			for p in self.__badgePanels:
				p.draw()
		else:
			self.__descriptionLabel.draw()
			
	def __loadConsoleScreen(self, console):
		screenName = "Console %s" % console.getName()
		self.app.screens[screenName].refresh()
		self.app.setScreen(screenName)
		
	def loadTextures(self):
		logging.debug("HomeScreen.loadTextures: pre-loading textures for thumb panels...")
		for console in self.app.consoles:
			if console.getGameTotal() > 0:
				games = console.getRecentlyAddedGames(0, self.__showThumbs)
				if len(games) > 0:
					t = ThumbnailPanel(self.renderer, self.screenRect[0] + self.screenMargin, self.__recentlyAddedLabel.y + self.__recentlyAddedLabel.height + self.__thumbYGap, self.screenRect[2] - self.screenMargin, games, self.app.bodyFont, self.app.textColour, self.app.menuSelectedBgColour, self.__thumbXGap, True, self.__showThumbs)
					t.loadTextures()
					self.__recentlyAddedThumbPanels[console.getName()] = self.addUiObject(t)
				games = console.getRecentlyPlayedGames(0, self.__showThumbs)
				if len(games) > 0:
					t = ThumbnailPanel(self.renderer, self.screenRect[0] + self.screenMargin, self.__recentlyPlayedLabel.y + self.__recentlyPlayedLabel.height + self.__thumbYGap, self.screenRect[2] - self.screenMargin, games, self.app.bodyFont, self.app.textColour, self.app.menuSelectedBgColour, self.__thumbXGap, True, self.__showThumbs)
					t.loadTextures()
					self.__recentlyPlayedThumbPanels[console.getName()] = self.addUiObject(t)
		

	def processEvent(self, event):
		super(HomeScreen, self).processEvent(event)
		if self.menuActive and event.type == sdl2.SDL_KEYDOWN and (event.key.keysym.sym == sdl2.SDLK_UP or event.key.keysym.sym == sdl2.SDLK_DOWN):
			self.update()
		elif not self.menuActive and self.menu.getSelectedItem().getText() == "Home" and event.type == sdl2.SDL_KEYDOWN and (event.key.keysym.sym == sdl2.SDLK_KP_ENTER or event.key.keysym.sym == sdl2.SDLK_RETURN):
			self.setMenuActive(True)
		
	def refreshMenu(self):
		logging.debug("HomeScreen.refreshMenu: refreshing menu contents...")
		items = self.menu.getItems()
		for m in items:
			if isinstance(m, ConsoleMenuItem):
				logging.debug("HomeScreen.refreshMenu: removing %s" % m.getText())
				self.menu.removeItem(m)
			else:
				logging.debug("HomeScreen.refreshMenu: not removing %s" % m.getText())
		for c in self.app.consoles:
			if c.getGameTotal() > 0:
				consoleName = c.getName()
				logging.debug("HomeScreen.refreshMenu: inserting %s" % consoleName)
				self.menu.insertItem(len(self.menu.getItems()) - 5, ConsoleMenuItem(c, False, False, self.app.setScreen, "Console %s" % consoleName))
				# update recently added thumbnails
				games = c.getRecentlyAddedGames(0, self.__showThumbs)
				if consoleName not in self.__recentlyAddedThumbPanels:
					if len(games) > 0:
						t = ThumbnailPanel(self.renderer, self.screenRect[0] + self.screenMargin, self.__recentlyAddedLabel.y + self.__recentlyAddedLabel.height + self.__thumbYGap, self.screenRect[2] - self.screenMargin, games, self.app.bodyFont, self.app.textColour, self.app.menuSelectedBgColour, self.__thumbXGap, True, self.__showThumbs)
						t.loadTextures()
						self.__recentlyAddedThumbPanels[consoleName] = self.addUiObject(t)
				else:
					self.__recentlyAddedThumbPanels[consoleName].setGames(games)
		self.menu.setSelected(0, deselectAll=True)
		self.__gamesAdded = self.app.getGameTotal() > 0
		if self.__gamesAdded and self.app.achievementUser:
			self.updateRecentBadges()
		else:
			if self.__gamesAdded:
				self.__welcomeText = self.__gamesAddedWelcomeText
			else:
				self.__welcomeText = self.__noGamesAddedWelcomeText
		self.update()
		
	def stop(self):
		super(HomeScreen, self).stop()
		logging.debug("HomeScreen.stop: deleting textures...")
		sdl2.SDL_DestroyTexture(self.__consoleTexture)
		
	def update(self):
		selected = self.menu.getSelectedItem()
		if isinstance(selected, ConsoleMenuItem):
			console = selected.getConsole()
			self.__consoleName = console.getName()
			if self.__consoleTexture:
				sdl2.SDL_DestroyTexture(self.__consoleTexture)
			self.__consoleTexture = sdl2.SDL_CreateTextureFromSurface(self.renderer, self.app.consoleSurfaces[self.__consoleName])
			sdl2.SDL_SetTextureAlphaMod(self.__consoleTexture, CONSOLE_TEXTURE_ALPHA)
			self.__headerLabel.setText(self.__consoleName)
			
			if self.__consoleName in self.__recentlyPlayedThumbPanels:
				self.__recentlyPlayedLabel.y = self.__recentlyAddedThumbPanels[self.__consoleName].y + self.__recentlyAddedThumbPanels[self.__consoleName].height + 50
				self.__recentlyPlayedLabel.setVisible(True)
				self.__recentlyPlayedThumbPanels[self.__consoleName].setCoords(self.__recentlyPlayedThumbPanels[self.__consoleName].x, self.__recentlyPlayedLabel.y + self.__recentlyPlayedLabel.height + self.__thumbYGap)
			else:
				self.__recentlyPlayedLabel.setVisible(False)
			self.__consoleSelected = True
		else:
			self.__consoleSelected = False
			selectedText = selected.getText()
			if selectedText == "Home":
				self.__headerLabel.setText("Welcome to PES!")
				self.__descriptionLabel.setText(self.__welcomeText, True)
			elif selectedText == "Reboot":
				self.__headerLabel.setText("Reboot")
				self.__descriptionLabel.setText("Select this menu item to reboot your system.", True)
			elif selectedText == "Reload":
				self.__headerLabel.setText("Reload")
				self.__descriptionLabel.setText("Select this menu item to reload the PES GUI - handy if you have edited any config files.", True)
			elif selectedText == "Exit":
				self.__headerLabel.setText("Exit")
				self.__descriptionLabel.setText("Select this menu item to exit the PES GUI and return to the command line.", True)
			elif selectedText == "Settings":
				self.__headerLabel.setText("Settings")
				self.__descriptionLabel.setText("Select this menu item to customise PES and to add ROMs to PES' database.", True)
			elif selectedText == "Power Off":
				self.__headerLabel.setText("Power Off")
				self.__descriptionLabel.setText("Select this menu item to power off your system.", True)
				
	def updateRecentBadges(self):
		if self.__gamesAdded and self.app.achievementUser:
			logging.debug("HomeScreen.updateRecentBadges: updating...")
			self.__welcomeText = "Welcome to PES %s.\n\nPoints: %d (%d)\nRank: %d" % (self.app.achievementUser.getName(), self.app.achievementUser.getTotalPoints(), self.app.achievementUser.getTotalTruePoints(), self.app.achievementUser.getRank())
			for b in self.__badgePanels:
				self.removeUiObject(b)
				b.destroy()
			self.__badgePanels = []
			badges = self.app.achievementUser.getRecentBadges(10)
			if len(badges) == 0:
				self.__welcomeText += "\n\nNo recent badges.\n\nYou may want to go to \"Update Badges\" under the \"Settings\" menu."
			else:
				self.__welcomeText += "\n\nYour recent badges:\n"
			self.__descriptionLabel.setText(self.__welcomeText, True)
			x = self.screenRect[0] + self.screenMargin
			y = self.__descriptionLabel.y + self.__descriptionLabel.height + 20
			width = self.screenRect[2] - (self.screenMargin * 2)
			for b in badges:
				badgePanel = self.addUiObject(BadgePanel(self.app.renderer, x, y, width, self.app.bodyFont, self.app.smallBodyFont, self.app.textColour, self.app.lightBackgroundColour, self.app.menuSelectedBgColour, b))
				self.__badgePanels.append(badgePanel)
				y += badgePanel.height + 10
				if y + badgePanel.height > self.screenRect[1] + self.screenRect[3]:
					break
				
class PlayScreen(Screen):
	
	def __init__(self, app, renderer, menuRect, screenRect, game):
		super(PlayScreen, self).__init__(app, renderer, "Play", Menu([MenuItem("Play", False, False, self.__play), MenuItem("Browse")]), menuRect, screenRect)
		self.__game = game
		self.__consoleTexture = None
		self.__titleLabel = None
		self.__consoleName = None
		self.__achievementsList = None
		logging.debug("PlayScreen.init: intialised")
		
	def drawScreen(self):
		super(PlayScreen, self).drawScreen()
		sdl2.SDL_RenderCopy(self.renderer, self.__consoleTexture, None, sdl2.SDL_Rect(self.screenRect[0], self.screenRect[1], self.screenRect[2], self.screenRect[3]))
		self.__titleLabel.draw()
		self.__achievementsList.draw()
		
	def __play(self):
		self.app.playGame(self.__game)
		
	def processEvent(self, event):
		super(PlayScreen, self).processEvent(event)
		
		if not self.menuActive and not self.justActivated:
			if self.menu.getSelectedItem().getText() == "Browse":
				self.__achievementsList.setFocus(True)
				self.__achievementsList.processEvent(event)
			elif self.__achievementsList.hasFocus():
				self.__achievementsList.setFocus(False)
		elif self.__achievementsList.hasFocus():
			self.__achievementsList.setFocus(False)
		
	def setGame(self, game):
		if game == self.__game:
			return
		achievementGame = self.app.achievementUser.getGame(game.getAchievementApiId())
		if achievementGame == None:
			logging.error("PlayScreen.setGame: could not find a game with achievement_api_id = %d" % game.getAchievementApiId())
			self.app.exit(1)
		self.__game = game
		consoleName = game.getConsole().getName()
		titleStr = "Game: %s\nProgress: %d%%\nPoints: %d of %d awarded" % (game.getName(), achievementGame.getPercentComplete(), achievementGame.getUserPointsTotal(), achievementGame.getScoreTotal())
		if self.__titleLabel == None:
			self.__titleLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.screenRect[1], titleStr,
 self.app.titleFont, self.app.textColour, fixedWidth=self.wrap))
		else:
			self.__titleLabel.setText(titleStr, True)
		if self.__consoleTexture == None:
			self.__consoleTexture = sdl2.SDL_CreateTextureFromSurface(self.renderer, self.app.consoleSurfaces[consoleName])
			sdl2.SDL_SetTextureAlphaMod(self.__consoleTexture, CONSOLE_TEXTURE_ALPHA)
		elif self.__consoleName != consoleName:
			sdl2.SDL_DestroyTexture(self.__consoleTexture)
			self.__consoleTexture = sdl2.SDL_CreateTextureFromSurface(self.renderer, self.app.consoleSurfaces[consoleName])
			sdl2.SDL_SetTextureAlphaMod(self.__consoleTexture, CONSOLE_TEXTURE_ALPHA)
		self.__consoleName = consoleName
		menu = Menu([])
		badges = achievementGame.getBadges()
		for b in badges:
			menu.addItem(DataMenuItem(b, False, False, self.__play))
		if self.__achievementsList == None:
			y = self.__titleLabel.y + self.__titleLabel.height + 10
			self.__achievementsList = self.addUiObject(IconPanelList(self.renderer, self.__titleLabel.x, y, self.screenRect[2] - (self.screenMargin * 2), self.screenRect[3] - y - self.screenMargin, menu, self.app.bodyFont, self.app.smallBodyFont, self.app.textColour, self.app.textColour, None, self.app.menuSelectedBgColour, List.SCROLLBAR_AUTO, True, False))
		else:
			self.__achievementsList.setMenu(menu)
				
class JoystickPromptMap(object):
	
	BUTTON = 1
	AXIS = 2
	HAT = 3
	AXIS_POSITIVE = 1
	AXIS_NEGATIVE = -1
	
	def __init__(self, prompt, sdlName):
		self.__prompt = prompt
		self.__sdlName = sdlName
		self.reset()
		
	def getPrompt(self):
		return "Press: %s" % self.__prompt
	
	def getInputTypeAsString(self):
		if self.__inputType == None:
			return "None"
		if self.__inputType == self.BUTTON:
			return "Button"
		if self.__inputType == self.HAT:
			return "Hat"
		if self.__inputType == self.AXIS:
			return "Axis"
		return "Unknown!"
	
	def getMap(self):
		if self.__inputType == self.BUTTON:
			return "%s:b%s" % (self.__sdlName, self.__value)
		if self.__inputType == self.AXIS:
			axis, value = self.__value
			return "%s:a%s" % (self.__sdlName, axis)
		if self.__inputType == self.HAT:
			hat, value = self.__value
			return "%s:h%s.%s" % (self.__sdlName, hat, value)
		return None
	
	def getValue(self):
		return self.__value
	
	def getValueAsString(self):
		if self.__inputType == self.HAT:
			return "(Hat: %d %d)" % (self.__value[0], self.__value[1])
		if self.__inputType == self.AXIS:
			return "(Axis: %d %d)" % (self.__value[0], self.__value[1])
		return "%s" % self.__value
	
	def getType(self):
		return self.__inputType
	
	def reset(self):
		self.__value = None
		self.__inputType = None
		
	def setValue(self, inputType, value):
		self.__inputType = inputType
		self.__value = value
		logging.debug("JoystickPromptMap.setValue: name: %s, type: %s, value: %s" % (self.__sdlName, self.getInputTypeAsString(), self.getValueAsString()))
		
class SettingsScreen(Screen):
	
	def __init__(self, app, renderer, menuRect, screenRect):
		super(SettingsScreen, self).__init__(app, renderer, "Settings", Menu([
			MenuItem("Update Games"),
			MenuItem("Update Badges"),
			MenuItem("Joystick Set-Up")]),
		menuRect, screenRect)
		
		if self.app.currentTimezone != None:
			self.menu.addItem(MenuItem("Timezone"))
		
		self.menu.addItem(MenuItem("Reset Database", False, False, app.resetDatabase))
		self.menu.addItem(MenuItem("Reset Config", False, False, app.resetConfig))
		self.menu.addItem(MenuItem("About"))
		
		self.__init = True
		self.__updateDatabaseMenu = Menu([])
		for c in self.app.consoles:
			self.__updateDatabaseMenu.addItem(ConsoleMenuItem(c, False, True))
		self.__toggleMargin = 20
		self.__updateDbThread = None
		self.__updateAchievementsThread = None
		self.__scanProgressBar = None
		self.__defaultHeaderText = "Settings"
		self.__headerLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.screenRect[1], self.__defaultHeaderText, self.app.titleFont, self.app.textColour))
		logging.debug("SettingsScreen.init: initialised")
		self.__initText = "Here you can scan for new games, sync your badges with www.retroachievements.org, set-up your joysticks as well as being able to reset PES to its default settings\n\nPlease select an item from the menu on the left."
		self.__scanText = "Please use the menu below to select which consoles you wish to include in your search. By default all consoles are selected. Use the SELECT button to toggle the items in the menu.\n\nWhen you are ready, please select the \"Begin Scan\" button."
		self.__descriptionLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.__headerLabel.y + (self.__headerLabel.height * 2), self.__initText, self.app.bodyFont, self.app.textColour, fixedWidth=self.screenRect[2] - self.screenMargin))
		self.__consoleList = None
		self.__scanButton = None
		self.__selectAllButton = None
		self.__deselectAllButton = None
		self.__gamepadLayoutIcon = None
		self.__jsIndex= None
		self.__jsName = None
		self.__jsPromptLabel = None
		self.__jsPrompts = [
			JoystickPromptMap("Start", "start"),
			JoystickPromptMap("Select", "back"),
			JoystickPromptMap("Up", "dpup"),
			JoystickPromptMap("Down", "dpdown"),
			JoystickPromptMap("Left", "dpleft"),
			JoystickPromptMap("Right", "dpright"),
			JoystickPromptMap("A", "a"),
			JoystickPromptMap("B", "b"),
			JoystickPromptMap("X", "x"),
			JoystickPromptMap("Y", "y"),
			JoystickPromptMap("L1", "leftshoulder"),
			JoystickPromptMap("R1", "rightshoulder"),
			JoystickPromptMap("L2", "lefttrigger"),
			JoystickPromptMap("R2", "righttrigger"),
			JoystickPromptMap("Left Axis Vertical", "lefty"),
			JoystickPromptMap("Left Axis Horizontal", "leftx"),
			JoystickPromptMap("Right Axis Vertical", "righty"),
			JoystickPromptMap("Right Axis Horizontal", "rightx"),
			JoystickPromptMap("Guide/Home", "guide")
		]
		self.__jsPromptLen = len(self.__jsPrompts)
		self.__jsPrompt = 0
		self.__joysticks = []
		self.__ignoreJsEvents = True
		self.__jsTimerTick = 0
		self.__jsTimerLabel = None
		self.__jsTimeOut = 10
		self.__jsTimeRemaining = self.__jsTimeOut
		self.__jsInitialAxis = []
		self.__jsLastButton = None
		self.__jsLastAxis = None
		self.__jsLastHat = None
		self.__jsLastHatValue = None
		self.__jsLastEventTick = 0
		self.__isBusy = False
		self.__timezoneList = None

	def drawScreen(self):
		super(SettingsScreen, self).drawScreen()
		
		currentX = self.screenRect[0] + self.screenMargin
		currentY = self.screenRect[1]
		
		self.__headerLabel.draw()
		self.__descriptionLabel.draw()
		
		if self.__init:
			return
		
		selected = self.menu.getSelectedItem().getText()
		
		if selected == "Update Games":
			if self.__updateDbThread != None:
				if self.__updateDbThread.started and not self.__updateDbThread.done:
					self.__descriptionLabel.setText("Scanned %d out of %d roms... press BACK to abort\n\nElapsed: %s\n\nRemaining: %s\n\nProgress:" % (self.__updateDbThread.getProcessed(), self.__updateDbThread.romTotal, self.__updateDbThread.getElapsed(), self.__updateDbThread.getRemaining()), True)
					self.__scanProgressBar.y = self.__descriptionLabel.y + self.__descriptionLabel.height + 10
					self.__scanProgressBar.setProgress(self.__updateDbThread.getProgress())
					self.__scanProgressBar.draw()
				elif self.__updateDbThread.done:
					interruptedStr = ""
					if self.__updateDbThread.interrupted:
						interruptedStr = "(scan interrupted)"
					self.__descriptionLabel.setText("Scan completed in %s %s\n\nAdded: %d\n\nUpdated: %d\n\nDeleted: %d\n\nPress BACK to return to the previous screen." % (self.__updateDbThread.getElapsed(), interruptedStr, self.__updateDbThread.added, self.__updateDbThread.updated, self.__updateDbThread.deleted), True)
					self.__isBusy = False
			else:
				self.__consoleList.draw()
				self.__scanButton.draw()
				self.__selectAllButton.draw()
				self.__deselectAllButton.draw()
		elif selected == "Update Badges":
			if self.app.retroAchievementConn:
				if self.__updateAchievementsThread != None:
					if self.__updateAchievementsThread.started and not self.__updateAchievementsThread.done:
						self.__descriptionLabel.setText("Processed %d out of %d games... press BACK to abort\n\nElapsed: %s\n\nRemaining: %s\n\nProgress:" % (self.__updateAchievementsThread.getProcessed(), self.__updateAchievementsThread.getTotal(), self.__updateAchievementsThread.getElapsed(), self.__updateAchievementsThread.getRemaining()), True)
						self.__scanProgressBar.y = self.__descriptionLabel.y + self.__descriptionLabel.height + 10
						self.__scanProgressBar.setProgress(self.__updateAchievementsThread.getProgress())
						self.__scanProgressBar.draw()
					elif self.__updateAchievementsThread.done:
						interruptedStr = ""
						if self.__updateAchievementsThread.interrupted:
							interruptedStr = "(scan interrupted)"
						self.__descriptionLabel.setText("Scan completed in %s %s\n\nProcessed %d badges\n\nPress BACK or HOME to continue." % (self.__updateAchievementsThread.getElapsed(), interruptedStr, self.__updateAchievementsThread.getBadgeTotal()), True)
						self.__isBusy = False
			self.__descriptionLabel.draw()
		elif selected == "Timezone":
			self.__descriptionLabel.draw()
			if self.__timezoneList:
				self.__timezoneList.draw()
		elif selected == "Joystick Set-Up":
			if self.__jsTimeRemaining > -1 and self.__jsPrompt < self.__jsPromptLen:
				tick = sdl2.SDL_GetTicks()
				poll = self.__jsPrompt > 0
				if tick - self.__jsTimerTick > 1000:
					self.__jsTimerTick = tick
					self.__jsTimeRemaining -= 1
					
					self.__jsTimerLabel.setText("Timeout in: %ds" % self.__jsTimeRemaining)
					
					if self.__jsTimeRemaining == 0:
						# trigger back event
						e = sdl2.SDL_Event()
						e.type = sdl2.SDL_KEYDOWN
						e.key.keysym.sym = sdl2.SDLK_BACKSPACE
						sdl2.SDL_PushEvent(e)
						self.__jsTimeRemaining = -1
						poll = False
				
				if poll:
					# check buttons
					value = None
					js = self.__joysticks[self.__jsIndex]
					for i in xrange(sdl2.SDL_JoystickNumButtons(js)):
						if sdl2.SDL_JoystickGetButton(js, i) == 1 and sdl2.SDL_GetTicks() - self.__jsLastEventTick > 500:
							value = i
							self.__jsLastButton = value
							self.__jsLastEventTick = sdl2.SDL_GetTicks()
							break
			
					if value != None:
						self.__jsTimeRemaining = self.__jsTimeOut
						
						if value == self.__jsPrompts[0].getValue():
							logging.debug("SettingsScreen.draw: skipping button %s" % self.__jsPrompts[self.__jsPrompt].getPrompt())
							self.__jsPrompt += 1
							if self.__jsPrompt < self.__jsPromptLen:
								self.__jsPromptLabel.setText(self.__jsPrompts[self.__jsPrompt].getPrompt())
						else:
							btnOk = True
							# have we already used this button value?
							for p in self.__jsPrompts:
								if p.getType() == JoystickPromptMap.BUTTON and p.getValue() == value:
									logging.warning("SettingsScreen.draw: this button has already been assigned")
									btnOk = False
									break
								
							if btnOk:
								self.__jsPrompts[self.__jsPrompt].setValue(JoystickPromptMap.BUTTON, value)
								self.__jsPrompt += 1
								if self.__jsPrompt < self.__jsPromptLen:
									self.__jsPromptLabel.setText(self.__jsPrompts[self.__jsPrompt].getPrompt())
					
					else:
						# do hats
						for i in xrange(sdl2.SDL_JoystickNumHats(js)):
							hvalue = sdl2.SDL_JoystickGetHat(js, i)
							# ignore diagonal hat buttons
							if sdl2.SDL_GetTicks() - self.__jsLastEventTick > 500 and hvalue != sdl2.SDL_HAT_CENTERED and hvalue != sdl2.SDL_HAT_RIGHTUP and hvalue != sdl2.SDL_HAT_RIGHTDOWN and hvalue != sdl2.SDL_HAT_LEFTUP and hvalue != sdl2.SDL_HAT_LEFTDOWN and (i != self.__jsLastHat or (i == self.__jsLastHat and hvalue != self.__jsLastHatValue)):
								value = hvalue
								self.__jsLastHat = i
								self.__jsLastHatValue = hvalue
								self.__jsLastEventTick = sdl2.SDL_GetTicks()
								break
							
						if value != None:
							self.__jsTimeRemaining = self.__jsTimeOut
							hatOk = True
							# have we already assigned this hat?
							for p in self.__jsPrompts:
								if p.getType() == JoystickPromptMap.HAT:
									h, v = p.getValue()
									if h == self.__jsLastHat and v == value:
										logging.warning("SettingsScreen.draw: this hat has already been assigned")
										hatOk = False
										break
						
							if hatOk:
								self.__jsPrompts[self.__jsPrompt].setValue(JoystickPromptMap.HAT, (self.__jsLastHat, value))
								self.__jsPrompt += 1
								if self.__jsPrompt < self.__jsPromptLen:
									self.__jsPromptLabel.setText(self.__jsPrompts[self.__jsPrompt].getPrompt())
						
						elif sdl2.SDL_GetTicks() - self.__jsLastEventTick > 750:
							# check axis
							for i in xrange(sdl2.SDL_JoystickNumAxes(js)):
								avalue = sdl2.SDL_JoystickGetAxis(js, i)
								if (avalue < JOYSTICK_AXIS_MIN or avalue > JOYSTICK_AXIS_MAX) and avalue != self.__jsInitialAxis[i]:
									value = i
									self.__jsLastAxis = value
									self.__jsLastEventTick = sdl2.SDL_GetTicks()
									break
								
							if value != None:
								self.__jsTimeRemaining = self.__jsTimeOut
								axisOk = True
								# have we already used this axis value?
								for p in self.__jsPrompts:
									if p.getType() == JoystickPromptMap.AXIS:
										a, v = p.getValue()
										if a == value and ((avalue < JOYSTICK_AXIS_MIN and v == JoystickPromptMap.AXIS_NEGATIVE) or (avalue > JOYSTICK_AXIS_MAX and v == JoystickPromptMap.AXIS_POSITIVE)):
											logging.warning("SettingsScreen.draw: this axis has already been assigned")
											axisOk = False
											break
									
								if axisOk:
									if avalue < JOYSTICK_AXIS_MIN:
										self.__jsPrompts[self.__jsPrompt].setValue(JoystickPromptMap.AXIS, (value, JoystickPromptMap.AXIS_NEGATIVE))
									else:
										self.__jsPrompts[self.__jsPrompt].setValue(JoystickPromptMap.AXIS, (value, JoystickPromptMap.AXIS_POSITIVE))
										
									self.__jsPrompt += 1
									if self.__jsPrompt < self.__jsPromptLen:
										self.__jsPromptLabel.setText(self.__jsPrompts[self.__jsPrompt].getPrompt())
									
					if self.__jsPrompt == self.__jsPromptLen:
						logging.debug("SettingsScreen.draw: joystick configuration complete!")
						self.__jsPromptLabel.setVisible(False)
						self.__jsTimerLabel.setVisible(False)
						self.__ignoreJsEvents = True
						self.app.doJsToKeyEvents = True
						errors = []
						
						jsGUID = getJoystickGUIDString(sdl2.SDL_JoystickGetDeviceGUID(self.__jsIndex))
						logging.debug("SettingsScreen.draw: creating SDL2 controller mapping using GUID: %s" % jsGUID)
						# remove commas from the name
						jsName = self.__jsName.replace(",", " ")
						jsMap = [jsGUID, jsName]
						for p in self.__jsPrompts:
							m = p.getMap()
							if m:
								jsMap.append(m)
						jsMapStr = ','.join(jsMap)
						logging.debug("SettingsScreen.draw: map: %s" % jsMapStr)
						
						for j in self.__joysticks:
							sdl2.SDL_JoystickClose(j)
							
						rtn = sdl2.SDL_GameControllerAddMapping(jsMapStr)
						if  rtn == 0 or rtn == 1:
							logging.debug("SettingsScreen.draw: mapping loaded OK!")
							try:
								db = GameControllerDb(userGameControllerFile)
								db.load()
								if db.add(jsMapStr):
									db.save()
								else:
									errors.append("Unable to save control pad mapping to file!")
									logging.error("SettingsScreen.draw: unable to add mapping to %s" % userGameControllerFile)
							except IOError, e:
								logging.error(e)
						else:
							errors.append("Could not add SDL2 mapping for control pad!")
							logging.error("SettingsScreen.draw: SDL_GameControllerAddMapping failed for joystick %d, %s" % (self.__jsIndex, self.__jsName))
							
						if len(errors) == 0:
							self.app.updateControlPad(self.__jsIndex)
							self.__descriptionLabel.setText("Configuration complete. Please press the BACK button to return to the previous menu.")
						else:
							self.__descriptionLabel.setText("Configuration failed with the following errors:\n\n%s" % "\n".join(errors))
			
			self.__jsPromptLabel.draw()
			self.__jsTimerLabel.draw()
			self.__gamepadLayoutIcon.draw()
			
	def isBusy(self):
		return self.__isBusy
		
	def processEvent(self, event):
		selected = self.menu.getSelectedItem().getText()
		oldMenuActive = self.menuActive # store state before parent method changes it!
		
		# don't pass up the event if a games scan is in progress
		if event.type == sdl2.SDL_KEYDOWN and selected == "Update Games" and self.__updateDbThread != None:
			if event.key.keysym.sym == sdl2.SDLK_BACKSPACE or event.key.keysym.sym == sdl2.SDLK_HOME:
				if self.__updateDbThread.started and not self.__updateDbThread.done:
					self.setMenuActive(False)
					self.__updateDbThread.stop()
				elif self.__updateDbThread.done:
					self.setMenuActive(False)
					self.__updateDbThread = None
					self.__descriptionLabel.setText(self.__scanText, True)
					self.__scanButton.setFocus(False)
					self.__consoleList.setFocus(True)
					self.__updateDatabaseMenu.toggleAll(True)
					self.__updateDatabaseMenu.setSelected(0)
					if event.key.keysym.sym == sdl2.SDLK_HOME:
						self.__reset()
			return
		elif event.type == sdl2.SDL_KEYDOWN and selected == "Update Badges" and self.__updateAchievementsThread != None:
			if event.key.keysym.sym == sdl2.SDLK_BACKSPACE or event.key.keysym.sym == sdl2.SDLK_HOME:
				if self.__updateAchievementsThread.started and not self.__updateAchievementsThread.done:
					self.setMenuActive(False)
					self.__updateAchievementsThread.stop()
				elif self.__updateAchievementsThread.done:
					self.__updateAchievementsThread = None
					if event.key.keysym.sym == sdl2.SDLK_HOME:
						self.__reset()
		
		super(SettingsScreen, self).processEvent(event)
		
		if oldMenuActive:
			if event.type == sdl2.SDL_KEYDOWN and (event.key.keysym.sym == sdl2.SDLK_RETURN or event.key.keysym.sym == sdl2.SDLK_KP_ENTER):
				logging.debug("SettingsScreen.processEvent: return key trapped for %s" % selected)
				if selected == "Update Games":
					self.__headerLabel.setText(selected)
					self.__updateDatabaseMenu.toggleAll(True)
					self.__descriptionLabel.setText(self.__scanText, True)
					if self.__consoleList != None:
						self.__consoleList.destroy()
					consoleListY = self.__descriptionLabel.y + self.__descriptionLabel.height + 10
					self.__consoleList = self.addUiObject(List(self.renderer, self.__descriptionLabel.x + self.__toggleMargin, consoleListY, 300, self.screenRect[3] - consoleListY, self.__updateDatabaseMenu, self.app.bodyFont, self.app.textColour, self.app.textColour, self.app.menuSelectedBgColour, self.app.menuTextColour))
					self.__consoleList.setFocus(True)
					self.__updateDatabaseMenu.setSelected(0)
					if self.__scanButton == None:
						self.__scanButton = self.addUiObject(Button(self.renderer, self.__consoleList.x + self.__consoleList.width + 200, self.__consoleList.y, 150, 50, "Begin Scan", self.app.bodyFont, self.app.textColour, self.app.menuSelectedBgColour, self.startScan))
						self.__selectAllButton = self.addUiObject(Button(self.renderer, self.__scanButton.x, self.__scanButton.y + self.__scanButton.height + 10, 150, 50, "Select All", self.app.bodyFont, self.app.textColour, self.app.menuSelectedBgColour, self.__updateDatabaseMenu.toggleAll, True))
						self.__deselectAllButton = self.addUiObject(Button(self.renderer, self.__scanButton.x, self.__selectAllButton.y + self.__selectAllButton.height + 10, 150, 50, "Deselect All", self.app.bodyFont, self.app.textColour, self.app.menuSelectedBgColour, self.__updateDatabaseMenu.toggleAll, False))
					self.__scanButton.setFocus(False)
				elif selected == "Update Badges":
					if not self.app.retroAchievementConn:
						self.__descriptionLabel.setText("To track your achievements in your games, please enter your www.retroachievements.org username, password and API key into \\pes\config\pes\pes.ini or %s and then reload PES." % userPesConfigFile)
					else:
						self.__descriptionLabel.setText("Preparing to synchronise PES with your www.retroachievements.org account...")
						if not self.__updateAchievementsThread:
							self.__updateAchievementsThread = RetroAchievementsUpdateThread(self.app.retroAchievementConn, self.app.badgeDir)
							if self.__scanProgressBar == None:
								self.__scanProgressBar = ProgressBar(self.renderer, self.screenRect[0] + self.screenMargin, self.__descriptionLabel.y + self.__descriptionLabel.height + 10, self.screenRect[2] - (self.screenMargin * 2), 40, self.app.lineColour, self.app.menuBackgroundColour)
							else:
								self.__scanProgressBar.setProgress(0)
							self.__isBusy = True
							self.__updateAchievementsThread.start()
				elif selected == "Timezone":
					self.__descriptionLabel.setText("You can change the current timezone from \"%s\" by selecting one from the list below." % self.app.currentTimezone, True)
					if self.__timezoneList == None:
						menuItems = []
						for t in self.app.timezones:
							menuItems.append(MenuItem(t, False, False, self.__setTimezone, t))
						timezoneMenu = Menu(menuItems)
						timezoneListY = self.__descriptionLabel.y + self.__descriptionLabel.height + 10
						self.__timezoneList = self.addUiObject(List(self.renderer, self.__descriptionLabel.x + self.__toggleMargin, timezoneListY, 300, self.screenRect[3] - timezoneListY, timezoneMenu, self.app.bodyFont, self.app.textColour, self.app.textColour, self.app.menuSelectedBgColour, self.app.menuTextColour, drawBackground=True))
					self.__timezoneList.setFocus(True)
				elif selected == "About":
					self.__headerLabel.setText(selected)
					self.__descriptionLabel.setText("Pi Entertainment System version %s\n\nReleased: %s\n\nLicense: Licensed under version 3 of the GNU Public License (GPL)\n\nAuthor: %s\n\nContributors: Eric Smith\n\nCover art: theGamesDB.net\n\nDocumentation: http://pes.mundayweb.com\n\nFacebook: https://www.facebook.com/pientertainmentsystem\n\nHelp: pes@mundayweb.com\n\nIP Address: %s" % (VERSION_NUMBER, VERSION_DATE, VERSION_AUTHOR, self.app.ip), True)
				elif selected == "Joystick Set-Up":
					self.app.doJsToKeyEvents = False
					self.__jsIndex = None
					self.__jsFirstPass = True
					self.__jsTimeRemaining = self.__jsTimeOut
					self.__jsPrompt = 0
					self.__joysticks = []
					self.__jsInitialAxis = []
					for p in self.__jsPrompts:
						p.reset()
					self.__headerLabel.setText(selected)
					self.__descriptionLabel.setText("Please make sure all axis are in their reset positions and then press START on the control pad you wish to configure.\n\nYou can abort the configuration process at any point by pressing BACKSPACE or the BACK button on your TV remote.\n\nIf your joystick/control pad does not have a particular button, press START to skip it.", True)
					if not self.__jsPromptLabel:
						self.__jsPromptLabel = self.addUiObject(Label(self.renderer, self.__descriptionLabel.x, self.__descriptionLabel.y + self.__descriptionLabel.height + 30, self.__jsPrompts[self.__jsPrompt].getPrompt(), self.app.bodyFont, self.app.textColour, fixedWidth=self.screenRect[2] - self.screenMargin))
						self.__jsTimerLabel = self.addUiObject(Label(self.renderer, self.__jsPromptLabel.x, self.__jsPromptLabel.y + self.__jsPromptLabel.height + 10, "Timeout in: %ds" % self.__jsTimeRemaining, self.app.bodyFont, self.app.textColour, fixedWidth=self.screenRect[2] - self.screenMargin))
					else:
						self.__jsPromptLabel.setCoords(self.__descriptionLabel.x, self.__descriptionLabel.y + self.__descriptionLabel.height + 30)
						self.__jsPromptLabel.setText(self.__jsPrompts[self.__jsPrompt].getPrompt())
						self.__jsPromptLabel.setVisible(True)
						self.__jsTimerLabel.setText("Timeout in: %ds" % self.__jsTimeRemaining)
						self.__jsTimerLabel.setCoords(self.__jsPromptLabel.x, self.__jsPromptLabel.y + self.__jsPromptLabel.height + 10)
						self.__jsTimerLabel.setVisible(True)
						
					if not self.__gamepadLayoutIcon:
						try:
							img = Image.open(gamepadLayoutImageFile)
							imgWidth, imgHeight = img.size
						except IOError as e:
							logging.error(e)
							self.app.exit(1)
						self.__gamepadLayoutIcon = self.addUiObject(Icon(self.renderer, self.screenRect[0] + ((self.screenRect[2] - imgWidth) / 2), self.__jsTimerLabel.y + self.__jsTimerLabel.height, imgWidth, imgHeight, gamepadLayoutImageFile, False))
					self.__gamepadLayoutIcon.setVisible(True)
						
					joystickTotal = sdl2.joystick.SDL_NumJoysticks()
					if joystickTotal > 0:
						#logging.debug("PESApp.run: found %d control pads" % joystickTotal)
						for i in xrange(joystickTotal):
							js = sdl2.SDL_JoystickOpen(i)
							self.__joysticks.append(js)
					
				self.__init = False
		else:
				if selected == "Update Games" and self.__consoleList:
					if event.type == sdl2.SDL_KEYDOWN:
						if event.key.keysym.sym == sdl2.SDLK_RIGHT:
							self.__consoleList.setFocus(False)
							self.__scanButton.setFocus(True)
						elif event.key.keysym.sym == sdl2.SDLK_LEFT:
							self.__consoleList.setFocus(True)
							self.__scanButton.setFocus(False)
							self.__selectAllButton.setFocus(False)
							self.__deselectAllButton.setFocus(False)
						else:
							self.__consoleList.processEvent(event)
							self.__scanButton.processEvent(event)
							self.__selectAllButton.processEvent(event)
							self.__deselectAllButton.processEvent(event)
								
						if not self.__consoleList.hasFocus():
							if event.key.keysym.sym == sdl2.SDLK_DOWN:
								if self.__scanButton.hasFocus():
									self.__scanButton.setFocus(False)
									self.__selectAllButton.setFocus(True)
								elif self.__selectAllButton.hasFocus():
									self.__selectAllButton.setFocus(False)
									self.__deselectAllButton.setFocus(True)
								elif self.__deselectAllButton.hasFocus():
									self.__deselectAllButton.setFocus(False)
									self.__scanButton.setFocus(True)
							elif event.key.keysym.sym == sdl2.SDLK_UP:
								if self.__scanButton.hasFocus():
									self.__scanButton.setFocus(False)
									self.__deselectAllButton.setFocus(True)
								elif self.__selectAllButton.hasFocus():
									self.__selectAllButton.setFocus(False)
									self.__scanButton.setFocus(True)
								elif self.__deselectAllButton.hasFocus():
									self.__deselectAllButton.setFocus(False)
									self.__selectAllButton.setFocus(True)
				elif selected == "Timezone" and self.__timezoneList:
					self.__timezoneList.processEvent(event)
				elif selected == "Joystick Set-Up":
					if self.__ignoreJsEvents:
						# don't accept an axis movement as the first input, only accept a button or hat
						if event.type == sdl2.SDL_JOYBUTTONUP or event.type == sdl2.SDL_JOYHATMOTION or (event.type == sdl2.SDL_KEYUP and (event.key.keysym.sym == sdl2.SDLK_RETURN or event.key.keysym.sym == sdl2.SDLK_KP_ENTER)):
							self.__ignoreJsEvents = False
					elif event.type == sdl2.SDL_JOYBUTTONUP and self.__jsPrompt == 0:
						self.__jsIndex = event.jbutton.which
						self.__jsName = sdl2.SDL_JoystickName(self.__joysticks[self.__jsIndex])
						for i in xrange(sdl2.SDL_JoystickNumAxes(self.__joysticks[self.__jsIndex])):
							value = sdl2.SDL_JoystickGetAxis(self.__joysticks[self.__jsIndex], i)
							logging.debug("SettingsScreen.processEvent: inital value for axis %d is: %d" % (i, value))
							if value > JOYSTICK_AXIS_MAX or value < JOYSTICK_AXIS_MIN:
								self.__jsInitialAxis.append(value)
							else:
								self.__jsInitialAxis.append(0)
						self.__descriptionLabel.setText("Configuring joystick #%d, %s\n\nIf you joystick/control pad does not have the button/axis below, please press START to skip it." % (self.__jsIndex, self.__jsName))
						logging.debug("SettingsScreen.processEvent: configuring joystick at %d (%s)" % (self.__jsIndex, self.__jsName))
						self.__jsPrompts[self.__jsPrompt].setValue(JoystickPromptMap.BUTTON, event.jbutton.button)
						self.__jsPrompt += 1
						self.__jsPromptLabel.setText(self.__jsPrompts[self.__jsPrompt].getPrompt())
						self.__jsTimeRemaining = self.__jsTimeOut

		if self.menuActive: # this will be true if parent method trapped a backspace event
			if event.type == sdl2.SDL_KEYDOWN:
				if event.key.keysym.sym == sdl2.SDLK_BACKSPACE:
					logging.debug("SettingsScreen.processEvent: trapping backspace event")
					self.__reset(False)
					
	def __reset(self, resetMenu=True):
		self.__init = True
		self.__headerLabel.setText(self.__defaultHeaderText)
		self.__descriptionLabel.setText(self.__initText, True)
		self.__ignoreJsEvents = True
		if resetMenu:
			self.menu.setSelected(0)
		self.app.doJsToKeyEvents = True
		
	def __setTimezone(self, timezone):
		process = Popen("%s %s" % (self.app.setTimezoneCommand, timezone), stdout=PIPE, stderr=PIPE, shell=True)
		stdout, stderr = process.communicate()
		if process.returncode != 0:
			logging.error("SettingsScreen.__setTimezone: failed to set timezone: %s" % stderr)
			self.app.showMessageBox("Failed to set timezone!", None, None)
			return
		self.app.currentTimezone = timezone
		self.__descriptionLabel.setText("You can change the current timezone from \"%s\" by selecting one from the list below." % self.app.currentTimezone, True)
		self.app.showMessageBox("Timezone changed successfully", None, None)

	def startScan(self):
		logging.debug("SettingsScreen.startScan: beginning scan...")
		self.__isBusy = True
		if self.__scanProgressBar == None:
			self.__scanProgressBar = ProgressBar(self.renderer, self.screenRect[0] + self.screenMargin, self.__descriptionLabel.y + self.__descriptionLabel.height + 10, self.screenRect[2] - (self.screenMargin * 2), 40, self.app.lineColour, self.app.menuBackgroundColour)
		else:
			self.__scanProgressBar.setProgress(0)
		self.__updateDbThread = UpdateDbThread([c.getConsole() for c in self.__updateDatabaseMenu.getToggled()])
		self.__updateDbThread.start()
									
	def stop(self):
		logging.debug("SettingsScreen.stop: deleting UI objects...")
		super(SettingsScreen, self).stop()
		if self.__updateDbThread:
			self.__updateDbThread.stop()
