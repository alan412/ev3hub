import os
import json
import string
import time
import hashlib
from passlib.apps import custom_app_context as pwd_context
import smtplib
import email.utils
import random
import ev3project
from email.mime.text import MIMEText
from operator import itemgetter
#import urllib.request, urllib.parse, urllib.error
import urllib
import shutil
import datetime;

def getSHA(text):
    m = hashlib.sha1()
    m.update(text.encode('utf-8'))
    return m.hexdigest()

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

class UserProjects(object):
    def __init__(self, username):
        self.path = os.path.join('data', getSHA(username))
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        self.username = username;
        self.proj_filepath = os.path.join(self.path, 'projects.json')
        self.load()
    def load(self):
        try:
            with open(self.proj_filepath, 'r') as project_file:
                self.projects = json.loads(project_file.read())
                print("list: ", self.projects)
                for project in self.projects:
                    if 'expires' in self.projects[project]:
                        self.projects[project]['expires'] = datetime.datetime.fromisoformat(self.projects[project]['expires'])
        except:
            self.projects = {}
            pass
    def save(self):
        with open(self.proj_filepath, 'w') as project_file:
               json.dump(self.projects, project_file, default=json_serial)
    def add_project(self, projname):
        self.projects[projname] = {}
        self.save();
    def expire_project(self, projName):
        self.projects[projName]['expires'] = datetime.datetime.now() + datetime.timedelta(days=7)
        self.save();
    def restore_project(self, projName):
        del self.projects[projName]['expires']
        filename = os.path.join(self.path, getSHA(projName))
        os.utime(filename, None)  # Sets modification time to now
        self.save();
    def remove_expired_projects(self):
        currTime = datetime.datetime.now();
        tmpProjects = self.projects;
        for project in tmpProjects:
            if 'expires' in self.projects[project]['expires']:
                if self.projects[project]['expires'] < currTime:
                   projectDir = os.path.join(self.path(), getSHA(project))
                   shutil.rmtree(projectDir, True) # ignoring errors because we really don't have anything we can do about it
                   self.projects.pop(project, None)
                   self.save();
    def rename_project(self, oldName, newName):
        self.projects.pop(oldName, None);
        self.projects[newName] = {}
        self.save();
    def expire_old_projects(self):
        oldTime = datetime.datetime.now() - datetime.timedelta(days=365);
        for project in self.projects:
            if not project['expires']:
               updated = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(self.path, getSHA(project))));
               if updated < oldTime:
                  self.expire_project(project)

    def get_project_list(self):
        project_list = []
        for project in self.projects:
            updated = os.path.getmtime(os.path.join(self.path, getSHA(project)));
            expires = 0;
            print("Project ", project)
            if 'expires' in self.projects[project]:
                expires = self.projects[project]['expires'].timestamp()
            project_list.append({'name':project, 'Updated': updated, 'expires': expires })
        return project_list;

class Users(object):
    def __init__(self):
        self.users = {};
        if not os.path.exists('data'):
            os.makedirs('data')
        self.path = os.path.join('data','users.json')
        try:
            with open(self.path, 'r') as user_file:
                self.users = json.loads(user_file.read())
        except:
            pass
    def create_forgot_token(self, username):
        try:
            if self.users[username]['forgot-time'] < (time.time() + 300):   # to keep mspradli from spamming people
                return ''
        except:
            pass
        chars='ABCDEFGHJKMNPQRSTUVWXYZ23456789';
        forgotID = ''.join(random.SystemRandom().choice(chars) for _ in range(8))
        try:
            self.users[username]['forgot'] = pwd_context.hash(forgotID)
            self.users[username]['forgot-time'] = time.time();
            self.save()
        except:
            forgotID = ''
        return forgotID
    def verify_forgot(self, username, forgot):
        try:
            if (self.users[username]['forgot-time'] < (time.time() + (60*60*24))) and pwd_context.verify(forgot, self.users[username]['forgot']):
                self.users[username]['forgot'] = ''   # Don't save because the next step is changing password
                self.users[username]['forgot-time'] = ''
                return True;
        except:
            pass
        return False
    def save(self):
        with open(self.path, 'w') as user_file:
               json.dump(self.users, user_file)

# if username already exists, this overwrites it.   So be careful upon calling it!
    def add(self, username, email, password):
        self.users[username] = {}
        self.users[username]['password'] = pwd_context.hash(password)
        self.users[username]['email'] = email;
        self.save();
    def change_password(self, username, newpass):
        self.users[username]['password'] = pwd_context.hash(newpass)
        self.save();
    def change_email(self, username, email):
        if email and (email != self.users[username]['email']):
            self.users[username]['email'] = email
            self.save();
    def get(self, username):   # this will return the case version that is in the users list
        if not username:
            return ''  # not found
        lower_username = username.lower()
        for key in self.users:
            if key.lower() == lower_username:
                return key
        return ''   # not found
    def get_email(self, username):
        try:
            result = self.users[username]['email'];
        except:
            result = ''
        return result;
    def verify_password(self, username_in,password):
        username = self.get(username_in)
        if username:
            return pwd_context.verify(password, self.users[username]['password'])
        else:
            return False;
    def get_user_dir(self, username):
        return getSHA(username)
    def get_project_dir(self, username, project):
        return os.path.join("data", self.get_user_dir(username), getSHA(project))
    def get_project(self, username, project):
        if not username:
            return None
        if not project:
            try:
               project_list = self.get_projectlist(username);
               project_item = project_list[0]
               project_name = project_item['name']
               project = self.get_projectlist(username)[0]['name']
            except:
               return None
        proj_dir = self.get_project_dir(username, project)
        if os.path.exists(proj_dir):
            return ev3project.EV3Project(project, self.get_project_dir(username, project))
        else:
            return None
    def new_project(self, username, project, ev3data, who, host):
        up = UserProjects(username)
        ev3project.EV3Project.newProject(project, self.get_project_dir(username, project), ev3data, who, host)
        up.add_project(project)
    def restore_project(self, username, project):
        up = UserProjects(username)
        up.restore_project(project)
        return True;

    def remove_project(self, username, project):
        up = UserProjects(username)
        up.expire_project(project)
        mail = self.get_email(username);
        if mail:
           safe_username=urllib.parse.quote_plus(username)
           msg = MIMEText("Someone marked project '" + project + "' for deletion.\n" +
           "If this wasn't intentional, it can be recovered for the next 7 days from the list of projects.")

           from_email = 'ev3hub@ev3hub.com';
           msg['To'] = email.utils.formataddr((username, mail))
           msg['From'] = email.utils.formataddr(('EV3Hub Admin', from_email))
           msg['Subject'] = 'Project Deleted'

#           print "Simulating sending: {0}, {1},{2}".format(from_email, mail, msg.as_string())
#           return ''

           server = smtplib.SMTP('localhost')
           try:
              server.sendmail(from_email, [mail], msg.as_string())
           finally:
              server.quit()
        return True
    def get_projectlist(self, username):
        up = UserProjects(username);
        projects_dates = up.get_project_list()

        return sorted(projects_dates, key=itemgetter('Updated'), reverse=True)
    def rename_project(self, username, oldName, newName):
        path = self.get_project_dir(username, oldName)
        newPath = self.get_project_dir(username, newName)
        if os.path.exists(newPath):   # Already a project by this name, don't allow duplicates
           return False
        if os.path.exists(path):
           os.rename(path, newPath)
        up = UserProjects(username);
        up.rename_project(oldName, newName);
        return True
    def project_exists(self, username, project):
        path = self.get_project_dir(username, project)
        if os.path.exists(path):
            return True
        else:
            return False

    def mail_token(self, username_in):
        username = self.get(username_in)
        if not username:
            return "Login doesn't exist"
        else:
           mail = self.get_email(username);
           if not mail:
              return "No email defined for user:{0}".format(username)

           token = self.create_forgot_token(username)
           if not token:
              return "Tokens only sent every 5 minutes per user.  Please check your email."

           safe_username=urllib.parse.quote_plus(username)
           msg = MIMEText("Please go to http://beta.ev3hub.com/forgot?username=" + safe_username +
               "&token=" + token + " to reset your password.  If you did not request that you had forgotten " +
               "your password, then you can safely ignore this e-mail.  This expires in 24 hours.\n\nThank you,\nThe EV3HUB team");

           from_email = 'ev3hub@ev3hub.com';
           msg['To'] = email.utils.formataddr((username, mail))
           msg['From'] = email.utils.formataddr(('EV3Hub Admin', from_email))
           msg['Subject'] = 'Forgotten Password'

#           print "Simulating sending: {0}, {1},{2}".format(from_email, mail, msg.as_string())
#           return ''

           server = smtplib.SMTP('localhost')
           try:
              server.sendmail(from_email, [mail], msg.as_string())
           finally:
              server.quit()
              return ''


if __name__ == '__main__':
   print("Need to create unit test code")
