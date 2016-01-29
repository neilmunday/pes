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
from collections import deque
from PIL import Image
import logging
import sdl2
import sdl2.sdlimage
import sdl2.joystick
import sdl2.video
import sdl2.render
import sdl2.sdlgfx
import sdl2.sdlttf
import sdl2.timer

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
	
	def __repr__(self):
		return "<ConsoleMenuItem: text: %s >" % self.__console.getName()
	
class GameMenuItem(MenuItem):
	
	def __init__(self, game, selected = False, toggable = False, callback = None, *callbackArgs):
		super(GameMenuItem, self).__init__(game.getName(), selected, toggable, callback, *callbackArgs)
		self.__game = game
		
	def getGame(self):
		return self.__game
	
	def __repr__(self):
		return "<GameMenuItem: text: %s >" % self.__game.getName()

class UIObject(object):
	
	def __init__(self, renderer, x, y, width, height):
		self.renderer = renderer
		self.x = x
		self.y = y
		self.width = width
		self.height = height
		self.visible = True
		self.__focus = False
		self.__borderColour = None
		self.__drawBorder = False
	
	def destroy(self):
		pass
	
	def draw(self):
		if self.visible and self.__drawBorder:
			sdl2.sdlgfx.rectangleRGBA(self.renderer, self.x, self.y, self.x + self.width, self.y + self.height, self.__borderColour.r, self.__borderColour.g, self.__borderColour.b, 255)
	
	def hasFocus(self):
		return self.__focus
	
	def setAlpha(self, alpha):
		if alpha < 0 or alpha > 255:
			raise ValueError("Invalid alpha value!")
		self.alpha = alpha
	
	def setBorderColour(self, colour):
		# crap hack as the PySDL2 authors have overridden the __ne__ operator for colours and can't handle None
		self.__borderColour = colour
		try:
			if self.__borderColour != None:
				self.__drawBorder = True
			self.__drawBorder = False
		except AttributeError:
			self.__drawBorder = True
	
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
	
	def __init__(self, renderer, x, y, text, font, colour, bgColour=None, fixedWidth=0, fixedHeight=0, autoScroll=False, bgAlpha=255):
		self.__text = text
		self.__colour = colour
		self.__font = font
		if fixedWidth == 0: # no wrap
			self.__surface = sdl2.sdlttf.TTF_RenderText_Blended(self.__font, self.__text, self.__colour)
			width = self.__surface.contents.w
		else:
			self.__surface = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(self.__font, self.__text, self.__colour, fixedWidth)
			width = fixedWidth
		self.__textWidth = self.__surface.contents.w
		self.__textHeight = self.__surface.contents.h
		if fixedHeight > 0:
			height = fixedHeight
		else:
			height = self.__textHeight
		super(Label, self).__init__(renderer, x, y, width, height)
		self.__texture = None
		self.__drawBackground = False
		self.__autoScroll = autoScroll
		self.__scrollY = 0
		self.__scrollTick = 0
		self.__firstDraw = True
		self.__bgAlpha = bgAlpha
		self.setBackgroundColour(bgColour)
		
	def destroy(self):
		logging.debug("Label.destroy: destroying label \"%s\"" % self.__text)
		self.setVisible(False)
		if self.__surface != None:
			sdl2.SDL_FreeSurface(self.__surface)
			self.__surface = None
		if self.__texture:
			sdl2.SDL_DestroyTexture(self.__texture)
			self.__texture = None
			
	def draw(self):
		if self.visible:
			super(Label, self).draw()
			if self.__drawBackground:
				sdl2.sdlgfx.boxRGBA(self.renderer, self.x, self.y, self.x + self.width, self.y + self.height, self.__bgColour.r, self.__bgColour.g, self.__bgColour.b, self.__bgAlpha)
			if self.__texture == None and self.__surface != None:
					self.__texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, self.__surface)
					sdl2.SDL_FreeSurface(self.__surface)
					self.__surface = None
			if self.__textWidth < self.width:
				w = self.__textWidth
			else:
				w = self.width
			if self.__textHeight < self.height:
				h = self.__textHeight
			else:
				h = self.height
			if self.__autoScroll and self.__textHeight > self.height:
				tick = sdl2.timer.SDL_GetTicks()
				if self.__firstDraw:
					self.__scrollTick = tick
					self.__firstDraw = False
				if self.__scrollY == 0:
					if tick - self.__scrollTick > 2000:
						self.__scrollTick = tick
						self.__scrollY += 1
				elif tick - self.__scrollTick > 75:
					self.__scrollTick = tick
					self.__scrollY += 1
				if self.__scrollY > self.__textHeight - self.height:
					self.__scrollY = 0
			sdl2.SDL_RenderCopy(self.renderer, self.__texture, sdl2.SDL_Rect(0, self.__scrollY, w, h), sdl2.SDL_Rect(self.x, self.y, w, h))
		
	def getText(self):
		return self.__text
	
	def setAlpha(self, alpha):
		super(Label, self).setAlpha(alpha)
		if self.__texture:
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
			surface = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(self.__font, self.__text, self.__colour, self.width)
			self.__texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
			sdl2.SDL_FreeSurface(surface)
			
	def setText(self, text, pack=False):
		if text == self.__text:
			return
		if text == None or text == "":
			self.__text = " "
		else:
			self.__text = text
		self.__scrollY = 0
		self.__firstDraw = True
		sdl2.SDL_DestroyTexture(self.__texture)
		surface = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(self.__font, self.__text, self.__colour, self.width)
		self.__textWidth = surface.contents.w
		self.__textHeight = surface.contents.h
		self.__texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
		sdl2.SDL_FreeSurface(surface)
		if pack:
			self.height = self.__textHeight

class List(UIObject):
	
	# listen events
	LISTEN_ITEM_ADDED = 1
	LISTEN_ITEM_REMOVED = 2
	LISTEN_ITEM_SELECTED = 3
	LISTEN_ITEM_INSERTED = 4
	
	SCROLLBAR_AUTO = 1
	SCROLLBAR_DISABLED = 2
	SCROLLBAR_ENABLED = 3
	
	def __init__(self, renderer, x, y, width, height, menu, font, colour, selectedColour, selectedBgColour, selectedBgColourNoFocus, showScrollbarPref=1, drawBackground=False):
		super(List, self).__init__(renderer,x, y, width, height)
		self.__drawBackground = drawBackground
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
		self.__showScrollbarPref = showScrollbarPref
		if self.__showScrollbarPref == List.SCROLLBAR_ENABLED or (self.__showScrollbarPref == List.SCROLLBAR_AUTO and self.__menuCount > self.__visibleMenuItems):
			self.__setupScrollbar()
		else:
			self.__labelX = self.x
			self.__labelWidth = self.width
			self.__showScrollbar = False
		self.__labels = []
		self.__labels.append(Label(self.renderer, self.__labelX, y, self.__menu.getItem(0).getText(), self.__font, self.__selectedColour, self.__selectedBgColour, fixedWidth=self.__labelWidth, fixedHeight=self.__fontHeight))
		labelY = y + self.__fontHeight
		for i in xrange(1, self.__visibleMenuItems):
			self.__labels.append(Label(self.renderer, self.__labelX, labelY, self.__menu.getItem(i).getText(), self.__font, self.__colour, fixedWidth=self.__labelWidth, fixedHeight=self.__fontHeight))
			labelY += self.__fontHeight
		self.__firstMenuItem = 0
		self.__labelIndex = 0
		self.__toggleRad = 3
		self.__toggleCenterY = self.__fontHeight / 2
		self.__menu.addListener(self)
		self.__listeners = []
		self.__lastScrollEvent = 0
		self.__checkScrollEvent = False
		logging.debug("List.init: created List with %d labels for %d menu items, width: %d, height: %d" % (len(self.__labels), self.__menuCount, self.width, self.height))
	
	def addListener(self, l):
		if l not in self.__listeners:
			self.__listeners.append(l)
	
	def destroy(self):
		self.__menu.removeListener(self)
		logging.debug("List.destroy: destroying %d labels..." % len(self.__labels))
		for l in self.__labels:
			l.destroy()
		
	def draw(self):
		if self.visible:
			super(List, self).draw()
			i = self.__firstMenuItem
			for l in self.__labels:
				l.draw()
				if self.__menu.getItem(i).isToggled():
					sdl2.sdlgfx.filledCircleRGBA(self.renderer, l.x - 10, self.__toggleCenterY + l.y, self.__toggleRad, self.__colour.r, self.__colour.g, self.__colour.b, 255)
				i += 1
			if self.__drawBackground:
				sdl2.sdlgfx.boxRGBA(self.renderer, self.x, self.y, self.x + self.width, self.y + self.height, self.__selectedBgColourNoFocus.r, self.__selectedBgColourNoFocus.g, self.__selectedBgColourNoFocus.b, 50)
			if self.__showScrollbar:
				sdl2.sdlgfx.boxRGBA(self.renderer, self.__sliderX, self.__sliderY, self.__sliderX + self.__sliderWidth, self.__sliderY + self.__sliderHeight, self.__selectedColour.r, self.__selectedColour.g, self.__selectedColour.b, 50)
				
			if self.__checkScrollEvent:
				if sdl2.timer.SDL_GetTicks() - self.__lastScrollEvent > 100:
					self.__fireListenEvent(List.LISTEN_ITEM_SELECTED, self.__menu.getSelectedItem())
					self.__checkScrollEvent = False
	
	def __fireListenEvent(self, eventType, item):
		for l in self.__listeners:
			l.processListEvent(eventType, item)
	
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
					self.__lastScrollEvent = sdl2.timer.SDL_GetTicks()
					self.__checkScrollEvent = True
					if self.__showScrollbar:
						self.__updateScrollbar()
				elif event.key.keysym.sym == sdl2.SDLK_UP:
					#logging.debug("List.processEvent: key event: UP")
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
					self.__lastScrollEvent = sdl2.timer.SDL_GetTicks()
					self.__checkScrollEvent = True
					if self.__showScrollbar:
						self.__updateScrollbar()
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
			else:
				if self.__showScrollbarPref == List.SCROLLBAR_AUTO or self.__showScrollbarPref == List.SCROLLBAR_ENABLED:
					self.__setupScrollbar()
			labelLen = len(self.__labels)
			if labelLen < self.__visibleMenuItems:
				self.__labels.append(Label(self.renderer, self.__labelX, (labelLen * self.__fontHeight) + self.y, item.getText(), self.__font, self.__colour, fixedWidth=self.__labelWidth, fixedHeight=self.__fontHeight))
				if self.__showScrollbar:
					self.__sliderHeight = int((float(self.__visibleMenuItems) / float(self.__menuCount)) * self.__scrollbarHeight)
			self.__fireListenEvent(List.LISTEN_ITEM_ADDED, item)
		elif eventType == Menu.LISTEN_ITEM_INSERTED:
			logging.debug("List.processMenuEvent: item inserted")
			self.__menuCount = self.__menu.getCount()
			self.__visibleMenuItems = int(self.height / self.__fontHeight)
			if self.__visibleMenuItems > self.__menuCount:
				self.__visibleMenuItems = self.__menuCount
			else:
				if self.__showScrollbarPref == List.SCROLLBAR_AUTO or self.__showScrollbarPref == List.SCROLLBAR_ENABLED:
					self.__setupScrollbar()
			labelLen = len(self.__labels)
			if labelLen < self.__visibleMenuItems:
				self.__labels.append(Label(self.renderer, self.__labelX, (labelLen * self.__fontHeight) + self.y, " ", self.__font, self.__colour, fixedWidth=self.__labelWidth, fixedHeight=self.__fontHeight))
				if self.__showScrollbar:
					self.__sliderHeight = int((float(self.__visibleMenuItems) / float(self.__menuCount)) * self.__scrollbarHeight)
			# update label text
			for i in xrange(self.__visibleMenuItems):
				self.__labels[i].setText(self.__menu.getItem(self.__firstMenuItem + i).getText())
			self.__fireListenEvent(List.LISTEN_ITEM_INSERTED, item)
		elif eventType == Menu.LISTEN_ITEM_SELECTED:
			logging.debug("List.processMenuEvent: item selected")
			self.__selectLabel(self.__menu.getSelectedIndex())
			self.__fireListenEvent(List.LISTEN_ITEM_SELECTED, item)
			
	def removeListener(self, l):
		if l in self.__listeners:
			self.__listeners.remove(l)
						
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
		self.__updateScrollbar()
		
	def __setupScrollbar(self):
		self.__scrollbarWidth = 20
		self.__scrollbarHeight = self.height
		self.__scrollbarX = self.x
		self.__scrollbarY = self.y
		self.__sliderGap = 2
		self.__labelX = self.__scrollbarX + self.__scrollbarWidth + 10
		self.__labelWidth = self.width - self.__scrollbarWidth - 10
		# work out slider height
		self.__sliderHeight = int((float(self.__visibleMenuItems) / float(self.__menuCount)) * self.__scrollbarHeight) - (self.__sliderGap * 2)
		self.__sliderX = self.__scrollbarX + 2
		self.__sliderWidth = self.__scrollbarWidth - (self.__sliderGap * 2)
		self.__showScrollbar = True
		self.__updateScrollbar()
		
	def __updateScrollbar(self):
		if self.__showScrollbar:
				self.__sliderY = int(((float(self.__menu.getSelectedIndex()) / float(self.__menuCount)) * float(self.__scrollbarHeight - self.__sliderHeight)) + self.__scrollbarY) + self.__sliderGap

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
	
	CACHE_LEN = 100
	__cache = {} # shared texture cache
	__queue = deque()
	
	def __init__(self, renderer, x, y, width, height, game, font, txtColour, drawLabel=True):
		self.__font = font
		self.__fontHeight = sdl2.sdlttf.TTF_FontHeight(self.__font)
		self.__thumbWidth = width
		self.__thumbHeight = height
		self.__labelHeight = self.__fontHeight * 2
		if drawLabel:
			height += 1 + self.__labelHeight # allow space for label
		super(Thumbnail, self).__init__(renderer, x, y, width, height)
		self.__txtColour = txtColour
		self.__game = game
		self.__gameId = game.getId()
		self.__coverart = game.getCoverArt()
		if self.__coverart == None:
			self.__coverart = game.getConsole().getNoCoverArtImg()
		self.__coverartTexture = None
		if drawLabel:
			self.__label = Label(self.renderer, self.x, self.y + self.__thumbHeight + 1, self.__game.getName(), self.__font, self.__txtColour, fixedWidth=self.width, fixedHeight=self.__labelHeight)
		else:
			self.__label = None
		logging.debug("Thumbnail.init: initialised for %s" % game.getName())
		
	@staticmethod
	def __addToCache(gameId, texture):
		Thumbnail.__cache[gameId] = texture
		Thumbnail.__queue.append(gameId)
		if len(Thumbnail.__queue) > Thumbnail.CACHE_LEN:
			logging.debug("Thumbnail.__addToCache: cache length %d exceeded, removing item from cache to make room..." % Thumbnail.CACHE_LEN)
			gameId = Thumbnail.__queue.popleft()
			sdl2.SDL_DestroyTexture(Thumbnail.__cache[gameId])
			del Thumbnail.__cache[gameId]
		
	def draw(self):
		if self.visible:
			super(Thumbnail, self).draw()
			if self.__gameId not in Thumbnail.__cache:
				logging.debug("Thumbnail.draw: loading texture for %s" % self.__game.getName())
				self.__coverartTexture = sdl2.sdlimage.IMG_LoadTexture(self.renderer, self.__coverart)
				self.__addToCache(self.__gameId, self.__coverartTexture)
			else:
				self.__coverartTexture = Thumbnail.__cache[self.__gameId]
			sdl2.SDL_RenderCopy(self.renderer, self.__coverartTexture, None, sdl2.SDL_Rect(self.x, self.y, self.__thumbWidth, self.__thumbHeight))
			# render text underneath
			if self.__label:
				self.__label.draw()
			
	def destroy(self):
		if self.__label:
			self.__label.destroy()
		
	@staticmethod
	def destroyTextures():
		logging.debug("Thumbnail.destroyTextures: purging %d textures..." % len(Thumbnail.__cache))
		keys = []
		for key, value in Thumbnail.__cache.iteritems():
			sdl2.SDL_DestroyTexture(value)
			keys.append(key)
		for k in keys:
			del Thumbnail.__cache[k]
			
	def setGame(self, game):
		if self.__gameId == game.getId():
			return
		if self.__label:
			self.__label.setText(game.getName())
		self.__game = game
		self.__gameId = game.getId()
		self.__coverart = game.getCoverArt()
		if self.__coverart == None:
			self.__coverart = game.getConsole().getNoCoverArtImg()
		self.__coverartTexture = None
		
class ThumbnailPanel(UIObject):
	
	def __init__(self, renderer, x, y, width, games, font, txtColour, selectedColour, gap=10, drawLabels=True, maxThumbs=0):
		super(ThumbnailPanel, self).__init__(renderer, x, y, width, 1) # height is overridden later
		self.__gap = gap
		self.__thumbnails = []
		self.__font = font
		self.__txtColour = txtColour
		self.__selectedColour = selectedColour
		self.__drawLabels = drawLabels
		self.__maxThumbs = maxThumbs
		self.setGames(games)
			
	def draw(self):
		if self.visible:
			for t in self.__thumbnails:
				t.draw()
			
	def destroy(self):
		logging.debug("ThumbnailPanel.destory: destroying...")
		for t in self.__thumbnails:
			t.destroy()
			
	def setGames(self, games):
		self.__games = games
		if self.__maxThumbs > 0:
			maxThumbs = self.__maxThumbs
		else:
			maxThumbs = len(games)
		desiredThumbWidth = int((self.width - (maxThumbs * self.__gap)) / maxThumbs)
		img = Image.open(games[0].getConsole().getNoCoverArtImg())
		img.close()
		w, h = img.size
		ratio = float(h) / float(w)
		self.__thumbWidth = desiredThumbWidth
		self.__thumbHeight = int(ratio * self.__thumbWidth)
		for t in self.__thumbnails:
			t.destroy()
		self.__thumbnails = []
		currentX = self.x
		for g in self.__games:
			self.__thumbnails.append(Thumbnail(self.renderer, currentX, self.y, self.__thumbWidth, self.__thumbHeight, g, self.__font, self.__txtColour, self.__drawLabels))
			currentX += self.__thumbWidth + self.__gap