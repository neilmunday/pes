Setting PES up from scratch
===========================

Notes:

* this requires a Fedora Linux system (32 or 64 bit)
* you must have git installed (e.g. dnf install git)
* pes will be install under /opt/pes
* a custom build of SDL 2.0.4 will be installed under /opt/sdl2

Set-up sudo
===========

Run as root:

	groupadd sudoers
	usermod -a -G sudoers YOUR_USERNAME
	
Run visudo and add a line like so:

	%sudoers ALL=(ALL) NOPASSWD: ALL
	
Now log out of your desktop and log back in again for the changes to take effect.

Download PES repository
=======================

Check out the PES git repo:

	cd ~
	mkdir git
	cd git
	git clone https://github.com/neilmunday/pes
	
Change to the fedora-x86 directory:

	cd pes/setup/fedora-x86
	
Now run the setup.sh script:

	./setup.sh

This script will run each install script to compile the emulators and supporting software required by PES.
	
Or you can opt to run each "install-" script yourself.

Note: not all are run by setup.sh as some install emulators etc. that are not production ready.

Start PES
=========

Providing no errors were encountered above, you can start PES as a normal user like so:

	/opt/pes/bin/pes
	
This will start PES in fullscreen mode. If you would rather run PES in a window, please run:

	/opt/pes/bin/pes -w
	
Debugging
=========

To turn on debug messages please add the "-v" flag. You can also redirect all logging information to a file of your choosing by using the "-l" flag, e.g.

	/opt/pes/bin/pes -v -l ~/pes/log
