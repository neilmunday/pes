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
	
Or you can opt to run each "install-" script yourself. Note: not all are run by setup.sh as some install emulators etc. that are not production ready.
