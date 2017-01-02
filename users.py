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

def getSHA(text):
    m = hashlib.sha1()
    m.update(text)
    return m.hexdigest()
    

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
        except:
            self.projects = {}
            pass    
    def save(self):
        with open(self.proj_filepath, 'w') as project_file:
               json.dump(self.projects, project_file)
    def add_project(self, projname):
        self.projects[projname] = {}
        self.save();
    def get_project_list(self):
        project_list = []
        print "Getting project list from {0}".format(self.projects)
        for project in self.projects:
            print "Project:{0}".format(project)
            updated = os.path.getmtime(os.path.join(self.path, getSHA(project)));
            project_list.append({'name':project, 'Updated': updated })
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
        chars='ABCDEFGHJKMNPQRSTUVWXYZ23456789';
        forgotID = ''.join(random.SystemRandom().choice(chars) for _ in range(8))
        try:
            self.users[username]['forgot'] = pwd_context.hash(forgotID)
            self.save()
        except:
            forgotID = ''
        return forgotID 
    def verify_forgot(self, username, forgot):
        try:
            if pwd_context.verify(forgot, self.users[username]['forgot']):
                self.users[username]['forgot'] = ''   # Don't save because the next step is changing password
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
    def verify_password(self, username,password):
        if self.get(username) == '':
            return False;
        else:
            return pwd_context.verify(password, self.users[username]['password'])
    def get_user_dir(self, username):
        return getSHA(username)
    def get_project_dir(self, username, project):
        # This will change to not just using username plus project
        return os.path.join("data", self.get_user_dir(username), getSHA(project))
    def get_project(self, username, project):
        return ev3project.EV3Project(project, self.get_project_dir(username, project))
    def new_project(self, username, project, ev3data, who, host):
        up = UserProjects(username)
        ev3project.EV3Project.newProject(project, self.get_project_dir(username, project), ev3data, who, host)
        up.add_project(project)
    def get_projectlist(self, username):
        up = UserProjects(username);
        projects_dates = up.get_project_list()
        
        return sorted(projects_dates, key=itemgetter('Updated'), reverse=True)    
    def project_exists(self, username, project):
        path = self.get_project_dir(username, project)
        if os.path.exists(path):
            return True
        else:
            return False
    
    def mail_token(self, username):
        if not self.get(username):
            return "Login doesn't exist"
        else:
           mail = self.get_email(username);
           if not mail:
              return "No email defined for user:{0}".format(username)
           print "1"
           token = self.create_forgot_token(username)
           print "2"
           msg = MIMEText("Please go to http://beta.ev3hub.com/forgot?username=" + username + 
               "&token=" + token + " to reset your password.  If you did not request that you had forgotten " +
               "your password, then you can safely ignore this e-mail.\n\nThank you,\nThe EV3HUB team");          

           from_email = 'ev3hub@ev3hub.com';
           msg['To'] = email.utils.formataddr((username, mail))
           msg['From'] = email.utils.formataddr(('EV3Hub Admin', from_email))
           msg['Subject'] = 'Forgotten Password'
           
           print "Simulating sending: {0}, {1},{2}".format(from_email, mail, msg.as_string())
           return ''

           server = smtplib.SMTP('localhost')       
           try:
              server.sendmail(from_email, [mail], msg.as_string())
              #print "Simulating sending: {0}, {1},{2}".format(from_email, mail, msg.as_string())
           finally:
              server.quit()
              return ''
             

if __name__ == '__main__':
   print "Need to create unit test code"