import base64

from unittest.mock import patch

import requests
import cherrypy
from cherrypy.test import helper
from cherrypy.lib.sessions import RamSession

from ev3hub import EV3hub


class SimpleCPTest(helper.CPWebCase):
    @staticmethod
    def setup_server():
        cherrypy.tree.mount(EV3hub(), '/', 'development.conf')

    def getPageWithPatch(self, page, headers=None, method='GET', body=None, expectedStatus=200):
        sess_mock = RamSession()
        sess_mock['username'] = 'fll447'
        sess_mock['project'] = 'AnimalAllies'
        with patch('cherrypy.session', sess_mock, create=True):
            self.getPage(page, headers, method, body)
            self.assertStatus(expectedStatus)

    def sendForm(self, page, body, expectedStatus=200):
        headers = [
            ('Content-type', 'application/x-www-form-urlencoded; charset=UTF-8'),
            ('Content-length', str(len(body)))]
        self.getPageWithPatch(page, headers, 'POST', body, expectedStatus)

    def test_login(self):
        self.getPage("/")
        self.assertStatus('200 OK')

    def test_mainpage(self):
        self.getPageWithPatch("/")

    def test_detailspage(self):
        self.sendForm("/details", 'cid=6')
        self.sendForm("/graph", 'cid=6')
        self.sendForm("/graphPage", 'cid=6')

    def test_projectList(self):
        self.getPageWithPatch("/projects")

    def test_logout(self):
        self.getPageWithPatch("/logout")

    def test_showUpload(self):
        self.getPageWithPatch("/upload")
        self.getPage('/upload')   # without session data
        self.assertStatus('200 OK')

    def test_getTags(self):
        self.getPageWithPatch("/tags")

    def test_add_and_del_Tags(self):
        self.sendForm("/createTag", 'cid=6&description=test')
        self.sendForm("/removeTag", 'tag=test')

    def test_diff(self):
        self.sendForm("/diff", 'cid1=6&cid2=5')

    def test_change_to_bogus_project(self):
        self.sendForm("/changeProject", 'project=BogusProject')

    def test_change_project(self):
        self.sendForm("/changeProject", 'project=AnimalAllies',
                      expectedStatus=303)

    def test_download(self):
        self.sendForm("/download", 'cid=head')
        self.sendForm("/download", 'cid=6')

    def test_changeProject_not_logged_in(self):
        body = "project=FakeProject"
        headers = [
            ('Content-type', 'application/x-www-form-urlencoded; charset=UTF-8'),
            ('Content-length', str(len(body)))]
        self.getPage('/changeProject', headers, 'POST', body)
        self.assertStatus(200)

    def test_listProjects_not_logged_in(self):
        self.getPage('/projects')
        self.assertStatus(200)

    def test_getMergePage(self):
        self.sendForm("/merge", 'cid=5')

    def test_ignoreFailedMerge(self):
        self.sendForm("/ignoreFailedMerge", 'cid=5&comment=Miscellaneous')

    def test_logins(self):
        self.sendForm("/login", 'username=fll447&password=kira')
        self.sendForm("/login", 'username=fll447&password=badPassword')

    def test_createUser(self):
        self.sendForm(
            "/createUser", 'username=fred&email=asd&password=pass&password2=fail')
        self.sendForm(
            "/createUser", 'username=fll447&email=asd&password=pass&password2=pass')
        self.sendForm(
            "/createUser", 'username=fred&email=asd&password=pass&password2=pass')

    def test_forgotPass(self):
        self.sendForm('/forgotPass', 'username=fll447')

    def test_forgot(self):
        self.sendForm('/forgot', 'username=fll447&token=ABCD')

    def test_rename_project(self):
        # rename (and back)
        self.sendForm('/renameProject', 'project=AnimalAllies&newName=tmpProj')
        self.sendForm('/renameProject', 'project=tmpProj&newName=AnimalAllies')

        # rename bad one
        self.sendForm('/renameProject', 'project=bogus&newName=tmpProj')

    def test_remove_and_restore_project(self):
        # bad password
        self.sendForm('/removeProject', 'project=AnimalAllies&password=foof')
        # bad project
        self.sendForm('/removeProject', 'project=bogus&password=kira')
        # actual removal
        self.sendForm('/removeProject', 'project=AnimalAllies&password=kira')

        # restore (actual)
        self.sendForm('/restoreProject', 'project=AnimalAllies')
        # bad restore
        self.sendForm('/restoreProject', 'project=bogus')

    def test_update_settings(self):
        self.sendForm(
            '/updateSettings', 'email=alan@randomsmiths.com&newpw1=&newpw2=&password=bogus')
        self.sendForm(
            '/updateSettings',
            'email=alan@randomsmiths.com&newpw1=right&newpw2=wrong&password=kira')
        self.sendForm(
            '/updateSettings', 'email=alan@randomsmiths.com&newpw1=kira&newpw2=kira&password=kira')
        self.sendForm(
            '/updateSettings', 'email=joe@randomsmiths.com&newpw1=kira&newpw2=kira&password=kira')
        self.sendForm(
            '/updateSettings', 'email=alan@randomsmiths.com&newpw1=kira&newpw2=kira&password=kira')

    def test_new_project(self):
        url = 'http://newProject'
        data = {'project': 'test12345', 'who': 'me', 'host': '127.0.0.1'}
        files = {'ev3file': ('newFile.ev3', open('data/newFile.ev3', 'rb'))}
        req = requests.Request(url=url,
                               files=files, data=data).prepare()
        newHeaders = [('Content-type', req.headers['Content-type']),
                      ('Content-Length', req.headers['Content-Length'])]

        self.getPageWithPatch('/newProject', newHeaders,
                              'POST', req.body, expectedStatus=303)
        data = {'project': 'test12345', 'comment': 'test',
                'who': 'me', 'host': '127.0.0.1'}
        files = {'ev3file': ('newFile.ev3', open('data/newFile.ev3', 'rb'))}
        req = requests.Request(url=url,
                               files=files, data=data).prepare()
        newHeaders = [('Content-type', req.headers['Content-type']),
                      ('Content-Length', req.headers['Content-Length'])]

        self.getPageWithPatch('/uploadDone', newHeaders,
                              'POST', req.body)
