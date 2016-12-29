import os
import json
import string
import time
from passlib.apps import custom_app_context as pwd_context
import smtplib
import email.utils
import random
from email.mime.text import MIMEText
from operator import itemgetter

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
    def get(self, username):
        try:
            result = self.users[username];
        except:
            result = ''        
        return result; 
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
    def get_project_dir(self, username, project):
        # This will change to not just using username plus project
        return os.path.join("data", username, project)

    def get_projectlist(self, username):
        projects = [];
        path = os.path.join('data', username);
        if os.path.exists(path):
           projects = next(os.walk(path))[1]

        projects_dates = [];
        if projects:
            for project in projects:
                updated = os.path.getmtime(os.path.join('data', username, project));
                projects_dates.append({'name':project, 'Updated': updated })

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