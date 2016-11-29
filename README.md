#Purpose
This is to provide version control for EV3 files such that FLL teams can work on multiple computers.

This starts from the great work done by Thad Hughes at https://github.com/Thaddeus-Maximus/ev3hub

#Disclaimer 
This is from reverse engineering the EV3 format.  (which could change at any time)
There is absolutely **NO** promise made that your data will be ok.   It has not been thoroughly tested.
This is in progress and being developed.   If you want a more stable one, go to the original work mentioned above. 

#Plans
1. Store the ev3 files uploaded so that they are backed up as well as the changesets
2. Change the logins so it doesn't store passwords as plain text.  (this will include an admin page where people can create new accounts)   
3. Cleanup some of the formatting on the web pages
4. Move to using cherrypy and get rid of having own web framework

#Issues 
Issues?  Please open them on the github project at https://github.com/alan412/ev3hub 

#Old readme
Server system requirements:
An operating system. I've devved this in Windows. It should work on Linux. Haven't tested on Mac and make no guaruntees.
Python 2.7
A computer that can run things. Don't really need a lot of horsepower or even transfer speeds.
That should be all.

Disclaimer: We (FLL Team Power Surge) make absolutely no guaruntee your data will stay intact.
We haven't battle tested this yet.
In fact, this system very much can kill your project.
You should be able to roll back to a working copy, though.

To setup:
0. Put this whole folder somewhere you like. Doesn't really matter. Somewhere you have as much elevation is probably good. I'd personally put the contents in the C:\Users\<username goes here>\EV3HUB directory.
1. Open up the logins.json file in any text editor EXCEPT FOR EDITTEXT ON MACS. EditText uses the wrong quotation marks. You'll have to use a different editor.
2. Do you see how it's name-value pairs? Okay, good. A name is for an account name, the corresponding string is the password for that account. You can have many accounts if you like but it's not really useful. Look up JSON syntax if the server fails to work right or throws errors at you...
3. Make your changes and save them. For best results, only use characters A-z, spaces, underscores, and numbers.

To start: Run the server.py file. Command prompt opens. Should stay open unless it dies... in which case, see troubleshooting.
If you want to run it without the command prompt window... you can rename the file to have a .pyw extension instead of .py; keep in mind you'll have to use the resource manager/task manager to kill it in Processes then.
You might be able to make it run on startup by putting a link to it into your startup folder.
To kill it: Close the window or hit ctrl-c/command-c when the window is open.

To access from machine server is running on:
Open up browser, go to 'localhost'.

To access from another machine on the same network:
1. Open up cmd.exe (Start, type 'cmd', hit enter), type ipconfig.
2. Find out your IP adress from this. Probably looks something like 192.168.xx.yyy, where yyy is not 1.
3. On the separate machine, go to this IP address in the web browser.

Firefox and Chrome handle downloads differently. Experiment and find out which one fits your workflow better.
I'm doing this browser-based because it's hard to mess up, super cross-platform, and it just works.

Issues? Email me at hughes.thad@gmail.com .