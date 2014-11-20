pes
===

PES is a graphical front end for a variety of games console emulators that has been written in Python which is intended for use on the Raspberry Pi.

At the heart of PES is the pes.py GUI. This can be used on any OS that supports Python and PyGame.

![PES GUI](http://pes.mundayweb.com/html/_images/pes-main.png)

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
  * Nintendo Super Entertainment System (SNES)
  * Sega Game Gear
  * Sega Master System
  * Sega Mega Drive (aka Genesis)
  * Sega CD
  * Sony PlayStation
  
The documentation and Raspberry Pi image for PES can be found at: http://pes.mundayweb.com
