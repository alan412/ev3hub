import cherrypy
import os
import ev3project
import json
import string
from mako.template import Template
from mako.lookup import TemplateLookup
from passlib.apps import custom_app_context as pwd_context
import argparse

# this is for Mike Spradling who found the bug which let him
# violate the system.
def sanitize(filename):
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    clean_filename = ''.join(c for c in filename if c in valid_chars)
    if clean_filename.startswith(('.',' ')):
       clean_filename = '_' + clean_filename
    return clean_filename

def getHostname():
    try:
        return cherrypy.request.headers['X-Real-IP']
    except:
        return cherrypy.request.headers['Remote-Addr']

class Cookie(object):
    def __init__(self, name):
        self.name = name;
    def get(self, default=''):
        result = default
        try:
           result = cherrypy.session.get(self.name);
	   if not result:
              self.set(default)
        except:
           self.set(default);
        return result;
    def set(self, value):
        cherrypy.session[self.name] = value
    def delete(self):
        cherrypy.session.pop(self.name, None)
        self.set('', 0)  # Way to delete a cookie is to set it with an expiration time of immediate

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

# if username already exists, this overwrites it.   So be careful upon calling it!
    def add(self, username, email, password):
        self.users[username] = {}
        self.users[username]['password'] = pwd_context.hash(password)
        self.users[username]['email'] = email;

        with open(self.path, 'w') as user_file:
               json.dump(self.users, user_file)

    def get(self, username):
        try:
            result = self.users[username];
        except:
            result = ''        
        return result;        
    def verifyPassword(self, username,password):
        if self.get(username) == '':
            return False;
        else:
            return pwd_context.verify(password, self.users[username]['password'])
    
class EV3hub(object):  
    def __init__(self):
        self.users = Users();
        self.lookup = TemplateLookup(directories=['HTMLTemplates'],default_filters=['h'])
        
    def template(self, name, **kwargs):
        return self.lookup.get_template(name).render(**kwargs);
          
    def show_loginpage(self, error=''):
        cherrypy.session.regenerate();      
        return self.template("login.html", error = error)
    
    def show_diffpage(self, project, commit1, commit2, files, error=''):
        return self.template("diff.html", project=project, commit1 = commit1, commit2 = commit2, files = files, error = error)
    
    def show_mainpage(self, username, error=''):
        project = Cookie('project').get("")
        if not project:
            return self.projects()
        ev3P = ev3project.EV3Project(project, username)
        commits = ev3P.getListOfCommits()
                   
        return self.template("mainpage.html", username = username, project = project, commits = commits, failedMerges = ev3P.failedMerges, head= ev3P.head, error=error)
        
    def show_createaccountpage(self, error=''):
        return self.template("createAccount.html", error = error)
    
    def show_uploadpage(self, project, username, programmer, host):
        return self.template("upload.html", project = project, username = username, programmer = programmer, host = host)
        
    def show_changeprojectpage(self, error=''):
        host = Cookie('host').get(getHostname());
        username = Cookie('username').get()
        programmer = Cookie('who').get()
        if not username:
            return self.show_loginpage('')
            
        return self.template("projects.html",projects=self.get_projectlist(username),host=host,username=username,programmer=programmer,error=error)
        
    def get_projectlist(self, username):
        path = os.path.join('data', username);
        if os.path.exists(path):
           return next(os.walk(path))[1]
        return [];
        
    @cherrypy.expose
    def index(self):
        username = Cookie('username').get()
        if not username:
            return self.show_loginpage('')
        return self.show_mainpage(username)
    
    @cherrypy.expose
    def projects(self):
        return self.show_changeprojectpage()
    
    @cherrypy.expose
    def changeProject(self, project):
        username = Cookie('username').get()
        if not username:
            return self.show_loginpage('')
        Cookie('project').set(project)
        return self.show_mainpage(username)
                
    @cherrypy.expose
    def newProject(self, project, who, host, ev3file):
        project = sanitize(project)
        username = Cookie('username').get()
        if not username:
           return self.show_loginpage('')       
        if project in self.get_projectlist(username):
           return self.show_changeprojectpage('Duplicate Project')
        if not project:   # if blank
           return self.show_changeprojectpage('Blank name for project')
        try:      
           ev3data = ev3file.file.read();
           ev3P = ev3project.EV3Project.newProject(username, project, ev3data, who, host)
           Cookie('project').set(project)
        except:
           return self.show_changeprojectpage('Error in Project')
        
        return self.show_mainpage(username)    
    @cherrypy.expose
    def login(self,username=None,password=None):
        username = username.lower()
        if self.users.verifyPassword(username, password):
            Cookie('username').set(username)
            return self.show_mainpage(username);
        else:
            return self.show_loginpage("Username and password don't match")
    
    @cherrypy.expose
    def createAccount(self):
        return self.show_createaccountpage('')
        
    @cherrypy.expose
    def createUser(self, username, email, password, password2):
        error = ''
        username = sanitize(username.lower())
        if password != password2:
            error = "Password's don't match!"
        elif self.users.get(username):
            error = "Username in use!"
        else:
            self.users.add(username, email, password);
        if error:
            return self.show_createaccountpage(error);
        
        return self.show_loginpage('')
    
    @cherrypy.expose
    def logout(self):
        cherrypy.lib.sessions.expire()
         
        return self.show_loginpage('')
    
    @cherrypy.expose
    def upload(self):
        host = Cookie('host').get(getHostname());
        project = Cookie('project').get('')
        username = Cookie('username').get('')
        programmer = Cookie('who').get('')

        if project and username:
           return self.show_uploadpage(project, username, programmer, host);
        else: 
           return self.projects()    
    @cherrypy.expose
    def download(self, cid):
        project = Cookie('project').get('')
        ev3P = ev3project.EV3Project(project, Cookie('username').get(''))

        if cid == 'head':
          filename = project + ".ev3"
        else:
          filename = "{0}-{1}.ev3".format(project, cid)
          
        cherrypy.response.headers['Content-Type'] = 'application/x-download'    
        cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="{0}"'.format(filename)
        print cherrypy.response.headers
        return ev3P.download(cid)
            
    @cherrypy.expose
    def uploadDone(self, project, comment, who, host, ev3file):  
        error = '' 
        try:
           Cookie('host').set(host)
           Cookie('who').set(who)
           ev3data = ev3file.file.read();
           ev3P = ev3project.EV3Project(Cookie('project').get(project), Cookie('username').get(''))
           cid = ev3P.uploadCommit(ev3data, comment, who, host)
           merge_errors = ev3P.merge(cid)
           if merge_errors:
              error = merge_errors            
        except:
            error = 'Error in uploading.  Upload not saved'
         
        username = Cookie('username').get('')
        return self.show_mainpage(username, error)
        
    @cherrypy.expose
    def diff(self, cid1, cid2):
        error = ''
        files = []
        filelist = [];
        
        project = Cookie('project').get('')
        
        ev3P = ev3project.EV3Project(project, Cookie('username').get(''))
        commit1 = ev3P.getCommit(cid1)
        commit2 = ev3P.getCommit(cid2)

        for filename in commit1.files():
            if filename not in filelist:
                filelist.append(filename)   
        
        for filename in commit2.files():
            if filename not in filelist:
                filelist.append(filename)                     
        
        for filename in sorted(filelist, key=unicode.lower):
            sha1 = commit1.getSHA(filename)
            sha2 = commit2.getSHA(filename)
            if (sha1 == sha2) and (not sha1):   # is a variable
                if filename in commit1.files():
                    sha1 = 'var'
                if filename in commit2.files():
                    sha2 = 'var'
            files.append({'name' : filename, '1' : sha1, '2' : sha2})
            
        return self.show_diffpage(project,commit1, commit2, files)       
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Version Control for ev3")
    parser.add_argument('conf')
    args = parser.parse_args()   
        
    cherrypy.quickstart(EV3hub(),'', args.conf)
