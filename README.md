#Purpose
This is to provide version control for EV3 files such that FLL teams can work on multiple computers.

This starts from the great work done by Thad Hughes at https://github.com/Thaddeus-Maximus/ev3hub

#Disclaimer 
This is from reverse engineering the EV3 format.  (which could change at any time)
There is absolutely **NO** promise made that your data will be ok.   It has not been thoroughly tested.
This is in progress and being developed.   If you want a more stable one, go to the original work mentioned above. 
This is an *EARLY* early, **EARLY** alpha release.   It will break.
If you are uncomfortable setting up python libraries to run and running your own webserver, back away slowly now....

#Known Issues 
A few known problems:
1. Very little verification and worthless errors
2. If you forget your password, then you are up the creek without a paddle.   I haven't put in the "forgot password" yet. 
3. Right now, items are put into cookies, but not in any kind of secure way
4. the UI is ugly and is as bare bones as I could justify for testing
5. I have only tested this on my mac, and only with a few dummy files. 
 
#To Run
python ev3hub.py
It will put a webserver on port 8000 on the machine you run on
 
#Setup
This uses python 2.7.  It uses a few packages: cherrypy, mako, passlib, zipfile, json
 
Issues?  Please open them on the github project at https://github.com/alan412/ev3hub 