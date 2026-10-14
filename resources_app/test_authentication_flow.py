from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings


class LoginFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='student',
            email='student@example.com',
            password='CoursePass!882',
        )

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_login_accepts_email_and_sends_verification_code(self):
        response = self.client.post(
            '/accounts/login/',
            {'username': 'STUDENT@EXAMPLE.COM', 'password': 'CoursePass!882'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['student@example.com'])
        self.assertEqual(
            mail.outbox[0].subject,
            'Your HiiT login verification code',
        )

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_login_accepts_username_with_different_case_and_surrounding_spaces(self):
        response = self.client.post(
            '/accounts/login/',
            {'username': '  STUDENT  ', 'password': 'CoursePass!882'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)
        self.assertEqual(len(mail.outbox), 1)

    def test_login_page_exposes_password_reset_link(self):
        response = self.client.get('/accounts/login/')

        self.assertContains(response, 'Username or email')
        self.assertContains(response, 'Forgot your password?')
        self.assertContains(response, '/accounts/password/reset/')
