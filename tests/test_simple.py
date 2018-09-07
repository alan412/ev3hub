from unittest.mock import patch

import cherrypy
from cherrypy.test import helper
from cherrypy.lib.sessions import RamSession

from ev3hub import EV3hub


class SimpleCPTest(helper.CPWebCase):
    @staticmethod
    def setup_server():
        cherrypy.tree.mount(EV3hub(), '/', 'development.conf')

    def test_login(self):
        self.getPage("/")
        self.assertStatus('200 OK')

    def test_mainpage(self):
        sess_mock = RamSession()
        sess_mock['username'] = 'fll447'
        sess_mock['project'] = 'AnimalAllies'
        with patch('cherrypy.session', sess_mock, create=True):
            self.getPage("/")
        self.assertStatus('200 OK')

    def test_detailspage(self):
        sess_mock = RamSession()
        sess_mock['username'] = 'fll447'
        sess_mock['project'] = 'AnimalAllies'
        with patch('cherrypy.session', sess_mock, create=True):
            self.getPage("/")
            headers = [
                ('Content-type', 'application/x-www-form-urlencoded; charset=UTF-8'),
                ('Content-length', '5')]
            body = 'cid=6'
            self.getPage("/details", headers, 'POST', body)
            self.assertStatus('200 OK')
            self.getPage("/graph", headers, 'POST', body)

    def test_projectList(self):
        sess_mock = RamSession()
        sess_mock['username'] = 'fll447'
        sess_mock['project'] = 'AnimalAllies'
        with patch('cherrypy.session', sess_mock, create=True):
            self.getPage("/projects")
        self.assertStatus('200 OK')

    def test_logout(self):
        sess_mock = RamSession()
        sess_mock['username'] = 'fll447'
        sess_mock['project'] = 'AnimalAllies'
        with patch('cherrypy.session', sess_mock, create=True):
            self.getPage("/logout")
        self.assertStatus('200 OK')

    def test_showUpload(self):
        sess_mock = RamSession()
        sess_mock['username'] = 'fll447'
        sess_mock['project'] = 'AnimalAllies'
        with patch('cherrypy.session', sess_mock, create=True):
            self.getPage("/upload")
        self.assertStatus('200 OK')

    def test_diff(self):
        sess_mock = RamSession()
        sess_mock['username'] = 'fll447'
        sess_mock['project'] = 'AnimalAllies'
        with patch('cherrypy.session', sess_mock, create=True):
            headers = [
                ('Content-type', 'application/x-www-form-urlencoded; charset=UTF-8'),
                ('Content-length', '13')]
            body = 'cid1=6&cid2=5'
            self.getPage("/diff", headers, 'POST', body)
        self.assertStatus('200 OK')
