"""Main web interface for ev3hub"""
import argparse
import cherrypy
from mako.lookup import TemplateLookup
from users import Users


class Cookie(object):
    """Abstracts cookies so they can be in sessions"""

    def __init__(self, name):
        self.name = name

    def get(self, default=''):
        """Get the value of the cookie or set if doesn't exist"""
        if self.name in cherrypy.session:
            return cherrypy.session[self.name]
        else:
            self.set(default)
            return default

    def set(self, value):
        """Set the value of the cookie"""
        cherrypy.session[self.name] = value


class EV3hub(object):
    """"Web interface for EV3Hub"""

    def __init__(self):
        self.users = Users()
        self.lookup = TemplateLookup(
            directories=['HTMLTemplates'], default_filters=['h'])

    def get_hostname(self):
        """return the hostname"""
        try:
            return Cookie('host').get(cherrypy.request.headers['X-Real-IP'])
        except KeyError:
            return Cookie('host').get(cherrypy.request.headers['Remote-Addr'])

    def template(self, name, **kwargs):
        """return template with substitutions"""
        return self.lookup.get_template(name).render(**kwargs)

    def get_project(self):
        """Get the project user is working on"""
        project = Cookie('project').get('')
        username = Cookie('username').get('')
        ev3p = self.users.get_project(username, project)
        if ev3p:
            Cookie('project').set(ev3p.name)
        return ev3p

    def show_loginpage(self, error=''):
        """Clear session and show login page"""
        cherrypy.session.regenerate()
        return self.template("login.html", error=error)

    def show_mainpage(self, username, error=''):
        """Shows the main page of commits if we have a project"""
        ev3P = self.get_project()
        if not ev3P:
            return self.projects()
        project_name = ev3P.name
        commits = ev3P.getListOfCommits()
        email = self.users.get_email(username)

        return self.template("mainpage.html", username=username, email=email,
                             project=project_name, commits=commits,
                             failedMerges=ev3P.failedMerges, head=ev3P.head, error=error)

    def show_changeprojectpage(self, error=''):
        """Show the page for changing projects"""
        host = self.get_hostname()
        username = Cookie('username').get()
        programmer = Cookie('who').get()
        if not username:
            return self.show_loginpage('')

        return self.template("projects.html", projects=self.users.get_projectlist(username),
                             host=host, username=username, programmer=programmer, error=error)

    @cherrypy.expose
    def index(self):
        """Shows main page of ev3hub or forces login if not logged in"""
        username = Cookie('username').get()
        if not username:
            return self.show_loginpage('')
        return self.show_mainpage(username)

    @cherrypy.expose
    def projects(self):
        """default changing projects"""
        return self.show_changeprojectpage()

    @cherrypy.expose
    def changeProject(self, project):
        """ask to change project"""
        username = Cookie('username').get()
        if not username:
            return self.show_loginpage('')
        if self.users.project_exists(username, project):
            Cookie('project').set(project)
            raise cherrypy.HTTPRedirect("/")
        else:
            return self.show_changeprojectpage('Please select an existing project')

    @cherrypy.expose
    def newProject(self, project, who, host, ev3file):
        """create new project"""
        project = project
        username = Cookie('username').get()
        if not username:
            return self.show_loginpage('')
        if self.users.project_exists(username, project):
            return self.show_changeprojectpage('Duplicate Project')
        if not project:   # if blank
            return self.show_changeprojectpage('Blank name for project')
        try:
            ev3data = ev3file.file.read()
            self.users.new_project(username, project, ev3data, who, host)
            Cookie('project').set(project)
            Cookie('who').set(who)
            Cookie('host').set(host)
        except:  # pylint: disable=bare-except
            return self.show_changeprojectpage('Error in Project')
        raise cherrypy.HTTPRedirect("/")

    @cherrypy.expose
    def login(self, username=None, password=None):
        """login user"""
        if self.users.verify_password(username, password):
            Cookie('username').set(self.users.get(username))
            return self.show_mainpage(username)
        else:
            return self.show_loginpage("Username and password don't match")

    @cherrypy.expose
    def createUser(self, username, email, password, password2):
        """create new account"""
        error = ''
        if password != password2:
            error = "Error: Password's don't match!"
        elif self.users.get(username):
            error = "Error: Username '{0}' already in use!".format(username)
        else:
            self.users.add(username, email, password)
            error = "Account '{0}' created.".format(username)
        return error

    @cherrypy.expose
    def forgotPass(self, username):
        """forgot password"""
        error = self.users.mail_token(username)
        return error

    @cherrypy.expose
    def forgot(self, username, token):
        """"load forgot password page"""
        return self.template("forgot.html", username=username, token=token, error='')

    @cherrypy.expose
    def resetPassword(self, username, token, newpw1, newpw2):
        """reset password - from forgot token"""
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
            return 'Invalid forgot username/token.  Tokens expire after 24 hours.'

    @cherrypy.expose
    def logout(self):
        """logout user"""
        cherrypy.lib.sessions.expire()

        return self.show_loginpage('')

    @cherrypy.expose
    def upload(self):
        """get upload page"""
        host = self.get_hostname()
        project = Cookie('project').get('')
        username = Cookie('username').get('')
        programmer = Cookie('who').get('')

        if project and username:
            return self.template("upload.html", project=project,
                                 username=username, programmer=programmer, host=host)
        else:
            return self.projects()

    @cherrypy.expose
    def removeProject(self, project, password):
        """remove project"""
        username = Cookie('username').get('')
        if self.users.verify_password(username, password):
            if self.users.remove_project(username, project):
                return 'Project "' + project + '" deleted'
            else:
                return 'Error removing project'
        else:
            return 'Incorrect password'

    @cherrypy.expose
    def renameProject(self, project, newName):
        """rename project"""
        username = Cookie('username').get('')
        if self.users.rename_project(username, project, newName):
            return 'Project renamed'
        else:
            return 'Error renaming project'

    @cherrypy.expose
    def restoreProject(self, project):
        """restore project"""
        username = Cookie('username').get('')
        if self.users.restore_project(username, project):
            return 'Project restored'
        else:
            return 'Error restoring project'

    @cherrypy.expose
    def updateSettings(self, email, newpw1, newpw2, password):
        """change password or e-mail"""
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
    def graphPage(self, cid):
        """show graph of commit"""
        ev3P = self.get_project()
        commit = ev3P.getCommit(cid)

        return self.template("graph.html", project=ev3P.name, commit=commit)

    @cherrypy.expose
    def graph(self, cid, showTest=False):
        """get graph image"""
        ev3P = self.get_project()
        cherrypy.response.headers['Content-Type'] = 'image/svg+xml'
        return ev3P.graph(cid, showTest)

    @cherrypy.expose
    def merge(self, cid):
        """get merge page"""
        ev3P = self.get_project()
        commit = ev3P.getCommit(cid)
        (_, added, modified) = ev3P.try_merge(commit)
        different = sorted(added+modified, key=str.lower)
        return self.template("merge.html", project=ev3P, commit=commit, different=different)

    @cherrypy.expose
    def manual_merge(self, cid, files):
        """perform a manual merge"""
        ev3P = self.get_project()
        commit_files = []
        head_files = []

        if isinstance(files, str):
            info = files.split(':', 1)
            if info[0] == 'head':
                head_files.append(info[1])
            else:
                commit_files.append(info[1])
        else:
            for line in files:
                info = line.split(':', 1)
                if info[0] == 'head':
                    head_files.append(info[1])
                else:
                    commit_files.append(info[1])
        error = ev3P.manual_merge(cid, commit_files, head_files)
        return error

    @cherrypy.expose
    def download(self, cid):
        """download a ev3 file"""
        ev3P = self.get_project()

        if cid == 'head':
            filename = ev3P.name + ".ev3"
        else:
            filename = "{0}-v{1}.ev3".format(ev3P.name, cid)

        cherrypy.response.headers['Content-Type'] = 'application/x-download'
        cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="{0}"'.format(
            filename)
        return ev3P.download(cid)

    @cherrypy.expose
    def uploadDone(self, project, comment, who, host, ev3file):
        """send upload commit"""
        error = ''

        Cookie('host').set(host)
        Cookie('who').set(who)

        ev3P = self.get_project()
        if ev3P.name != project:
            return 'Error: uploading to different project!'
        try:
            ev3data = ev3file.file.read()
            cid = ev3P.uploadCommit(ev3data, comment, who, host)
        except:  # pylint: disable=bare-except
            return 'Error in uploading.  Upload not saved'

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

        return error

    @cherrypy.expose
    def ignoreFailedMerge(self, cid, comment):
        """add ignored fail merge comment"""
        ev3P = self.get_project()
        return ev3P.addIgnoreComment(cid, comment)

    @cherrypy.expose
    def changeHead(self, cid):
        """changes what the HEAD is for a project"""
        ev3P = self.get_project()
        return ev3P.change_head(cid)

    @cherrypy.expose
    def createTag(self, cid, description):
        """create a tag for a commit id"""
        ev3P = self.get_project()
        return ev3P.addTag(cid, description)

    @cherrypy.expose
    def removeTag(self, tag):
        """remove a tag from the project"""
        ev3P = self.get_project()
        return ev3P.removeTag(tag)

    @cherrypy.expose
    def details(self, cid):
        """get details page for a commit"""
        ev3P = self.get_project()
        fileDetails = ev3P.getDetails(cid)
        commit = ev3P.getCommit(cid)

        return self.template("details.html", project=ev3P.name,
                             commit=commit, fileDetails=fileDetails)

    @cherrypy.expose
    def tags(self):
        """get tags info"""
        return self.template("tags.html", project=self.get_project())

    @cherrypy.expose
    def diff(self, cid1, cid2):
        """show diff between two id's"""
        files = []
        filelist = []

        ev3P = self.get_project()
        commit1 = ev3P.getCommit(cid1)
        commit2 = ev3P.getCommit(cid2)

        for filename in commit1.files():
            if filename not in filelist:
                filelist.append(filename)

        for filename in commit2.files():
            if filename not in filelist:
                filelist.append(filename)

        for filename in sorted(filelist, key=str.lower):
            sha1 = commit1.getSHA(filename)
            sha2 = commit2.getSHA(filename)
            if (sha1 == sha2) and (not sha1):   # is a variable
                if filename in commit1.files():
                    sha1 = 'var'
                if filename in commit2.files():
                    sha2 = 'var'
            files.append({'name': filename, '1': sha1, '2': sha2})

        return self.template("diff.html", project=ev3P, commit1=commit1,
                             commit2=commit2, files=files)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Version Control for ev3")
    parser.add_argument('conf')
    args = parser.parse_args()

    cherrypy.quickstart(EV3hub(), '', args.conf)
