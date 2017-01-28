import cherrypy
import os
import ev3project
import json
import string
import time
from mako.template import Template
from mako.lookup import TemplateLookup
import argparse
from operator import itemgetter
from users import Users

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
           result = cherrypy.session.get(self.name)
           if not result:
              self.set(default)
              result = default
        except:
           self.set(default);
        return result;
    def set(self, value):
        cherrypy.session[self.name] = value
    def delete(self):
        cherrypy.session.pop(self.name, None)
        self.set('', 0)  # Way to delete a cookie is to set it with an expiration time of immediate

class EV3hub(object):  
    def __init__(self):
        self.users = Users();
        self.lookup = TemplateLookup(directories=['HTMLTemplates'],default_filters=['h'])
        
    def template(self, name, **kwargs):
        return self.lookup.get_template(name).render(**kwargs);
    
    def get_project(self):
        project = Cookie('project').get('')
        username = Cookie('username').get('')
        return ev3project.EV3Project(project, self.users.get_project_dir(username, project))
          
    def show_loginpage(self, error=''):
        cherrypy.session.regenerate();      
        return self.template("login.html", error = error)
    
    def show_forgotpage(self, username, token, error=''):
        return self.template("forgot.html", username = username, token = token, error = error)
        
    def show_diffpage(self, project, commit1, commit2, files, error=''):
        return self.template("diff.html", project=project, commit1 = commit1, commit2 = commit2, files = files, error = error)
    def show_detailspage(self, project, commit, fileDetails, error=''):
        return self.template("details.html", project=project, commit = commit, fileDetails = fileDetails, error = error)
    def show_mergepage(self, project, commit, different, error=''):
        return self.template("merge.html",project=project, commit = commit, different = different, error = error)
    def show_mainpage(self, username, error=''):
        project = Cookie('project').get("")
        if not project:
            return self.projects()
        ev3P = self.get_project()
        commits = ev3P.getListOfCommits()
        email = self.users.get_email(username)
                   
        return self.template("mainpage.html", username = username, email = email, project = project, commits = commits, failedMerges = ev3P.failedMerges, head= ev3P.head, error=error)
        
    def show_uploadpage(self, project, username, programmer, host):
        return self.template("upload.html", project = project, username = username, programmer = programmer, host = host)
        
    def show_changeprojectpage(self, error=''):
        host = Cookie('host').get(getHostname());
        username = Cookie('username').get()
        programmer = Cookie('who').get()
        if not username:
            return self.show_loginpage('')
            
        return self.template("projects.html",projects=self.users.get_projectlist(username),host=host,username=username,programmer=programmer,error=error)
                    
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
        if self.users.project_exists(username, project):
            Cookie('project').set(project)
            raise cherrypy.HTTPRedirect("/")
            return self.show_mainpage(username)
        else:
            return self.show_changeprojectpage('Please select an existing project')
                
    @cherrypy.expose
    def newProject(self, project, who, host, ev3file):
        project = project
        username = Cookie('username').get()
        if not username:
           return self.show_loginpage('')       
        if self.users.project_exists(username, project):
           return self.show_changeprojectpage('Duplicate Project')
        if not project:   # if blank
           return self.show_changeprojectpage('Blank name for project')
        try:      
           ev3data = ev3file.file.read();
           ev3P = self.users.new_project(username, project, ev3data, who, host)
           Cookie('project').set(project)
           Cookie('who').set(who)
           Cookie('host').set(host)
        except:
           return self.show_changeprojectpage('Error in Project')
        raise cherrypy.HTTPRedirect("/")
        return self.show_mainpage(username)    
    @cherrypy.expose
    def login(self,username=None,password=None):
        if self.users.verify_password(username, password):
            Cookie('username').set(self.users.get(username))
            return self.show_mainpage(username);
        else:
            return self.show_loginpage("Username and password don't match")
    
    @cherrypy.expose
    def createUser(self, username, email, password, password2):
        error = ''
        if password != password2:
            error = "Error: Password's don't match!"
        elif self.users.get(username):
            error = "Error: Username '{0}' already in use!".format(username)
        else:
            self.users.add(username, email, password);
            error = "Account '{0}' created.".format(username)
        return error;
        
    @cherrypy.expose
    def forgotPass(self, username):
        error = self.users.mail_token(username)
        return error;

    @cherrypy.expose
    def forgot(self, username, token):
        return self.show_forgotpage(username, token)

    @cherrypy.expose
    def resetPassword(self, username, token, newpw1, newpw2):
        if self.users.verify_forgot(username, token):
            if newpw1 == newpw2:
                if newpw1:
                    self.users.change_password(username, newpw1)
                    return ""
                else:
                    return "password can't be blank"
            else:
                return "new passwords don't match"
        else:
           return 'Invalid forgot username/token'            
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
    def updateSettings(self, email, newpw1, newpw2, password):
        username = Cookie('username').get('')
        if self.users.verify_password(username, password):
           if newpw1 == newpw2:
               if newpw1:
                   self.users.change_password(username, newpw1)
           else:
               return "new passwords don't match"             
           self.users.change_email(username, email)  
        else:
           return 'Password was incorrect'    
    @cherrypy.expose
    def graph(self, cid):
        ev3P = self.get_project()      
        cherrypy.response.headers['Content-Type'] = 'image/svg+xml'    
        return ev3P.graph(cid)       
        
    @cherrypy.expose
    def merge(self, cid):
        result = ""
        ev3P = self.get_project()        
        commit = ev3P.getCommit(cid)
        (p, added, modified) = ev3P.try_merge(commit)
        
        different = sorted(added+modified, key=unicode.lower)
        
        return self.show_mergepage(ev3P, commit, different);
    @cherrypy.expose
    def manual_merge(self, cid, files):
        ev3P = self.get_project()
        commit_files = []
        head_files = []

        if isinstance(files, basestring):
            info = files.split(':', 1);
            if info[0] == 'head':
                head_files.append(info[1])
            else:
                commit_files.append(info[1])       
        else:    
            for line in files:
                info = line.split(':', 1);
                if info[0] == 'head':
                    head_files.append(info[1])
                else:
                    commit_files.append(info[1])
        error = ev3P.manual_merge(cid, commit_files, head_files)
        return error
        
    @cherrypy.expose
    def download(self, cid):
        ev3P = self.get_project()
  
        if cid == 'head':
          filename = ev3P.name + ".ev3"
        else:
          filename = "{0}-v{1}.ev3".format(ev3P.name, cid)
          
        cherrypy.response.headers['Content-Type'] = 'application/x-download'    
        cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="{0}"'.format(filename)
        return ev3P.download(cid)
    
    @cherrypy.expose
    def settings(self):
        return self.show_settingspage()
                
    @cherrypy.expose
    def uploadDone(self, project, comment, who, host, ev3file):  
        error = '' 
        try:
           Cookie('host').set(host)
           Cookie('who').set(who)
           ev3data = ev3file.file.read();

           ev3P = self.get_project()
           cid = ev3P.uploadCommit(ev3data, comment, who, host)
           if not cid:
               return 'Error: No changes from head, upload not saved'
           merge_errors = ev3P.merge(cid)
           if merge_errors:
              if len(merge_errors) == 1:
                  error = 'Merge Error:'
              else:
                  error = 'Merge Errors:'
              for me in merge_errors:
                  error = error + '\n' + me
        except:
            raise
            error = 'Error in uploading.  Upload not saved'
         
        return error

    @cherrypy.expose
    def ignoreFailedMerge(self, cid, comment):    
        ev3P = self.get_project()
        return ev3P.addIgnoreComment(cid, comment)
    
    @cherrypy.expose
    def details(self, cid):
        ev3P = self.get_project()
        fileDetails = ev3P.getDetails(cid)
        commit = ev3P.getCommit(cid)

        return self.show_detailspage(ev3P.name, commit, fileDetails)    
        
    @cherrypy.expose
    def diff(self, cid1, cid2):
        error = ''
        files = []
        filelist = [];
            
        ev3P = self.get_project()
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
            
        return self.show_diffpage(ev3P.name, commit1, commit2, files)       


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Version Control for ev3")
    parser.add_argument('conf')
    args = parser.parse_args()   
        
    cherrypy.quickstart(EV3hub(),'', args.conf)
