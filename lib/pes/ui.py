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

from ctypes import c_int, c_uint32, byref
import logging
import sdl2
import sdl2.sdlimage
import sdl2.joystick
import sdl2.video
import sdl2.render
import sdl2.sdlgfx
import sdl2.sdlttf

def getTextureDimensions(texture):
	flags = c_uint32()
	access = c_int()
	w = c_int()
	h = c_int()
	ret = sdl2.SDL_QueryTexture(texture, byref(flags), byref(access), byref(w), byref(h))
	return (w.value, h.value)

class Menu(object):
	
	# listen events
	LISTEN_ITEM_ADDED = 1
	LISTEN_ITEM_REMOVED = 2
	LISTEN_ITEM_SELECTED = 3
	LISTEN_ITEM_INSERTED = 4
	
	def __init__(self, items):
		super(Menu, self).__init__()
		self.__selected = 0
		self.__items = items
		self.__listeners = []
		logging.debug("Menu.init: Menu initialised")
	
	def addItem(self, item):
		self.__items.append(item)
		self.__fireListenEvent(Menu.LISTEN_ITEM_ADDED, item)
		
	def addListener(self, l):
		if l not in self.__listeners:
			self.__listeners.append(l)
			
	def __fireListenEvent(self, eventType, item):
		for l in self.__listeners:
			l.processMenuEvent(eventType, item)
		
	def getItem(self, i):
		maxIndex = len(self.__items) - 1
		if i < 0 or i > maxIndex:
			raise IndexError("Menu.getItem: List index %d out of range, max: %d" % (i, maxIndex))
		return self.__items[i]
		
	def getItems(self):
		return list(self.__items)
	
	def getSelectedIndex(self):
		return self.__selected
	
	def getSelectedItem(self):
		return self.__items[self.__selected]
	
	def getCount(self):
		return len(self.__items)
	
	def getToggled(self):
		toggled = []
		for i in self.__items:
			if i.isToggled():
				toggled.append(i)
		return toggled
	
	def getToggledCount(self):
		toggled = 0
		for i in self.__items:
			if i.isToggled():
				toggled += 1
		return toggled
	
	def insertItem(self, i, item):
		self.__items.insert(i, item)
		self.__fireListenEvent(Menu.LISTEN_ITEM_INSERTED, item)
	
	def removeItem(self, item):
		self.__items.remove(item)
		self.__fireListenEvent(Menu.LISTEN_ITEM_REMOVED, item)
		
	def removeListener(self, l):
		if l in self.__listeners:
			self.__listeners.remove(l)
		
	def setSelected(self, i, deselectAll=False, fireEvent=True):
		if i >= 0 and i < len(self.__items):
			if deselectAll:
				for m in self.__items:
					m.setSelected(False)
			else:
				self.__items[self.__selected].setSelected(False)
			self.__selected = i
			self.__items[self.__selected].setSelected(True)
			if fireEvent:
				self.__fireListenEvent(Menu.LISTEN_ITEM_SELECTED, self.__items[self.__selected])
			return
		raise ValueError("Menu.setSelected: invalid value for i: %s" % i)
	
	def toggleAll(self, toggle):
		for i in self.__items:
			if i.isToggable():
				i.toggle(toggle)
	
class MenuItem(object):
	
	def __init__(self, text, selected = False, toggable = False, callback = None, *callbackArgs):
		super(MenuItem, self).__init__()
		self.__text = text
		self.__selected = selected
		self.__callback = callback
		self.__toggled = False
		self.__toggable = toggable
		self.__callbackArgs = callbackArgs
	
	def getText(self):
		return self.__text
	
	def isSelected(self):
		return self.__selected
	
	def isToggled(self):
		return self.__toggled
		
	def isToggable(self):
		return self.__toggable
	
	def setSelected(self, selected):
		self.__selected = selected
	
	def setText(self, text):
		self.__text = text
		
	def toggle(self, t):
		self.__toggled = t
		
	def trigger(self):
		if self.__callback:
			logging.debug("MenuItem.trigger: calling function for %s menu item" % self.__text)
			if self.__callbackArgs:
				self.__callback(*self.__callbackArgs)
			else:
				self.__callback()
		else:
			logging.debug("MenuItem.trigger: no callback defined for %s menu item" % self.__text)
		
	def __repr__(self):
		return "<MenuItem: text: %s >" % self.__text
		
class ConsoleMenuItem(MenuItem):
	
	def __init__(self, console, selected = False, toggable = False, callback = None, *callbackArgs):
		super(ConsoleMenuItem, self).__init__(console.getName(), selected, toggable, callback, *callbackArgs)
		self.__console = console
		
	def getConsole(self):
		return self.__console

class UIObject(object):
	
	def __init__(self, renderer, x, y, width, height):
		self.renderer = renderer
		self.x = x
		self.y = y
		self.width = width
		self.height = height
		self.visible = True
		self.__focus = False
	
	def destroy(self):
		pass
	
	def draw(self):
		pass
	
	def hasFocus(self):
		return self.__focus
	
	def setAlpha(self, alpha):
		if alpha < 0 or alpha > 255:
			raise ValueError("Invalid alpha value!")
		self.alpha = alpha
	
	def setCoords(self, x, y):
		self.x = x
		self.y = y
		
	def setFocus(self, focus):
		self.__focus = focus
		
	def setSize(self, w, h):
		self.width = w
		self.height = h
		
	def setVisible(self, visible):
		self.visible = visible
		
class Button(UIObject):
	
	def __init__(self, renderer, x, y, width, height, text, font, colour, selectedBgColour, callback = None, *callbackArgs):
		super(Button, self).__init__(renderer, x, y, width, height)
		txtWidth = c_int()
		txtHeight = c_int()
		sdl2.sdlttf.TTF_SizeText(font, text, txtWidth, txtHeight)
		self.__labelWidth = txtWidth.value
		if self.__labelWidth > width:
			self.__labelWidth = width
		self.__labelHeight = txtHeight.value
		self.__labelX = self.x + int((self.width - self.__labelWidth) / 2)
		self.__labelY = self.y + int((self.height - self.__labelHeight) / 2)
		self.__colour = colour
		self.__selectedBgColour = selectedBgColour
		self.__texture = None
		self.__font = font
		self.__text = text
		self.__callback = callback
		self.__callbackArgs = callbackArgs
		
	def destroy(self):
		logging.debug("Button.destroy: destroying button \"%s\"" % self.__text)
		if self.__texture:
			sdl2.SDL_DestroyTexture(self.__texture)
			self.__texture = None
			
	def processEvent(self, event):
		if self.__callback and self.visible and self.hasFocus():
			if event.type == sdl2.SDL_KEYDOWN and (event.key.keysym.sym == sdl2.SDLK_RETURN or event.key.keysym.sym == sdl2.SDLK_KP_ENTER):
				logging.debug("Button.processEvent: calling callback for button \"%s\"" % self.__text)
				if self.__callbackArgs:
					self.__callback(*self.__callbackArgs)
				else:
					self.__callback()
			
	def draw(self):
		if self.visible:
			if self.__texture == None:
				surface = sdl2.sdlttf.TTF_RenderText_Blended(self.__font, self.__text, self.__colour)
				self.__texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
				sdl2.SDL_FreeSurface(surface)
			if self.hasFocus():
				sdl2.sdlgfx.boxRGBA(self.renderer, self.x, self.y, self.x + self.width, self.y + self.height, self.__selectedBgColour.r, self.__selectedBgColour.g, self.__selectedBgColour.b, 255)
			else:
				sdl2.sdlgfx.rectangleRGBA(self.renderer, self.x, self.y, self.x + self.width, self.y + self.height, self.__selectedBgColour.r, self.__selectedBgColour.g, self.__selectedBgColour.b, 255)
			sdl2.SDL_RenderCopy(self.renderer, self.__texture, sdl2.SDL_Rect(0, 0, self.__labelWidth, self.__labelHeight), sdl2.SDL_Rect(self.__labelX, self.__labelY, self.__labelWidth, self.__labelHeight))
		
class Label(UIObject):
	
	def __init__(self, renderer, x, y, text, font, colour, bgColour=None, wrap=0, fixedWidth=0, fixedHeight=0):
		self.__truncate = False
		txtWidth = c_int()
		txtHeight = c_int()
		sdl2.sdlttf.TTF_SizeText(font, text, txtWidth, txtHeight)
		if fixedWidth > 0:
			if txtWidth.value > fixedWidth:
				width = fixedWidth
				self.__truncate = True
			else:
				width = txtWidth.value
			self.__labelWidth = fixedWidth
		else:
			width = txtWidth.value
			self.__labelWidth = width
		if fixedHeight > 0:
			#if txtHeight.value > fixedHeight:
			#	height = fixedHeight
			self.__truncate = True
			#else:
			#	height = txtHeight.value
			self.__labelHeight = fixedHeight
			height = fixedHeight
		else:
			height = txtHeight.value
			self.__labelHeight = height
		super(Label, self).__init__(renderer, x, y, width, height)
		self.__font = font
		self.__colour = colour
		self.setBackgroundColour(bgColour)
		self.__wrap = wrap
		self.__texture = None
		self.__text = text
		self.__fixedWidth = fixedWidth
		self.__fixedHeight = fixedHeight
		#logging.debug("Label.init: created label \"%s\" at (%d, %d) with dimensions (%d, %d)" % (self.__text, self.x, self.y, self.width, self.height))
		
	def destroy(self):
		if self.__texture:
			sdl2.SDL_DestroyTexture(self.__texture)
			self.__texture = None
		
	def draw(self):
		if self.visible:
			if self.__texture == None:
				if self.__wrap > 0:
					surface = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(self.__font, self.__text, self.__colour, self.__wrap)
					self.__texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
				else:
					surface = sdl2.sdlttf.TTF_RenderText_Blended(self.__font, self.__text, self.__colour)
					self.__texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
				sdl2.SDL_FreeSurface(surface)
				(w, h) = getTextureDimensions(self.__texture)
				self.width = w
				self.height = h
				if h < self.__fixedHeight:
					self.__fixedHeight = h
			if self.__drawBackground:
				sdl2.sdlgfx.boxRGBA(self.renderer, self.x, self.y, self.x + self.__labelWidth, self.y + self.__labelHeight, self.__bgColour.r, self.__bgColour.g, self.__bgColour.b, 255)
			if self.__truncate:
				w = self.width
				h = self.height
				if self.__fixedHeight > 0:
					h = self.__fixedHeight
				if self.__fixedWidth > 0:
					w = self.__fixedWidth
				sdl2.SDL_RenderCopy(self.renderer, self.__texture, sdl2.SDL_Rect(0, 0, w, h), sdl2.SDL_Rect(self.x, self.y, w, h))
			else:
				sdl2.SDL_RenderCopy(self.renderer, self.__texture, None, sdl2.SDL_Rect(self.x, self.y, self.width, self.height))
			
	def setAlpha(self, alpha):
		super(Label, self).setAlpha(alpha)
		sdl2.SDL_SetTextureAlphaMod(self.__texture, alpha)
		
	def setBackgroundColour(self, colour):
		# crap hack as the PySDL2 authors have overridden the __ne__ operator for colours and can't handle None
		self.__bgColour = colour
		try:
			if self.__bgColour != None:
				self.__drawBackground = True
			self.__drawBackground = False
		except AttributeError:
			self.__drawBackground = True
			
	def setColour(self, colour):
		self.__colour = colour
		if self.__texture:
			sdl2.SDL_DestroyTexture(self.__texture)
			self.__texture = None
			
	def setText(self, text):
		if text == self.__text:
			return
		if self.__texture != None:
			sdl2.SDL_DestroyTexture(self.__texture)
		
		self.__text = text
		txtWidth = c_int()
		txtHeight = c_int()
		sdl2.sdlttf.TTF_SizeText(self.__font, self.__text, txtWidth, txtHeight)
		
		if self.__wrap > 0:
			surface = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(self.__font, self.__text, self.__colour, self.__wrap)
		else:
			surface = sdl2.sdlttf.TTF_RenderText_Blended(self.__font, self.__text, self.__colour)
		self.__texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
		sdl2.SDL_FreeSurface(surface)
		(w, h) = getTextureDimensions(self.__texture)
		self.width = w
		self.height = h

class List(UIObject):
	
	def __init__(self, renderer, x, y, width, height, menu, font, colour, selectedColour, selectedBgColour, selectedBgColourNoFocus):
		super(List, self).__init__(renderer,x, y, width, height)
		self.__menu = menu
		self.__font = font
		self.__colour = colour
		self.__selectedColour = selectedColour
		self.__selectedBgColour = selectedBgColour
		self.__selectedBgColourNoFocus = selectedBgColourNoFocus
		self.__fontHeight = sdl2.sdlttf.TTF_FontHeight(self.__font)
		self.__visibleMenuItems = int(self.height / self.__fontHeight)
		self.__menuCount = self.__menu.getCount()
		if self.__visibleMenuItems > self.__menuCount:
			self.__visibleMenuItems = self.__menuCount
		self.__labels = []
		self.__labels.append(Label(self.renderer, self.x, y, self.__menu.getItem(0).getText(), self.__font, self.__selectedColour, self.__selectedBgColour, fixedWidth=width))
		labelY = y + self.__fontHeight
		for i in xrange(1, self.__visibleMenuItems):
			self.__labels.append(Label(self.renderer, self.x, labelY, self.__menu.getItem(i).getText(), self.__font, self.__colour, fixedWidth=width))
			labelY += self.__fontHeight
		self.__firstMenuItem = 0
		self.__labelIndex = 0
		self.__toggleRad = 3
		self.__toggleCenterY = self.__fontHeight / 2
		self.__menu.addListener(self)
		logging.debug("List.init: created List with %d labels for %d menu items, width: %d, height: %d" % (len(self.__labels), self.__menuCount, self.width, self.height))
		
	def destroy(self):
		self.__menu.removeListener(self)
		logging.debug("List.destroy: destroying %d labels..." % len(self.__labels))
		for l in self.__labels:
			l.destroy()
		
	def draw(self):
		if self.visible:
			i = self.__firstMenuItem
			for l in self.__labels:
				l.draw()
				if self.__menu.getItem(i).isToggled():
					sdl2.sdlgfx.filledCircleRGBA(self.renderer, l.x - 10, self.__toggleCenterY + l.y, self.__toggleRad, self.__colour.r, self.__colour.g, self.__colour.b, 255)
				i += 1
	
	def processEvent(self, event):
		if self.visible and self.hasFocus():
			if event.type == sdl2.SDL_KEYDOWN:
				if event.key.keysym.sym == sdl2.SDLK_DOWN:
					#logging.debug("List.processEvent: key event: DOWN")
					menuIndex = self.__menu.getSelectedIndex()
					self.__labels[self.__labelIndex].setBackgroundColour(None)
					self.__labels[self.__labelIndex].setColour(self.__colour)
					#print "menuIndex: %d, labelIndex: %d, visibleMenuItems: %d, menuCount: %d" % (menuIndex, self.__labelIndex, self.__visibleMenuItems, self.__menuCount)
					if self.__labelIndex + 1 > self.__visibleMenuItems - 1:
						if menuIndex + 1 > self.__menuCount - 1:
							self.__firstMenuItem = 0
							self.__labelIndex = 0
							menuIndex = 0
						else:
							self.__firstMenuItem += 1
							menuIndex += 1
						# shift labels
						for i in xrange(self.__visibleMenuItems):
							self.__labels[i].setText(self.__menu.getItem(i + self.__firstMenuItem).getText())
					else:
						self.__labelIndex += 1
						menuIndex += 1
					self.__labels[self.__labelIndex].setBackgroundColour(self.__selectedBgColour)
					self.__labels[self.__labelIndex].setColour(self.__selectedColour)
					self.__menu.setSelected(menuIndex, fireEvent=False)
				elif event.key.keysym.sym == sdl2.SDLK_UP:
					logging.debug("List.processEvent: key event: UP")
					menuIndex = self.__menu.getSelectedIndex()
					self.__labels[self.__labelIndex].setBackgroundColour(None)
					self.__labels[self.__labelIndex].setColour(self.__colour)
					if self.__labelIndex - 1 < 0:
						if menuIndex - 1 < 0:
							self.__firstMenuItem = self.__menuCount - self.__visibleMenuItems
							self.__labelIndex = self.__visibleMenuItems - 1
							menuIndex = self.__menuCount - 1
						else:
							self.__firstMenuItem -= 1
							menuIndex -= 1
						# shift labels
						for i in xrange(self.__visibleMenuItems):
							self.__labels[i].setText(self.__menu.getItem(i + self.__firstMenuItem).getText())
					else:
						self.__labelIndex -= 1
						menuIndex -= 1
					self.__labels[self.__labelIndex].setBackgroundColour(self.__selectedBgColour)
					self.__labels[self.__labelIndex].setColour(self.__selectedColour)
					self.__menu.setSelected(menuIndex, fireEvent=False)
				elif event.key.keysym.sym == sdl2.SDLK_RETURN or event.key.keysym.sym == sdl2.SDLK_KP_ENTER:
					logging.debug("List.processEvent: key event: RETURN")
					m = self.__menu.getSelectedItem()
					if m.isToggable():
						m.toggle(not m.isToggled())
					else:
						m.trigger()
				elif event.key.keysym.sym == sdl2.SDLK_PAGEDOWN:
					self.__menu.toggleAll(False)
				elif event.key.keysym.sym == sdl2.SDLK_PAGEUP:
					self.__menu.toggleAll(True)
					
	def processMenuEvent(self, eventType, item):
		if eventType == Menu.LISTEN_ITEM_ADDED:
			logging.debug("List.processMenuEvent: item added")
			self.__menuCount = self.__menu.getCount()
			self.__visibleMenuItems = int(self.height / self.__fontHeight)
			if self.__visibleMenuItems > self.__menuCount:
				self.__visibleMenuItems = self.__menuCount
			labelLen = len(self.__labels)
			if labelLen < self.__visibleMenuItems:
				self.__labels.append(Label(self.renderer, self.x, (labelLen * self.__fontHeight) + self.y, item.getText(), self.__font, self.__colour, fixedWidth=self.width))
		elif eventType == Menu.LISTEN_ITEM_INSERTED:
			logging.debug("List.processMenuEvent: item inserted")
			self.__menuCount = self.__menu.getCount()
			self.__visibleMenuItems = int(self.height / self.__fontHeight)
			if self.__visibleMenuItems > self.__menuCount:
				self.__visibleMenuItems = self.__menuCount
			labelLen = len(self.__labels)
			if labelLen < self.__visibleMenuItems:
				self.__labels.append(Label(self.renderer, self.x, (labelLen * self.__fontHeight) + self.y, " ", self.__font, self.__colour, fixedWidth=self.width))
			# update label text
			for i in xrange(self.__visibleMenuItems):
				self.__labels[i].setText(self.__menu.getItem(self.__firstMenuItem + i).getText())
		elif eventType == Menu.LISTEN_ITEM_SELECTED:
			logging.debug("List.processMenuEvent: item selected")
			self.__selectLabel(self.__menu.getSelectedIndex())
						
	def setFocus(self, focus):
		color = None
		if focus:
			colour = self.__selectedBgColour
		else:
			colour = self.__selectedBgColourNoFocus
		self.__labels[self.__labelIndex].setBackgroundColour(colour)
		super(List, self).setFocus(focus)
		
	def __selectLabel(self, menuIndex):
		logging.debug("List.__selectLabel: selecting index %d (%s)" % (menuIndex, self.__menu.getSelectedItem().getText()))
		self.__labels[self.__labelIndex].setBackgroundColour(None)
		self.__labels[self.__labelIndex].setColour(self.__colour)
		if menuIndex < self.__visibleMenuItems:
			self.__labelIndex = menuIndex
			self.__firstMenuItem = 0
			if self.__menuCount > self.__visibleMenuItems:
				for i in xrange(self.__visibleMenuItems):
					self.__labels[i].setText(self.__menu.getItem(i + self.__firstMenuItem).getText())
		else:
			if self.__menuCount - menuIndex > self.__visibleMenuItems:
				self.__firstMenuItem = menuIndex
				self.__labelIndex = 0
				# shift labels
				for i in xrange(self.__visibleMenuItems):
					self.__labels[i].setText(self.__menu.getItem(i + self.__firstMenuItem).getText())
			else:
				self.__firstMenuItem = self.__menuCount - self.__visibleMenuItems
				self.__labelIndex = self.__visibleMenuItems - (self.__menuCount - menuIndex)
				print "FIRST MENU ITEM: %d INDEX: %d" % (self.__firstMenuItem, self.__labelIndex)
				# shift labels
				for i in xrange(self.__visibleMenuItems):
					self.__labels[i].setText(self.__menu.getItem(i + self.__firstMenuItem).getText())
		self.__labels[self.__labelIndex].setBackgroundColour(self.__selectedBgColour)
		self.__labels[self.__labelIndex].setColour(self.__selectedColour)

class ProgressBar(UIObject):
	
	def __init__(self, renderer, x, y, width, height, colour, backgroundColour):
		super(ProgressBar, self).__init__(renderer, x, y, width, height)
		self.__progress = 0.0 # percent complete
		self.__colour = colour
		self.__backgroundColour = backgroundColour
		logging.debug("ProgressBar.init: initialised")
	
	def draw(self):
		if self.visible:
			margin = 3
			w = int(self.width * (self.__progress / 100.0))
			sdl2.sdlgfx.boxRGBA(self.renderer, self.x, self.y, self.x + self.width, self.y + self.height, self.__backgroundColour.r, self.__backgroundColour.g, self.__backgroundColour.b, 255)
			sdl2.sdlgfx.boxRGBA(self.renderer, self.x + margin, self.y + margin, self.x + w - margin, self.y + self.height - margin, self.__colour.r, self.__colour.g, self.__colour.b, 255)
	
	def setProgress(self, p):
		if p > 100:
			raise ValueError("%d is greater than 100" % p)
		if p < 0:
			raise ValueError("%d is less than 0" % p)
		self.__progress = p
		
class Thumbnail(UIObject):
	
	__cache = {} # shared texture cache
	
	def __init__(self, renderer, x, y, width, height, game, font, txtColour):
		self.__font = font
		self.__fontHeight = sdl2.sdlttf.TTF_FontHeight(self.__font)
		self.__thumbWidth = width
		self.__thumbHeight = height
		self.__labelHeight = self.__fontHeight * 2
		height += 1 + self.__labelHeight # allow space for label
		super(Thumbnail, self).__init__(renderer, x, y, width, height)
		self.__txtColour = txtColour
		self.__game = game
		self.__coverart = game.getCoverArt()
		if self.__coverart == None:
			self.__coverart = game.getConsole().getNoCoverArtImg()
		self.__coverartTexture = None
		self.__label = Label(self.renderer, self.x, self.y + self.__thumbHeight + 1, self.__game.getName(), self.__font, self.__txtColour, wrap=self.width, fixedHeight=self.__labelHeight)
		logging.debug("Thumbnail.init: initialised for %s" % game.getName())
		
	def draw(self):
		if self.visible:
			if self.__coverartTexture == None:
				gameId = self.__game.getId()
				if gameId in self.__cache:
					self.__coverartTexture = self.__cache[gameId]
				else:
					logging.debug("Thumbnail.draw: loading texture for %s" % self.__game.getName())
					self.__coverartTexture = sdl2.sdlimage.IMG_LoadTexture(self.renderer, self.__coverart)
					self.__cache[gameId] = self.__coverartTexture
					#logging.debug("Thumbnail.draw: drawing at (%d, %d) dimensions (%d, %d)" % (self.x, self.y, self.__thumbWidth, self.__thumbHeight))
			sdl2.SDL_RenderCopy(self.renderer, self.__coverartTexture, None, sdl2.SDL_Rect(self.x, self.y, self.__thumbWidth, self.__thumbHeight))
			# render text underneath
			self.__label.draw()
			
	def destroy(self):
		self.__label.destroy
		
	@staticmethod
	def destroyTextures():
		logging.debug("Thumbnail.destroyTextures: purging %d textures..." % len(Thumbnail.__cache))
		keys = []
		for key, value in Thumbnail.__cache.iteritems():
			sdl2.SDL_DestroyTexture(value)
			keys.append(key)
		for k in keys:
			del Thumbnail.__cache[k]