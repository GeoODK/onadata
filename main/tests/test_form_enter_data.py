import re

from urlparse import urlparse
from time import time
from django.core.urlresolvers import reverse
from django.core.validators import URLValidator
from django.conf import settings
from nose import SkipTest

from test_base import MainTestCase
from main.views import set_perm, show
from main.models import MetaData
from odk_logger.views import enter_data
from utils.viewer_tools import enketo_url


class TestFormEnterData(MainTestCase):

    def setUp(self):
        MainTestCase.setUp(self)
        self._create_user_and_login()
        self._publish_transportation_form_and_submit_instance()
        self.perm_url = reverse(set_perm, kwargs={
            'username': self.user.username, 'id_string': self.xform.id_string})
        self.show_url = reverse(show, kwargs={'uuid': self.xform.uuid})
        self.url = reverse(enter_data, kwargs={
            'username': self.user.username,
            'id_string': self.xform.id_string
        })

        #for enketo use only

    def _running_enketo(self):
        if hasattr(settings, 'ENKETO_URL') and \
                self._check_url(settings.ENKETO_URL):
            return True
        return False

    def test_enketo_remote_server(self):
        if not self._running_enketo():
            raise SkipTest
        server_url = 'https://testserver.com/bob'
        form_id = "test_%s" % re.sub(re.compile("\."), "_", str(time()))
        url = enketo_url(server_url, form_id)
        self.assertIsInstance(url, basestring)
        self.assertIsNone(URLValidator()(url))

    def test_enter_data_redir(self):
        response = self.client.get(self.url)
        #make sure response redirect to an enketo site
        enketo_base_url = urlparse(settings.ENKETO_URL).netloc
        redirected_base_url = urlparse(response['Location']).netloc
        #TODO: checking if the form is valid on enketo side
        self.assertIn(enketo_base_url, redirected_base_url)
        self.assertEqual(response.status_code, 302)

    def test_enter_data_no_permission(self):
        response = self.anon.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_public_with_link_to_share_toggle_on(self):
        #sharing behavior as of 09/13/2012:
        #it requires both data_share and form_share both turned on
        #in order to grant anon access to form uploading
        #TODO: findout 'for_user': 'all' and what it means
        response = self.client.post(self.perm_url, {'for_user': 'all',
                                    'perm_type': 'link'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MetaData.public_link(self.xform), True)
        #toggle shared on
        self.xform.shared = True
        self.xform.shared_data = True
        self.xform.save()
        response = self.anon.get(self.show_url)
        self.assertEqual(response.status_code, 302)
        response = self.anon.get(self.url)
        status_code = 302 if self._running_enketo() else 403
        self.assertEqual(response.status_code, status_code)

    def test_enter_data_non_existent_user(self):
        url = reverse(enter_data, kwargs={
            'username': 'nonexistentuser',
            'id_string': self.xform.id_string
        })
        response = self.anon.get(url)
        self.assertEqual(response.status_code, 404)
