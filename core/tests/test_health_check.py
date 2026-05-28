""" Health check tests """
from django.test import SimpleTestCase
from django.urls import reverse


class HealthCheckTests(SimpleTestCase):
    """ Tests de health check endpoint """

    def test_health_check_return_ok(self):
        """ Testa se o health check retorna o status code 200 """
        
        response = self.client.get(reverse('core:health-check'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'OK')
