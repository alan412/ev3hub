from unittest.mock import patch

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

    def test_logins(self):
        self.sendForm("/login", 'username=fll447&password=test')
        self.sendForm("/login", 'username=fll447&password=badPassword')

    def test_createUser(self):
        self.sendForm(
            "/createUser", 'username=fred&email=asd&password=pass&password2=fail')
        self.sendForm(
            "/createUser", 'username=fll447&email=asd&password=pass&password2=pass')
        self.sendForm(
            "/createUser", 'username=fred&email=asd&password=pass&password2=pass')
