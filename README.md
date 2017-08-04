# Purpose
This is to provide version control for EV3 files such that FLL teams can work on multiple computers.

This starts from the great work done by Thad Hughes at https://github.com/Thaddeus-Maximus/ev3hub

# Disclaimer 
This is from reverse engineering the EV3 format.  (which could change at any time)
There is absolutely **NO** promise made that your data will be ok.   It has not been thoroughly tested.

# Known Issues 
The only known issues at this time.

1. Very little verification and worthless errors
2. Almost no help file

# To Run
This is available at http://beta.ev3hub.com

If you want to run your own server, use virtualenv and the requirements.txt file to get the needed Python bits.

* For Debug: python ev3hub.py development.conf   
* For 'Production': python ev3hub.py production.conf

It will put a webserver on port 8080 on the machine you run on
 
# Issues
Issues?  Please open them on the github project at https://github.com/alan412/ev3hub 
