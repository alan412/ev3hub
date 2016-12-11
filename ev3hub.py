import cherrypy
import os
import ev3project
import json
from mako.template import Template
from mako.lookup import TemplateLookup

from passlib.apps import custom_app_context as pwd_context

class Cookie(object):
    def __init__(self, name):
        self.name = name;
    def get(self, default=''):
        result = default
        try:
           result = cherrypy.request.cookie[self.name].value;
        except:
           self.set(default);
        return result;
    def set(self, value, expires=3600*24*365):
        cherrypy.response.cookie[self.name] = value
        cherrypy.response.cookie[self.name]['expires'] = expires  
        cherrypy.request.cookie[self.name] = value;   # Not sure this is kosher, this is in case it is checked before a roundtrip
    def delete(self):
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
        self.lookup = TemplateLookup(directories=['HTMLTemplates'])
        
    def template(self, name, **kwargs):
        return self.lookup.get_template(name).render(**kwargs);
          
    def show_loginpage(self, error):      
        return self.template("login.html", error = error)
    
    def show_mainpage(self, username):
        project = Cookie('project').get("")
        if not project:
            return self.projects()
        ev3P = ev3project.EV3Project(project, username)
        commits = ev3P.getListOfCommits()
        
        return self.template("mainpage.html", username = username, project = project, commits = commits)
        
    def show_createaccountpage(self, error):
        return self.template("createAccount.html", error = error)
    
    def show_uploadpage(self, project, username, programmer, host):
        return self.template("upload.html", project = project, username = username, programmer = programmer, host = host)
    
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
        host = Cookie('host').get(cherrypy.request.headers['Remote-Addr']);
        username = Cookie('username').get()
        programmer = Cookie('who').get()
        if not username:
           print "No username"
           return self.show_loginpage('')       
         
        return self.template("projects.html",projects=self.get_projectlist(username),host=host,username=username,programmer=programmer)
    @cherrypy.expose
    def changeProject(self, project):
        username = Cookie('username').get()
        if not username:
            return self.show_loginpage('')
        Cookie('project').set(project)
        return self.show_mainpage(username)
                
    @cherrypy.expose
    def newProject(self, project, who, host, ev3file):
        username = Cookie('username').get()
        if not username:
           return self.show_loginpage('')       
        if project in self.get_projectlist(username):
           host = Cookie('host').get(cherrypy.request.headers['Remote-Addr']);
           programmer = Cookie('who').get()            
           return self.template("projects.html",projects=self.get_projectlist(username),host=host,username=username,programmer=programmer, error="Duplicate Project")
              
        ev3data = ev3file.file.read();
        Cookie('project').set(project)
        
        ev3P = ev3project.EV3Project.newProject(username, project, ev3data, who, host)

        return self.show_mainpage(username)    
    @cherrypy.expose
    def login(self,username=None,password=None):
        if self.users.verifyPassword(username, password):
            Cookie('username').set(username)
            print "Logged in as {0}".format(username)
            return self.show_mainpage(username);
        else:
            return self.show_loginpage("Username and password don't match")
    
    @cherrypy.expose
    def createAccount(self):
        return self.show_createaccountpage('')
        
    @cherrypy.expose
    def createUser(self, username, email, password, password2):
        error = ''
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
        Cookie('username').delete()
        Cookie('project').delete()
        Cookie('who').delete()
         
        return self.show_loginpage('')
    
    @cherrypy.expose
    def upload(self):
        host = Cookie('host').get(cherrypy.request.headers['Remote-Addr']);
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
        ev3data = ev3file.file.read();
        ev3P = ev3project.EV3Project(Cookie('project').get(project), Cookie('username').get(''))
        Cookie('host').set(host)
        Cookie('who').set(who)
        
        cid = ev3P.uploadCommit(ev3data, comment, who, host)
        merge_errors = ev3P.merge(cid)
        if merge_errors:
# TODO: do this for real            
           return merge_errors             
        username = Cookie('username').get('')
        return self.mainpage('username')


               
if __name__ == '__main__':
   # This is the configuration and starting of the service
   cherrypy.config.update({'server.socket_host' : "0.0.0.0",
                           'server.socket_port' : 8000})    
  
   file_path = os.getcwd()
   
   cherrypy.quickstart(EV3hub(),'/', 
         {
           '/':
           {
               'tools.staticdir.root' : file_path,
           },
           '/favicon.ico':
           {
               'tools.staticfile.on' : True,
               'tools.staticfile.filename' : file_path + '/static/favicon.ico'
           },
           '/static':
           {
               'tools.staticdir.on' : True,
               'tools.staticdir.dir' : 'static'
           },
         }
      )