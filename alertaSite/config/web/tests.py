from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from monitors.models import Monitor, MonitorCheck
from monitors.task_utils import enqueue_task
from monitors.tasks import check_monitor, schedule_checks, _is_local_ip
from projects.models import Project

User = get_user_model()


class MonitorCheckTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='monitor_tester',
            email='monitor_tester@example.com',
            password='testpass123',
        )
        self.project = Project.objects.create(user=self.user, name='Checks Project')
        self.monitor = Monitor.objects.create(
            project=self.project,
            name='Example HTTP',
            url='https://example.com',
            monitor_type='http',
        )

    @patch('monitors.tasks.requests.Session')
    @patch('monitors.tasks.socket.gethostbyname', return_value='93.184.216.34')
    def test_http_check_marks_monitor_up(self, _mock_dns, mock_session_cls):
        response = MagicMock()
        response.status_code = 200
        response.url = 'https://example.com'
        session = MagicMock()
        session.get.return_value = response
        mock_session_cls.return_value = session

        result = check_monitor(str(self.monitor.id))

        self.monitor.refresh_from_db()
        self.assertIn('up', result.lower())
        self.assertEqual(self.monitor.last_status, 'up')
        self.assertEqual(MonitorCheck.objects.filter(monitor=self.monitor).count(), 1)

    @patch('monitors.tasks.socket.gethostbyname', return_value='127.0.0.1')
    def test_ssrf_blocks_localhost(self, _mock_dns):
        local_monitor = Monitor.objects.create(
            project=self.project,
            name='Localhost',
            url='http://127.0.0.1',
            monitor_type='http',
        )

        result = check_monitor(str(local_monitor.id))

        local_monitor.refresh_from_db()
        self.assertEqual(local_monitor.last_status, 'down')
        self.assertIn('SSRF', result)

    @patch('monitors.tasks.enqueue_task')
    def test_schedule_checks_uses_enqueue_helper(self, mock_enqueue):
        self.monitor.last_check_at = None
        self.monitor.save(update_fields=['last_check_at'])

        message = schedule_checks()

        mock_enqueue.assert_called_once()
        self.assertIn('Triggered check for 1 monitors', message)

    def test_is_local_ip_detects_private_ranges(self):
        self.assertTrue(_is_local_ip('127.0.0.1'))
        self.assertTrue(_is_local_ip('10.0.0.5'))
        self.assertFalse(_is_local_ip('8.8.8.8'))

    @patch('monitors.tasks.check_monitor.delay', side_effect=ConnectionError('redis down'))
    def test_enqueue_task_falls_back_to_sync(self, mock_delay):
        task = MagicMock()
        task.delay.side_effect = ConnectionError('redis down')
        task.run.return_value = 'ok'

        result = enqueue_task(task, 'abc')

        task.delay.assert_called_once_with('abc')
        task.run.assert_called_once_with('abc')
        self.assertEqual(result, 'ok')


class LandingPageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='landing_user',
            email='landing_user@example.com',
            password='testpass123',
        )

    def test_landing_page_renders_for_guest(self):
        response = self.client.get(reverse('web:landing'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'landing-hero')
        self.assertContains(response, reverse('web:register'))
        self.assertContains(response, reverse('web:login'))

    def test_landing_page_shows_dashboard_for_authenticated_user(self):
        self.client.login(username='landing_user', password='testpass123')

        response = self.client.get(reverse('web:landing'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Панель управления')
        self.assertNotContains(response, 'Начать бесплатно')

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('web:dashboard'))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('web:login')))

    def test_apk_download_returns_404_when_missing(self):
        response = self.client.get(reverse('web:download_apk'))

        self.assertEqual(response.status_code, 404)

    def test_logout_redirects_to_landing(self):
        self.client.login(username='landing_user', password='testpass123')

        response = self.client.get(reverse('web:logout'))

        self.assertRedirects(response, reverse('web:landing'))

    @patch('monitors.tasks.requests.Session')
    @patch('monitors.tasks.socket.gethostbyname', return_value='93.184.216.34')
    def test_monitor_run_check_endpoint_updates_status(self, _mock_dns, mock_session_cls):
        project = Project.objects.create(user=self.user, name='Web Checks')
        monitor = Monitor.objects.create(
            project=project,
            name='Run Now',
            url='https://example.org',
            monitor_type='http',
        )
        response = MagicMock()
        response.status_code = 200
        response.url = 'https://example.org'
        session = MagicMock()
        session.get.return_value = response
        mock_session_cls.return_value = session

        self.client.login(username='landing_user', password='testpass123')
        response = self.client.get(reverse('web:monitor_run_check', args=[monitor.pk]))

        monitor.refresh_from_db()
        self.assertRedirects(response, reverse('web:monitor_detail', args=[monitor.pk]))
        self.assertEqual(monitor.last_status, 'up')
