pes
===

PES is a graphical front end for a variety of games console emulators that has been written in Python which is intended for use on the Raspberry Pi.

At the heart of PES is the pes.py GUI. This can be used on any OS that supports Python and PyGame.

![PES GUI 1](http://pes.mundayweb.com/html/_images/pes-main.png)
![PES GUI 2](http://pes.mundayweb.com/html/_images/pes-nes.png)

For use on the Raspberry Pi, PES is distributed via an ArchLinux image (see http://pes.mundayweb.com/html/Installation.html#downloading for the latest image) which contains pre-compiled emulators for the Raspberry Pi. The configuration and compiliation scripts used to create the image are also included in this repository.

The PES Raspberry Pi image has the following features:

* Graphical interface
* Works with HDMI CEC enabled displays thus allowing you to use your TV remote control to navigate the interface
* Automatic downloading of game cover art (requires network connection)
* Works with USB game pads
* PS3 control pad support via Bluetooth (requires compatible Bluetooth dongle)
* Automatic pairing of PS3 control pads
* File sharing support to allow you to install new games (requires network connection)
* Uses ArchLinux for a minimal system installation
* Provides console emulation via RetroArch for:

  * Nintendo Entertainment System (NES)
  * Nintendo Game Boy
  * Nintendo Game Boy Color
  * Nintendo Super Entertainment System (SNES)
  * Sega Game Gear
  * Sega Master System
  * Sega Mega Drive (aka Genesis)
  * Sega CD
  * Sony PlayStation
  
The documentation and Raspberry Pi image for PES can be found at: http://pes.mundayweb.com

Acknowledgements
----------------

I would like to thank the following people/groups as without them PES would not be possible:

* Frank Raiser for his `image scaling code <http://www.pygame.org/pcr/transform_scale>`_ that I have modified for use by PES to scale thumbnail images
* The maintainers of `RetroArch <http://www.libretro.com>`_ and all of the emulators that PES uses:

  * `fceu-next <https://github.com/libretro/fceu-next>`_
  * `gambatte-libretro <https:///github.com/libretro/gambatte-libretro>`_
  * `Genesis-Plus-GX <https://github.com/ekeeke/Genesis-Plus-GX.git>`_
  * `pcsx_rearmed <https://github.com/notaz/pcsx_rearmed>`_
  * `PicoDrive <https://github.com/libretro/picodrive.git>`_
  * `Pocket SNES <https://github.com/libretro/pocketsnes-libretro>`_

* falkTX for creating the `QtSixA <http://qtsixa.sourceforge.net/>`_ daemon and utilities which is used by PES for using Sony PlayStation 3 control pads via Bluetooth.
* All the maintainers of `Arch Linux <http://archlinuxarm.org/platforms/armv6/raspberry-pi>`_
* `theGamesDB.net <http://thegamesdb.net/>`_ for their comprehensive game meta data API
* All the maintainers of the `Python <https://www.python.org>`_ programming language in which PES is written
* The `Raspberry Pi Foundation <http://www.raspberrypi.org>`_
* Eric Smith for his many hours of testing, finding bugs, suggesting new features and for supplying graphics for PES

