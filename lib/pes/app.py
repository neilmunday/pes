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
from pes.ui import *
import pes.event
from pes.util import *
from PIL import Image
from collections import OrderedDict
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
import glob
import logging
import math
import ConfigParser
import pes.event
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

CONSOLE_TEXTURE_ALPHA = 50
JOYSTICK_AXIS_MIN = -32000
JOYSTICK_AXIS_MAX = 32000

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
	
	__CONTROL_PAD_BUTTON_REPEAT = 50 # delay in ms between firing events for button holds
	
	def __del__(self):
		logging.debug("PESApp.del: deleting object")
		if getattr(self, "__window", None):
			logging.debug("PESApp.del: window destroyed")
			sdl2.video.SDL_DestroyWindow(self.__window)
			self.__window = None

	def __init__(self, dimensions, fontFile, romsDir, coverartDir, coverartSize, coverartCacheLen, backgroundColour, menuBackgroundColour, headerBackgroundColour, lineColour, textColour, menuTextColour, menuSelectedTextColour):
		super(PESApp, self).__init__()
		self.__dimensions = dimensions
		self.fontFile = fontFile
		self.romsDir = romsDir
		self.coverartDir = coverartDir
		
		ConsoleTask.SCALE_WIDTH = coverartSize
		Thumbnail.CACHE_LEN = coverartCacheLen
		
		self.coverartCacheLen = coverartCacheLen
		self.consoles = []
		self.consoleSurfaces = None
		self.__uiObjects = [] # list of UI objects created so we can destroy them upon exit
		
		self.lineColour = sdl2.SDL_Color(lineColour[0], lineColour[1], lineColour[2])
		self.backgroundColour = sdl2.SDL_Color(backgroundColour[0], backgroundColour[1], backgroundColour[2])
		self.headerBackgroundColour = sdl2.SDL_Color(headerBackgroundColour[0], headerBackgroundColour[1], headerBackgroundColour[2])
		self.menuBackgroundColour = sdl2.SDL_Color(menuBackgroundColour[0], menuBackgroundColour[1], menuBackgroundColour[2])
		self.menuTextColour = sdl2.SDL_Color(menuTextColour[0], menuTextColour[1], menuTextColour[2])
		self.menuSelectedTextColour = sdl2.SDL_Color(menuSelectedTextColour[0], menuSelectedTextColour[1], menuSelectedTextColour[2])
		self.menuSelectedBgColour = self.lineColour
		self.textColour = sdl2.SDL_Color(textColour[0], textColour[1], textColour[2])
		
		self.__headerHeight = 30
		self.__footerHeight = 0
		
		self.doKeyEvents = True
		
	def exit(self, rtn=0):
		# tidy up
		logging.debug("PESApp.exit: stopping screens...")
		for s in self.screens:
			self.screens[s].stop()
		logging.debug("PESApp.exit: purging cached surfaces...")
		for console, surface in self.consoleSurfaces.iteritems():
			logging.debug("PESApp.exit: unloading surface for %s..." % console)
			sdl2.SDL_FreeSurface(surface)
		logging.debug("PESApp.exit: tidying up...")
		#sdl2.SDL_DestroyTexture(self.__gamepadTexture)
		#sdl2.SDL_DestroyTexture(self.__networkTexture)
		self.__gamepadIcon.destroy()
		self.__networkIcon.destroy()
		Thumbnail.destroyTextures()
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
		
	def initScreens(self):
		logging.debug("PESApp.initScreens: initialising screens...")
		self.screens["Home"] = HomeScreen(self, self.renderer, self.menuRect, self.screenRect)
		self.screens["Settings"] = SettingsScreen(self, self.renderer, self.menuRect, self.screenRect)
		consoleScreens = 0
		for c in self.consoles:
			if c.getGameTotal() > 0:
				self.screens["Console %s" % c.getName()] = ConsoleScreen(self, self.renderer, self.menuRect, self.screenRect, c)
				consoleScreens += 1
		logging.debug("PESApp.initScreens: initialised %d screens of which %d are console screens" % (len(self.screens), consoleScreens))
		self.screenStack = ["Home"]
	
	def initSurfaces(self):
		
		if self.consoleSurfaces != None:
			return
		
		self.consoleSurfaces = {}
		logging.debug("PESApp.initSurfaces: pre-loading console images...")
		for c in self.consoles:
			surface = sdl2.sdlimage.IMG_Load(c.getImg())
			if surface == None:
				logging.error("PESApp.initSurfaces: failed to load image: %s" % c.getImg())
				self.exit(1)
			self.consoleSurfaces[c.getName()] = surface
			logging.debug("PESApp.initSurfaces: pre-loaded %s surface from %s" % (c.getName(), c.getImg()))
			
	@staticmethod
	def getMupen64PlusConfigButtonValue(controller, button):
		bind = sdl2.SDL_GameControllerGetBindForButton(controller, button)
		if bind:
			if bind.bindType == sdl2.SDL_CONTROLLER_BINDTYPE_BUTTON:
				return "B%d" % bind.value.button
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
				return PESApp.getRetroArchConfigAxisValue(param, controller, button)
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
			
	def playGame(self, game):
		emulator = game.getConsole().getEmulator()
		logging.debug("PESApp.playGame: emulator is %s" % emulator)
		if emulator == "RetroArch":
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
								f.write("input_driver = \"udev\"\n")
								# buttons
								f.write(self.getRetroArchConfigButtonValue("input_a", c, sdl2.SDL_CONTROLLER_BUTTON_A))
								f.write(self.getRetroArchConfigButtonValue("input_b", c, sdl2.SDL_CONTROLLER_BUTTON_B))
								f.write(self.getRetroArchConfigButtonValue("input_x", c, sdl2.SDL_CONTROLLER_BUTTON_X))
								f.write(self.getRetroArchConfigButtonValue("input_y", c, sdl2.SDL_CONTROLLER_BUTTON_Y))
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
								f.write(self.getRetroArchConfigButtonValue("input_enable_hotkey", c, sdl2.SDL_CONTROLLER_BUTTON_BACK))
								f.write(self.getRetroArchConfigButtonValue("input_exit_emulator", c, sdl2.SDL_CONTROLLER_BUTTON_START))
								f.write(self.getRetroArchConfigButtonValue("input_save_state", c, sdl2.SDL_CONTROLLER_BUTTON_A))
								f.write(self.getRetroArchConfigButtonValue("input_load_state", c, sdl2.SDL_CONTROLLER_BUTTON_B))
								f.write("input_pause_toggle = \"nul\"\n")
						sdl2.SDL_GameControllerClose(c)
		elif emulator == "Mupen64Plus":
			joystickTotal = sdl2.joystick.SDL_NumJoysticks()
			if joystickTotal > 0:
				if not os.path.exists(userMupen64PlusConfFile):
					logging.error("PESApp.playGame: could not open %s" % userMupen64PlusConfFile)
					self.exit(1)
				configParser = ConfigParser.SafeConfigParser()
				configParser.optionxform = str # make options case sensitive
				configParser.read(userMupen64PlusConfFile)
				hotkey = self.getMupen64PlusConfigButtonValue(self.__controlPad, sdl2.SDL_CONTROLLER_BUTTON_BACK)
				if configParser.has_section('CoreEvents'):
					configParser.set('CoreEvents', 'Joy Mapping Stop', 'J%d%s/%s' % (self.__controlPadIndex, hotkey, self.getMupen64PlusConfigButtonValue(self.__controlPad, sdl2.SDL_CONTROLLER_BUTTON_START)))
					configParser.set('CoreEvents', 'Joy Mapping Save State', 'J%d%s/%s' % (self.__controlPadIndex, hotkey, self.getMupen64PlusConfigButtonValue(self.__controlPad, sdl2.SDL_CONTROLLER_BUTTON_A)))
					configParser.set('CoreEvents', 'Joy Mapping Load State', 'J%d%s/%s' % (self.__controlPadIndex, hotkey, self.getMupen64PlusConfigButtonValue(self.__controlPad, sdl2.SDL_CONTROLLER_BUTTON_B)))
				logging.debug("PESApp.playGame: writing Mupen64Plus config to %s" % userMupen64PlusConfFile)
				with open(userMupen64PlusConfFile, 'wb') as f:
					configParser.write(f)
		
		logging.info("loading game: %s" % game.getName())
		game.setPlayCount()
		game.setLastPlayed()
		game.save()
		launchString = game.getCommand()
		logging.debug("PESApp.playGame: launch string: %s" % launchString)
		self.runCommand(launchString)
		#self.exit(0)
        
	def run(self):
		#sdl2.SDL_Init(sdl2.SDL_INIT_EVERYTHING)
		sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_GAMECONTROLLER)
		sdl2.SDL_ShowCursor(0)
		sdl2.sdlttf.TTF_Init()
		imgFlags = sdl2.sdlimage.IMG_INIT_JPG | sdl2.sdlimage.IMG_INIT_PNG
		initted = sdl2.sdlimage.IMG_Init(imgFlags)
		if initted != imgFlags:
			logging.error("PESApp.run: failed to initialise SDL_Image")
			self.exit(1)
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
			self.__window = sdl2.video.SDL_CreateWindow('PES', sdl2.video.SDL_WINDOWPOS_UNDEFINED, sdl2.video.SDL_WINDOWPOS_UNDEFINED, self.__dimensions[0], self.__dimensions[1], self.__dimensions[0], self.__dimensions[1], sdl2.video.SDL_WINDOW_FULLSCREEN_DESKTOP)
		else:
			# windowed
			logging.debug("PESApp.run: running windowed")
			self.__window = sdl2.video.SDL_CreateWindow('PES', sdl2.video.SDL_WINDOWPOS_UNDEFINED, sdl2.video.SDL_WINDOWPOS_UNDEFINED, self.__dimensions[0], self.__dimensions[1], 0)
		
		self.menuWidth = 200
		self.menuHeight = self.__dimensions[1] - self.__footerHeight - self.__headerHeight
		
		self.menuRect = [0, self.__headerHeight + 1, self.menuWidth, self.__dimensions[1] - self.__headerHeight + 1]
		self.screenRect = [self.menuWidth + 1, self.__headerHeight + 1, self.__dimensions[0] - self.menuWidth + 1, self.__dimensions[1] - self.__headerHeight + 1]
		
		logging.debug("PESApp.run: window dimensions: (%d, %d)" % (self.__dimensions[0], self.__dimensions[1]))
		
		self.splashFont = sdl2.sdlttf.TTF_OpenFont(self.fontFile, 50)
		self.menuFont = sdl2.sdlttf.TTF_OpenFont(self.fontFile, 20)
		self.headerFont = sdl2.sdlttf.TTF_OpenFont(self.fontFile, 22)
		self.titleFont = sdl2.sdlttf.TTF_OpenFont(self.fontFile, 20)
		self.bodyFont = sdl2.sdlttf.TTF_OpenFont(self.fontFile, 18)
		
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
		
		self.__gamepadIcon = Icon(self.renderer, dateLabel.x, dateLabel.y, 32, 32, gamepadImageFile)
		self.__gamepadIcon.setVisible(False)
		
		self.__networkIcon = Icon(self.renderer, dateLabel.x - 42, dateLabel.y, 32, 32, networkImageFile)
		self.ip = None
		defaultInterface = getDefaultInterface()
		if defaultInterface:
			self.ip = getIPAddress(defaultInterface)
			logging.debug("PESApp.run: default interface: %s, IP address: %s" % (defaultInterface, self.ip))
		else:
			self.__networkIcon.setVisible(False)
		
		self.__controlPad = None
		self.__controlPadIndex = None
		tick = sdl2.timer.SDL_GetTicks()
		downTick = tick
		
		while running:
			events = sdl2.ext.get_events()
			for event in events:
				
				if (event.type == sdl2.SDL_CONTROLLERBUTTONDOWN or event.type == sdl2.SDL_CONTROLLERBUTTONUP) and self.__controlPad and event.cbutton.which == self.__controlPadIndex:
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
				
				# device add/remove isn't reliable at the moment so don't use it for now
				#if event.type == sdl2.SDL_CONTROLLERDEVICEADDED:
				#	print "ADDED %d" % event.cdevice.which
				#elif event.type == sdl2.SDL_CONTROLLERDEVICEREMOVED:
				#	print "REMOVED %d" % event.cdevice.which

				if event.type == pes.event.EVENT_TYPE:
					(t, d1, d2) = pes.event.decodePesEvent(event)
					logging.debug("PESApp.run: trapping PES Event")
					if not loading and t == pes.event.EVENT_DB_UPDATE:
						for c in self.consoles:
							c.refresh()
							screenName = "Console %s" % c.getName()
							if c.getGameTotal() > 0:
								if screenName in self.screens:
									self.screens[screenName].refresh()
								else:
									logging.debug("PESApp.run adding ConsoleScreen for %s following database update" % c.getName())
									self.screens[screenName] = ConsoleScreen(self, self.renderer, self.menuRect, self.screenRect, c)
								
						self.screens["Home"].refreshMenu()
						Thumbnail.destroyTextures()
					elif t == pes.event.EVENT_RESOURCES_LOADED:
						pass
				
				if not loading:
					# keyboard events
					if self.doKeyEvents and event.type == sdl2.SDL_KEYDOWN:
						if event.key.keysym.sym == sdl2.SDLK_BACKSPACE:
							logging.debug("PESApp.run: trapping backspace key event")
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
							# pop all screens and return home
							while len(self.screenStack) > 1:
								s = self.screenStack.pop()
								self.screens[s].setMenuActive(False)
							self.setScreen("Home", False)
							self.screens["Home"].setMenuActive(True)
							self.screens["Home"].menu.setSelected(0)
							self.screens["Home"].update()
					self.screens[self.screenStack[-1]].processEvent(event)
								
				if event.type == sdl2.SDL_KEYDOWN and event.key.keysym.sym == sdl2.SDLK_ESCAPE:
					logging.debug("PESApp.run: trapping escape key event")
					running = False
					break
					
				# joystick events
				if event.type == sdl2.SDL_QUIT:
					running = False
					break
				
			sdl2.SDL_SetRenderDrawColor(self.renderer, self.backgroundColour.r, self.backgroundColour.g, self.backgroundColour.b, 255)
			sdl2.SDL_RenderClear(self.renderer)
			
			if loading:
				if not loadingThread.started:
					loadingThread.start()
				tick = sdl2.timer.SDL_GetTicks()
				if splashTextureAlpha < 255 and tick - lastTick > 100:
					splashTextureAlpha += 25
					if splashTextureAlpha > 255:
						splashTextureAlpha = 255
					lastTick = tick
				splashLabel.setAlpha(splashTextureAlpha)
				splashLabel.draw()
				if loadingThread.done and splashTextureAlpha >= 255:
					loading = False
					splashLabel.destroy()
					statusLabel.destroy()
				else:
					progressBar.setProgress(loadingThread.progress)
					progressBar.draw()
					if statusLabel.setText(loadingThread.status):
						statusLabel.x = int((self.__dimensions[0] - statusLabel.width) / 2)
					statusLabel.draw()
			else:
				sdl2.sdlgfx.boxRGBA(self.renderer, 0, 0, self.__dimensions[0], self.__headerHeight, self.headerBackgroundColour.r, self.headerBackgroundColour.g, self.headerBackgroundColour.b, 255) # header bg
				headerLabel.draw()
				
				self.screens[self.screenStack[-1]].draw()
			
				now = datetime.now()
				dateLabel.setText(now.strftime("%H:%M:%S %d/%m/%Y"))
				dateLabel.draw()
				
				#iconX = dateLabel.x - 10
				
				if self.__networkIcon.visible:
					self.__networkIcon.draw()
					
				if self.__gamepadIcon.visible:
					if self.__networkIcon.visible:
						self.__gamepadIcon.x = self.__networkIcon.x - 37
					else:
						self.__gamepadIcon.x = dateLabel.x - 42
					self.__gamepadIcon.draw()
				
				sdl2.sdlgfx.rectangleRGBA(self.renderer, 0, self.__headerHeight, self.__dimensions[0], self.__headerHeight, self.lineColour.r, self.lineColour.g, self.lineColour.b, 255) # header line
				
				# detect joysticks
				if self.__controlPad and not sdl2.SDL_GameControllerGetAttached(self.__controlPad):
					logging.debug("PESApp.run: player 1 control pad no longer attached!")
					sdl2.SDL_GameControllerClose(self.__controlPad)
					self.__controlPad = None
					self.__controlPadIndex = None
					self.__gamepadIcon.setVisible(False)
				else:
					# is the user holding down a button?
					# note: we only care about directional buttons
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
				
				if sdl2.timer.SDL_GetTicks() - tick > 1000:
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
										self.__controlPad = c
										self.__controlPadIndex = i
										close = False
										self.__gamepadIcon.setVisible(True)
										#print sdl2.SDL_GameControllerMapping(c)
								if close:
									sdl2.SDL_GameControllerClose(c)
			
			sdl2.SDL_RenderPresent(self.renderer)
			
		self.exit(0)
		
	def runCommand(self, command):
		logging.debug("PESApp.runCommand: about to write to: %s" % scriptFile)
		logging.debug("PESApp.runCommand: command: %s" % command)
		execLog = "%s%sexec.log" % (userLogDir, os.sep)
		with open(scriptFile, 'w') as f:
			f.write("echo running %s\n" % command)
			f.write("echo see %s for console output\n" % execLog)
			f.write("%s &> %s\n" % (command, execLog))
			f.write("exec %s%sbin%spes %s\n" % (baseDir, os.sep, os.sep, ' '.join(sys.argv[1:])))
		self.exit(0)
		
	def setScreen(self, screen, doAppend=True):
		if not screen in self.screens:
			logging.warning("PESApp.setScreen: invalid screen selection \"%s\"" % screen)
		else:
			logging.debug("PESApp.setScreen: setting current screen to \"%s\"" % screen)
			logging.debug("PESApp.setScreen: adding screen \"%s\" to screen stack" % screen)
			if doAppend:
				self.screenStack.append(screen)
			self.screens[screen].setMenuActive(True)
			
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
			cur.execute('CREATE TABLE IF NOT EXISTS `games`(`game_id` INTEGER PRIMARY KEY, `api_id` INT, `exists` INT, `console_id` INT, `name` TEXT, `cover_art` TEXT, `game_path` TEXT, `overview` TEXT, `released` INT, `last_played` INT, `added` INT, `favourite` INT(1), `play_count` INT, `size` INT )')
			cur.execute('CREATE INDEX IF NOT EXISTS "games_index" on games (game_id ASC)')
			cur.execute('CREATE TABLE IF NOT EXISTS `consoles`(`console_id` INTEGER PRIMARY KEY, `api_id` INT, `name` TEXT)')
			cur.execute('CREATE INDEX IF NOT EXISTS "console_index" on consoles (console_id ASC)')
			cur.execute('CREATE TABLE IF NOT EXISTS `games_catalogue` (`short_name` TEXT, `full_name` TEXT)')
			cur.execute('CREATE INDEX IF NOT EXISTS "games_catalogue_index" on games_catalogue (short_name ASC)')
			
			self.progress = 20
			
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
				for section in sections:
					if catalogueConfigParser.has_option(section, 'full_name'):
						fullName = catalogueConfigParser.get(section, 'full_name')
						logging.debug("PESLoadingThread.run: inserting game into catalogue: %s -> %s" % (section, fullName))
						cur.execute('INSERT INTO `games_catalogue` (`short_name`, `full_name`) VALUES ("%s", "%s");' % (section, fullName))
					else:
						logging.error("PESLoadingThread.run: games catalogue section \"%s\" has no \"full_name\" option!" % section)
					i += 1.0
					self.progress = 20 + (20 * (i / sectionTotal))
						
			con.commit()
		except sqlite3.Error, e:
			pesExit("Error: %s" % e.args[0], True)
		finally:
			if con:
				con.close()
				
		self.progress = 40
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
				consoleApiId = configParser.getint(c, 'api_id')
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
				
				console = Console(c, consoleId, consoleApiId, extensions, consolePath, command, userPesDb, consoleImg, nocoverart, consoleCoverartDir, emulator)
				if configParser.has_option(c, 'ignore_roms'):
					for r in configParser.get(c, 'ignore_roms').split(','):
						console.addIgnoreRom(r.strip())
				if console.isNew():
					console.save()
				self.app.consoles.append(console)
				i += 1
				self.progress = 40 + (20 * (i / supportedConsoleTotal))
			except ConfigParser.NoOptionError, e:
				logging.error('PESLoadingThread.run: error parsing config file %s: %s' % (userConsolesConfigFile, e.message))
				self.done = True
				self.app.exit(1)
				return
			
		self.progress = 60
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
		self.menu.setSelected(0)
		self.__uiObjects = []
		self.__menuList = self.addUiObject(List(self.renderer, self.__menuMargin + self.menuRect[0], self.menuRect[1] + self.__menuTopMargin, self.menuRect[2] - (self.__menuMargin * 2), self.menuRect[3] - (self.menuRect[1] + self.__menuTopMargin), self.menu, self.app.menuFont, self.app.menuTextColour, self.app.menuSelectedTextColour, self.app.menuSelectedBgColour, self.app.menuTextColour, List.SCROLLBAR_DISABLED, labelMargin=0))
		self.__menuList.setFocus(True)
		
	def addUiObject(self, o):
		if o not in self.__uiObjects:
			self.__uiObjects.append(o)
		return o
		
	def draw(self):
		self.drawMenu()
		self.drawScreen()
		
	def drawMenu(self):
		sdl2.sdlgfx.boxRGBA(self.renderer, self.menuRect[0], self.menuRect[1], self.menuRect[0] + self.menuRect[2], self.menuRect[1] + self.menuRect[3], self.app.menuBackgroundColour.r, self.app.menuBackgroundColour.g, self.app.menuBackgroundColour.b, 255)
		self.__menuList.draw()
	
	def drawScreen(self):
		sdl2.sdlgfx.boxRGBA(self.renderer, self.screenRect[0], self.screenRect[1], self.screenRect[0] + self.screenRect[2], self.screenRect[1] + self.screenRect[3], self.app.backgroundColour.r, self.app.backgroundColour.g, self.app.backgroundColour.b, 255)
	
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
		self.menu.setSelected(0, True)
	
	def setMenuActive(self, active):
		self.menuActive = active
		self.__menuList.setFocus(True)
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
			MenuItem("Recently Played"),
			MenuItem("Recently Added"),
			MenuItem("Favourites"),
			MenuItem("Most Played"),
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
		self.__gameInfoLabel = None
		self.__gameOverviewLabel = None
		self.__previewThumbnail = None
		self.__listX = self.screenRect[0] + self.screenMargin
		self.__listY = self.__titleLabel.y + (self.__titleLabel.height * 2)
		self.__listWidth = 300
		self.__listHeight = self.screenRect[1] + self.screenRect[3] - self.__listY - self.screenMargin
		self.__previewThumbnailX = self.__listX + self.__listWidth
		self.__previewThumbnailWidth, self.__previewThumbnailHeight = scaleImage((self.__noCoverArtWidth, self.__noCoverArtHeight), (self.screenRect[0] + self.screenRect[2] - self.__previewThumbnailX - 50,
 int((self.screenRect[3] - self.screenRect[1]) / 2)))
		self.__previewThumbnailX += int((((self.screenRect[0] + self.screenRect[2]) - self.__previewThumbnailX) / 2) - (self.__previewThumbnailWidth / 2))
		self.__previewThumbnailY = self.__listY
		self.__gameInfoLabelX = self.__listX + self.__listWidth + 50
		self.__gameInfoLabelY = self.__previewThumbnailY + self.__previewThumbnailHeight + 10
		self.__gameInfoLabelWidth = self.screenRect[0] + self.screenRect[2] - self.__gameInfoLabelX - 5
		self.__gameInfoLabelHeight = 5 * sdl2.sdlttf.TTF_FontHeight(self.app.bodyFont)
		self.__gameInfoLabel = self.addUiObject(Label(self.renderer, self.__gameInfoLabelX, self.__gameInfoLabelY, " ", self.app.bodyFont, self.app.textColour, fixedWidth=self.__gameInfoLabelWidth,
 fixedHeight=self.__gameInfoLabelHeight, bgColour=self.app.menuTextColour, bgAlpha=50))
		self.__gameOverviewLabelX = self.__gameInfoLabelX
		self.__gameOverviewLabelY = self.__gameInfoLabelY + self.__gameInfoLabelHeight
		self.__gameOverviewLabel = self.addUiObject(Label(self.renderer, self.__gameInfoLabelX, self.__gameOverviewLabelY, " ", self.app.bodyFont, self.app.textColour, fixedWidth=self.__gameInfoLabelWidth, fixedHeight=(self.screenRect[1] + self.screenRect[3] - self.__gameOverviewLabelY - self.screenMargin), autoScroll=True, bgColour=self.app.menuTextColour, bgAlpha=50))
		self.__recentlyAddedThumbPanel = None
		self.__recentlyPlayedThumbPanel = None
		self.__mostPlayedThumbPanel = None
		self.__favouriteThumbPanel = None
		self.refresh()
		logging.debug("ConsoleScreen.init: initialised for %s" % self.__consoleName)
		
	def __createMenu(self, games):
		menu = Menu([])
		for g in games:
			g.refresh()
			m = GameMenuItem(g, False, True, self.app.playGame, g)
			m.toggle(g.isFavourite())
			menu.addItem(m)
		return menu
		
	def __createPreviewThumbnail(self, game):
		if self.__previewThumbnail == None:
			self.__previewThumbnail = self.addUiObject(Thumbnail(self.renderer, self.__previewThumbnailX, self.__previewThumbnailY, self.__previewThumbnailWidth, self.__previewThumbnailHeight, game, self.app.bodyFont, self.app.textColour, False))
		
	def drawScreen(self):
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
			elif selectedText == "Most Played":
				if self.__mostPlayedGamesTotal > 0 and self.__mostPlayedThumbPanel:
					self.__mostPlayedThumbPanel.draw()
				else:
					self.__noGamesFoundLabel.draw()
			elif selectedText == "All":
				self.__descriptionLabel.draw()
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
		return "Released: %s\nPlay Count: %d\nLast Played: %s\nSize: %s\nOverview:" % (game.getReleased("%d/%m/%Y"), playCount, lastPlayed, game.getSize(True))
			
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
				else:
					if selectedText == "All":
						self.__allGamesList.processEvent(event)
					elif selectedText == "Recently Added":
						self.__recentlyAddedGamesList.processEvent(event)
					elif selectedText == "Favourites":
						if self.__favouritesList:
							self.__favouritesList.processEvent(event)
					elif selectedText == "Most Played":
						if self.__mostPlayedList:
							self.__mostPlayedList.processEvent(event)
					elif selectedText == "Recently Played":
						if self.__recentlyPlayedList:
							self.__recentlyPlayedList.processEvent(event)
						
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
		self.__allGames = self.__console.getGames()
		self.__allGamesTotal = len(self.__allGames)
		if self.__allGamesList:
			self.__allGamesList.setMenu(self.__createMenu(self.__allGames))
		self.__recentlyAddedGames = self.__console.getRecentlyAddedGames()
		self.__recentlyAddedGamesTotal = len(self.__recentlyAddedGames)
		if self.__recentlyAddedGamesList:
			self.__recentlyAddedGamesList.setMenu(self.__createMenu(self.__recentlyAddedGames))
		if self.__recentlyAddedThumbPanel:
			self.__recentlyAddedThumbPanel.setGames(self.__recentlyAddedGames[0:self.__showThumbs])
		else:
			self.__recentlyAddedThumbPanel = self.addUiObject(ThumbnailPanel(self.renderer, self.__listX, self.__listY, self.screenRect[2] - self.screenMargin,  self.__recentlyAddedGames[0:self.__showThumbs], self.app.bodyFont, self.app.textColour, self.app.menuSelectedBgColour, self.__thumbXGap, True, self.__showThumbs))
		self.__mostPlayedGames = self.__console.getMostPlayedGames()
		self.__mostPlayedGamesTotal = len(self.__mostPlayedGames)
		if self.__mostPlayedGamesTotal > 0:
			if self.__mostPlayedList:
				self.__mostPlayedList.setMenu(self.__createMenu(self.__mostPlayedGames))
			if self.__mostPlayedThumbPanel:
				self.__mostPlayedThumbPanel.setGames(self.__mostPlayedGames[0:self.__showThumbs])
			else:
				self.__mostPlayedThumbPanel = self.addUiObject(ThumbnailPanel(self.renderer, self.__listX, self.__listY, self.screenRect[2] - self.screenMargin,  self.__mostPlayedGames[0:self.__showThumbs], self.app.bodyFont, self.app.textColour, self.app.menuSelectedBgColour, self.__thumbXGap, True, self.__showThumbs))
		self.__recentlyPlayedGames = self.__console.getRecentlyPlayedGames()
		self.__recentlyPlayedGamesTotal = len(self.__recentlyPlayedGames)
		if self.__recentlyPlayedGamesTotal > 0:
			if self.__recentlyPlayedList:
				self.__recentlyPlayedList.setMenu(self.__createMenu(self.__recentlyPlayedGames))
			if self.__recentlyPlayedThumbPanel:
				self.__recentlyPlayedThumbPanel.setGames(self.__recentlyPlayedGames[0:self.__showThumbs])
			else:
				self.__recentlyPlayedThumbPanel = self.addUiObject(ThumbnailPanel(self.renderer, self.__listX, self.__listY, self.screenRect[2] - self.screenMargin,  self.__recentlyPlayedGames[0:self.__showThumbs], self.app.bodyFont, self.app.textColour, self.app.menuSelectedBgColour, self.__thumbXGap, True, self.__showThumbs))
		self.__updateFavourites()
		
	def __updateFavourites(self):
		self.__favouriteGames = self.__console.getFavourites()
		self.__favouriteGamesTotal = len(self.__favouriteGames)
		if self.__favouriteGamesTotal > 0:
			if self.__favouritesList:
				self.__favouritesList.setMenu(self.__createMenu(self.__favouriteGames))
			if self.__favouriteThumbPanel:
				self.__favouriteThumbPanel.setGames(self.__favouriteGames[0:self.__showThumbs])
			else:
				self.__favouriteThumbPanel = self.addUiObject(ThumbnailPanel(self.renderer, self.__listX, self.__listY, self.screenRect[2] - self.screenMargin,  self.__favouriteGames[0:self.__showThumbs], self.app.bodyFont, self.app.textColour, self.app.menuSelectedBgColour, self.__thumbXGap, True, self.__showThumbs))
		
	def stop(self):
		super(ConsoleScreen, self).stop()
		logging.debug("ConsoleScreen.stop: deleting textures for %s..." % self.__consoleName)
		if self.__consoleTexture:
			sdl2.SDL_DestroyTexture(self.__consoleTexture)
	
class HomeScreen(Screen):
	
	def __init__(self, app, renderer, menuRect, screenRect):
		super(HomeScreen, self).__init__(app, renderer, "Home", Menu([MenuItem("Home")]), menuRect, screenRect)
		for c in self.app.consoles:
			if c.getGameTotal() > 0:
				self.menu.addItem(ConsoleMenuItem(c, False, False, self.app.setScreen, "Console %s" % c.getName()))
		self.menu.addItem(MenuItem("Settings", False, False, self.app.setScreen, "Settings"))
		self.menu.addItem(MenuItem("Reboot"))
		self.menu.addItem(MenuItem("Power Off"))
		self.menu.addItem(MenuItem("Exit", False, False, self.app.exit))
		self.__thumbXGap = 20
		self.__thumbYGap = 10
		self.__showThumbs = 10
		self.__desiredThumbWidth = int((screenRect[2] - (self.__showThumbs * self.__thumbXGap)) / self.__showThumbs)
		self.__consoleTexture = None
		self.__consoleSelected = False
		self.__headerLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.screenRect[1], "Welcome to PES!", self.app.titleFont, self.app.textColour))
		self.__welcomeText = "The home screen provides you with quick access to your favourite, new additions and most recently played games."
		self.__descriptionLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.__headerLabel.y + (self.__headerLabel.height * 2), self.__welcomeText, self.app.bodyFont, self.app.textColour, fixedWidth=self.wrap))
		self.__recentlyAddedText = "Recently Added"
		self.__recentlyAddedLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.__headerLabel.y + (self.__headerLabel.height * 2), self.__recentlyAddedText, self.app.bodyFont, self.app.textColour, fixedWidth=self.wrap))
		self.__recentlyPlayedLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.__headerLabel.y + (self.__headerLabel.height * 2), "Recently Played", self.app.bodyFont, self.app.textColour, fixedWidth=self.wrap))
		
		self.__recentlyAddedThumbPanel = None
		self.__recentlyPlayedThumbPanel = None
		
		#logging.debug("HomeScreen.init: thumbWidth %d" % self.__thumbWidth)
		logging.debug("HomeScreen.init: initialised")
			
	def drawScreen(self):
		super(HomeScreen, self).drawScreen()
		
		self.__headerLabel.draw()
		if self.__consoleSelected:
			sdl2.SDL_RenderCopy(self.renderer, self.__consoleTexture, None, sdl2.SDL_Rect(self.screenRect[0], self.screenRect[1], self.screenRect[2], self.screenRect[3]))
			self.__recentlyAddedLabel.draw()
			self.__recentlyAddedThumbPanel.draw()
			self.__recentlyPlayedLabel.draw()
			if self.__recentlyPlayedThumbPanel:
				self.__recentlyPlayedThumbPanel.draw()
		else:
			self.__descriptionLabel.draw()

	def processEvent(self, event):
		super(HomeScreen, self).processEvent(event)
		if self.menuActive and event.type == sdl2.SDL_KEYDOWN and (event.key.keysym.sym == sdl2.SDLK_UP or event.key.keysym.sym == sdl2.SDLK_DOWN):
			self.update()
		
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
				logging.debug("HomeScreen.refreshMenu: inserting %s" % c.getName())
				self.menu.insertItem(len(self.menu.getItems()) - 4, ConsoleMenuItem(c, False, False, self.app.setScreen, "Console %s" % c.getName()))
		self.menu.setSelected(0, deselectAll=True)
		self.update()
		
	def stop(self):
		super(HomeScreen, self).stop()
		logging.debug("HomeScreen.stop: deleting textures...")
		sdl2.SDL_DestroyTexture(self.__consoleTexture)
		
	def update(self):
		selected = self.menu.getSelectedItem()
		if isinstance(selected, ConsoleMenuItem):
			console = selected.getConsole()
			consoleName = console.getName()
			if self.__consoleTexture:
				sdl2.SDL_DestroyTexture(self.__consoleTexture)
			self.__consoleTexture = sdl2.SDL_CreateTextureFromSurface(self.renderer, self.app.consoleSurfaces[consoleName])
			sdl2.SDL_SetTextureAlphaMod(self.__consoleTexture, CONSOLE_TEXTURE_ALPHA)
			self.__headerLabel.setText(consoleName)
			# get recently added
			logging.debug("HomeScreen.drawScreen: getting recently added games for %s..." % consoleName)
			games = console.getRecentlyAddedGames(0, self.__showThumbs)
			thumbX = self.screenRect[0] + self.screenMargin
			if len(games) > 0:
				if self.__recentlyAddedThumbPanel:
					self.__recentlyAddedThumbPanel.setGames(games)
				else:
					self.__recentlyAddedThumbPanel = self.addUiObject(ThumbnailPanel(self.renderer, self.screenRect[0] + self.screenMargin, self.__recentlyAddedLabel.y + self.__recentlyAddedLabel.height + self.__thumbYGap, self.screenRect[2] - self.screenMargin, games, self.app.bodyFont, self.app.textColour, self.app.menuSelectedBgColour, self.__thumbXGap, True, self.__showThumbs))
				self.__recentlyPlayedLabel.y = self.__recentlyAddedThumbPanel.y + self.__recentlyAddedThumbPanel.height + 50
			else:
				self.__recentlyAddedLabel.setText(self.__recentlyAddedText + ": None added")
			# get recently added
			logging.debug("HomeScreen.drawScreen: getting recently played games for %s..." % consoleName)
			games = console.getRecentlyPlayedGames(0, self.__showThumbs)
			if len(games) > 0:
				if self.__recentlyPlayedThumbPanel:
					self.__recentlyPlayedThumbPanel.setGames(games)
				else:
					self.__recentlyPlayedThumbPanel = self.addUiObject(ThumbnailPanel(self.renderer, self.screenRect[0] + self.screenMargin, self.__recentlyPlayedLabel.y + self.__recentlyPlayedLabel.height + self.__thumbYGap, self.screenRect[2] - self.screenMargin, games, self.app.bodyFont, self.app.textColour, self.app.menuSelectedBgColour, self.__thumbXGap, True, self.__showThumbs))
				self.__recentlyPlayedLabel.setVisible(True)
				self.__recentlyPlayedThumbPanel.setVisible(True)
			else:
				if self.__recentlyPlayedThumbPanel:
					self.__recentlyPlayedThumbPanel.setVisible(False)
				self.__recentlyPlayedLabel.setVisible(False)
				
			self.__consoleSelected = True
		else:
			self.__consoleSelected = False
			if selected.getText() == "Home":
				self.__headerLabel.setText("Welcome to PES!")
				self.__descriptionLabel.setText(self.__welcomeText)
			elif selected.getText() == "Reboot":
				self.__headerLabel.setText("Reboot")
				self.__descriptionLabel.setText("Select this menu item to reboot your system.")
			elif selected.getText() == "Exit":
				self.__headerLabel.setText("Exit")
				self.__descriptionLabel.setText("Select this menu item to exit the PES GUI and return to the command line.")
			elif selected.getText() == "Settings":
				self.__headerLabel.setText("Settings")
				self.__descriptionLabel.setText("Select this menu item to customise PES and to add ROMs to PES' database.")
			elif selected.getText() == "Power Off":
				self.__headerLabel.setText("Power Off")
				self.__descriptionLabel.setText("Select this menu item to power off your system.")
		
class SettingsScreen(Screen):
	
	def __init__(self, app, renderer, menuRect, screenRect):
		super(SettingsScreen, self).__init__(app, renderer, "Settings", Menu([
			MenuItem("Update Database"),
			MenuItem("Joystick Set-Up"),
			MenuItem("Reset Database"),
			MenuItem("Reset Config"),
			MenuItem("About")]),
		menuRect, screenRect)
		
		self.__init = True
		self.__updateDatabaseMenu = Menu([])
		for c in self.app.consoles:
			self.__updateDatabaseMenu.addItem(ConsoleMenuItem(c, False, True))
		self.__toggleMargin = 20
		self.__updateDbThread = None
		self.__scanProgressBar = None
		self.__defaultHeaderText = "Settings"
		self.__headerLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.screenRect[1], self.__defaultHeaderText, self.app.titleFont, self.app.textColour))
		logging.debug("SettingsScreen.init: initialised")
		self.__initText = "Here you can scan for new games, set-up your joysticks as well as being able to reset PES to its default settings\n\nPlease select an item from the menu on the left."
		self.__scanText = "Please use the menu below to select which consoles you wish to include in your search. By default all consoles are selected.\n\nWhen you are ready, please select the \"Begin Scan\" button."
		self.__descriptionLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.__headerLabel.y + (self.__headerLabel.height * 2), self.__initText, self.app.bodyFont, self.app.textColour, fixedWidth=self.screenRect[2] - self.screenMargin))
		self.__consoleList = None
		self.__scanButton = None
		self.__selectAllButton = None
		self.__deselectAllButton = None

	def drawScreen(self):
		super(SettingsScreen, self).drawScreen()
		
		currentX = self.screenRect[0] + self.screenMargin
		currentY = self.screenRect[1]
		
		self.__headerLabel.draw()
		self.__descriptionLabel.draw()
		
		if self.__init:
			return
		
		selected = self.menu.getSelectedItem().getText()
		
		if selected == "Update Database":
			if self.__updateDbThread != None:
				if self.__updateDbThread.started and not self.__updateDbThread.done:
					self.__descriptionLabel.setText("Scanned %d out of %d roms... press BACK to abort\n\nElapsed: %s\n\nRemaining: %s\n\nProgress:" % (self.__updateDbThread.getProcessed(), self.__updateDbThread.romTotal, self.__updateDbThread.getElapsed(), self.__updateDbThread.getRemaining()), True)
					self.__scanProgressBar.y = self.__descriptionLabel.y + self.__descriptionLabel.height + 10
					self.__scanProgressBar.setProgress(self.__updateDbThread.getProgress())
					self.__scanProgressBar.draw()
				elif self.__updateDbThread.done:
					self.app.doKeyEvents = True
					interruptedStr = ""
					if self.__updateDbThread.interrupted:
						interruptedStr = "(scan interrupted)"
					self.__descriptionLabel.setText("Scan completed in %s %s\n\nAdded: %d\n\nUpdated: %d\n\nDeleted: %d\n\nPress BACK to return to the previous screen." % (self.__updateDbThread.getElapsed(), interruptedStr, self.__updateDbThread.added, self.__updateDbThread.updated, self.__updateDbThread.deleted), True)
			else:
				self.__consoleList.draw()
				self.__scanButton.draw()
				self.__selectAllButton.draw()
				self.__deselectAllButton.draw()
		
	def processEvent(self, event):
		selected = self.menu.getSelectedItem().getText()
		oldMenuActive = self.menuActive # store state before parent method changes it!
		
		# don't pass up the event if a db scan is in progress
		if event.type == sdl2.SDL_KEYDOWN and selected == "Update Database" and self.__updateDbThread != None:
			if event.key.keysym.sym == sdl2.SDLK_BACKSPACE:
				if self.__updateDbThread.started and not self.__updateDbThread.done:
					self.setMenuActive(False)
					self.__updateDbThread.stop()
				elif selected == "Update Database" and self.__updateDbThread.done:
					self.setMenuActive(False)
					self.__updateDbThread = None
					self.__descriptionLabel.setText(self.__scanText, True)
					self.__scanButton.setFocus(False)
					self.__consoleList.setFocus(True)
					self.__updateDatabaseMenu.toggleAll(True)
					self.__updateDatabaseMenu.setSelected(0)
					#self.__consoleList.scrollTop()
			return
		
		super(SettingsScreen, self).processEvent(event)
		
		if oldMenuActive:
			if event.type == sdl2.SDL_KEYDOWN and (event.key.keysym.sym == sdl2.SDLK_RETURN or event.key.keysym.sym == sdl2.SDLK_KP_ENTER):
				logging.debug("SettingsScreen.processEvent: return key trapped for %s" % selected)
				if selected == "Update Database":
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
				elif selected == "About":
					self.__headerLabel.setText(selected)
					self.__descriptionLabel.setText("Pi Entertainment System version %s\n\nReleased: %s\n\nLicense: Licensed under version 3 of the GNU Public License (GPL)\n\nAuthor: %s\n\nContributors: Eric Smith\n\nCover art: theGamesDB.net\n\nDocumentation: http://pes.mundayweb.com\n\nFacebook: https://www.facebook.com/pientertainmentsystem\n\nHelp: pes@mundayweb.com\n\nIP Address: %s" % (VERSION_NUMBER, VERSION_DATE, VERSION_AUTHOR, self.app.ip), True)
				elif selected == "Joystick Set-Up":
					self.__headerLabel.setText(selected)
					self.__descriptionLabel.setText("To be implemented.", True)
					
				self.__init = False
		else:
				if selected == "Update Database":
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
							#if self.__updateDatabaseMenu.getToggledCount() == 0:
							#	self.__scanButton.setVisible(False)
							#else:
							#	self.__scanButton.setVisible(True)
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

		if self.menuActive: # this will be true if parent method trapped a backspace event
			if event.type == sdl2.SDL_KEYDOWN:
				if event.key.keysym.sym == sdl2.SDLK_BACKSPACE:
					logging.debug("SettingsScreen.processEvent: trapping backspace event")
					self.__init = True
					self.__headerLabel.setText(self.__defaultHeaderText)
					self.__descriptionLabel.setText(self.__initText, True)

	def startScan(self):
		logging.debug("SettingsScreen.startScan: beginning scan...")
		self.app.doKeyEvents = False
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
