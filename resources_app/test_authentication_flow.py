import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from .models import StudentProfile


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

    def test_all_signup_urls_use_the_student_registration_form(self):
        response = self.client.get('/accounts/signup/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create your student account')
        self.assertContains(response, 'name="gender"')
        self.assertContains(response, 'name="password1"')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_signup_email_verification_password_login_and_code_work_end_to_end(self):
        response = self.client.post(
            '/register/',
            {
                'username': 'newstudent',
                'first_name': 'New',
                'last_name': 'Student',
                'email': 'NewStudent@Example.com',
                'phone': '08098765432',
                'gender': StudentProfile.Gender.NON_BINARY,
                'password1': 'SafeCoursePass!882',
                'password2': 'SafeCoursePass!882',
            },
        )
        self.assertEqual(response.status_code, 302)

        user = get_user_model().objects.get(username='newstudent')
        self.assertEqual(user.email, 'newstudent@example.com')
        self.assertFalse(user.is_active)
        verification_url = re.search(
            r'http://testserver\S+',
            mail.outbox[0].body,
        ).group()
        response = self.client.get(verification_url)
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

        response = self.client.post(
            '/accounts/login/',
            {'username': 'NEWSTUDENT@EXAMPLE.COM', 'password': 'SafeCoursePass!882'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)
        login_code = re.search(r'\b\d{6}\b', mail.outbox[-1].body).group()

        response = self.client.post(
            '/accounts/verify-login/',
            {'code': login_code},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get('/dashboard/').status_code, 200)

    def test_signup_rejects_case_insensitive_duplicate_email(self):
        response = self.client.post(
            '/register/',
            {
                'username': 'anotherstudent',
                'first_name': 'Another',
                'last_name': 'Student',
                'email': 'STUDENT@EXAMPLE.COM',
                'phone': '08098765432',
                'gender': StudentProfile.Gender.MALE,
                'password1': 'SafeCoursePass!882',
                'password2': 'SafeCoursePass!882',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'An account with this email already exists')
        self.assertFalse(
            get_user_model().objects.filter(username='anotherstudent').exists()
        )
