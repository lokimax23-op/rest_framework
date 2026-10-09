import hashlib
import hmac
import json
import re
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    Course,
    Enrollment,
    LearningResource,
    NewsletterSubscription,
    PortalSubscription,
    StudentProfile,
    SubscriptionCheckout,
)


def force_login_verified(client, user):
    client.force_login(user)
    session = client.session
    session['email_2fa_pending'] = False
    session.save()


class LearningResourceApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.author = user_model.objects.create_user(
            username='author',
            password='test-password',
        )
        self.other_user = user_model.objects.create_user(
            username='other',
            password='test-password',
        )
        self.resource = LearningResource.objects.create(
            title='Django basics',
            category='Programming',
            description='An introduction to Django.',
            author=self.author,
        )

    def test_list_resources_is_public_and_ordered(self):
        response = self.client.get('/resources/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Django basics')

    def test_create_resource_requires_authentication(self):
        response = self.client.post(
            '/resources/',
            {
                'title': 'New resource',
                'category': 'Programming',
                'description': 'Resource description',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_is_set_as_author_on_create(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(
            '/resources/',
            {
                'title': 'New resource',
                'category': 'Programming',
                'description': 'Resource description',
                'author': self.author.pk,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['author'], self.other_user.pk)

    def test_only_author_can_update_or_delete_resource(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.patch(
            f'/resources/{self.resource.pk}/',
            {'title': 'Changed title'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.delete(f'/resources/{self.resource.pk}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_can_update_and_delete_resource(self):
        self.client.force_authenticate(user=self.author)
        response = self.client.patch(
            f'/resources/{self.resource.pk}/',
            {'title': 'Updated title'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.title, 'Updated title')

        response = self.client.delete(f'/resources/{self.resource.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            LearningResource.objects.filter(pk=self.resource.pk).exists()
        )


class StudentPortalTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='student',
            password='CoursePass!882',
            first_name='Ada',
            last_name='Okafor',
            email='ada@example.com',
        )
        self.profile = StudentProfile.objects.create(
            user=self.user,
            phone='08012345678',
            registration_number='HIT-2026-001',
        )
        self.instructor = get_user_model().objects.create_user(
            username='instructor',
            first_name='Tunde',
            last_name='Adebayo',
        )
        self.course = Course.objects.create(
            code='PY101',
            title='Python Foundations',
            description='Learn Python programming fundamentals.',
            instructor=self.instructor,
            duration_weeks=8,
        )

    def test_homepage_uses_live_courses_and_counts(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Python Foundations')
        self.assertContains(response, 'Available courses')
        self.assertContains(response, 'HiiT Learning Hub')

    def test_starter_courses_are_loaded_by_migration(self):
        expected_codes = {'WEB101', 'PYT101', 'UIX101', 'DBA101', 'CYB101', 'DSA101'}

        self.assertTrue(
            expected_codes.issubset(
                set(Course.objects.values_list('code', flat=True))
            )
        )

    def test_homepage_shows_course_enrollment_activity(self):
        Enrollment.objects.create(student=self.profile, course=self.course)

        response = self.client.get('/')

        self.assertContains(response, '1 learner')

    def test_catalog_search_renders_matching_course(self):
        response = self.client.get('/courses/?q=python')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Python Foundations')

    def test_catalog_ajax_search_returns_course_data(self):
        response = self.client.get('/courses/?format=json&q=PY101')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['courses'][0]['code'], 'PY101')
        self.assertEqual(response.json()['courses'][0]['instructor'], 'Tunde Adebayo')

    def test_student_dashboard_requires_authentication(self):
        response = self.client.get('/dashboard/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_staff_without_student_profile_is_redirected_to_admin(self):
        admin = get_user_model().objects.create_superuser(
            username='portaladmin',
            email='admin@example.com',
            password='AdminPass!882',
        )
        force_login_verified(self.client, admin)

        response = self.client.get('/dashboard/')

        self.assertRedirects(response, '/admin/')

    def test_account_without_student_profile_does_not_raise_404(self):
        profileless_user = get_user_model().objects.create_user(
            username='profileless',
            password='CoursePass!882',
        )
        force_login_verified(self.client, profileless_user)

        response = self.client.get('/dashboard/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        self.assertContains(
            self.client.get(response.url),
            'does not have a student profile',
        )

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_student_login_requires_email_code_before_dashboard(self):
        response = self.client.post(
            '/accounts/login/',
            {'username': 'student', 'password': 'CoursePass!882'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/dashboard/')
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['ada@example.com'])

        response = self.client.get('/dashboard/')
        self.assertRedirects(
            response,
            '/accounts/verify-login/',
            fetch_redirect_response=False,
        )
        email_body = str(mail.outbox[0].body)
        codes = re.findall(r'\b\d{6}\b', email_body)
        self.assertEqual(len(codes), 1)
        code = codes[0]
        response = self.client.post('/accounts/verify-login/', {'code': code})
        self.assertRedirects(response, '/dashboard/', fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].to, ['ada@example.com'])
        self.assertEqual(mail.outbox[1].subject, 'HiiT account login alert')
        self.assertEqual(self.client.get('/dashboard/').status_code, 200)

        response = self.client.post('/accounts/logout/')
        self.assertRedirects(response, '/')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_authenticated_student_sees_enrollments(self):
        Enrollment.objects.create(student=self.profile, course=self.course)
        force_login_verified(self.client, self.user)

        response = self.client.get('/dashboard/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Python Foundations')
        self.assertContains(response, 'HIT-2026-001')

    def test_enrollment_requires_login_and_post(self):
        response = self.client.post(f'/courses/{self.course.pk}/enroll/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

        force_login_verified(self.client, self.user)
        response = self.client.get(f'/courses/{self.course.pk}/enroll/')
        self.assertRedirects(response, '/courses/')
        self.assertFalse(Enrollment.objects.exists())

    def test_student_can_enroll_once_and_existing_enrollment_is_not_duplicated(self):
        force_login_verified(self.client, self.user)

        response = self.client.post(f'/courses/{self.course.pk}/enroll/')
        self.assertRedirects(response, '/dashboard/')
        enrollment = Enrollment.objects.get(student=self.profile, course=self.course)
        self.assertEqual(enrollment.status, Enrollment.Status.ACTIVE)

        response = self.client.post(f'/courses/{self.course.pk}/enroll/')
        self.assertRedirects(response, '/dashboard/')
        self.assertEqual(Enrollment.objects.filter(student=self.profile).count(), 1)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_student_registration_sends_verification_email(self):
        response = self.client.post(
            '/register/',
            {
                'username': 'newstudent',
                'first_name': 'New',
                'last_name': 'Student',
                'email': 'new@example.com',
                'phone': '08098765432',
                'registration_number': 'HIT-2026-002',
                'password1': 'SafeCoursePass!882',
                'password2': 'SafeCoursePass!882',
            },
        )

        self.assertRedirects(response, '/accounts/login/')
        created_user = get_user_model().objects.get(username='newstudent')
        self.assertFalse(created_user.is_active)
        self.assertTrue(
            StudentProfile.objects.filter(
                user=created_user,
                registration_number='HIT-2026-002',
            ).exists()
        )
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to, ['new@example.com'])
        self.assertEqual(mail.outbox[1].to, ['new@example.com'])
        self.assertEqual(mail.outbox[1].subject, 'HiiT account signup alert')
        self.assertIn('A signup to your HiiT account', mail.outbox[1].body)

        email_body = str(mail.outbox[0].body)
        verification_urls = re.findall(r'http://testserver\S+', email_body)
        self.assertEqual(len(verification_urls), 1)
        verification_url = verification_urls[0]
        response = self.client.get(verification_url)
        self.assertRedirects(response, '/accounts/login/')
        created_user.refresh_from_db()
        self.assertTrue(created_user.is_active)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_login_code_rejects_incorrect_code(self):
        self.client.post(
            '/accounts/login/',
            {'username': 'student', 'password': 'CoursePass!882'},
        )

        response = self.client.post('/accounts/verify-login/', {'code': 'not-a-code'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'verification code is incorrect')
        self.assertTrue(self.client.session['email_2fa_pending'])
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_too_many_incorrect_login_codes_signs_user_out(self):
        self.client.post(
            '/accounts/login/',
            {'username': 'student', 'password': 'CoursePass!882'},
        )

        for _ in range(4):
            self.client.post(
                '/accounts/verify-login/',
                {'code': 'not-a-code'},
            )
        response = self.client.post(
            '/accounts/verify-login/',
            {'code': 'not-a-code'},
        )

        self.assertRedirects(response, '/accounts/login/')
        self.assertNotIn('_auth_user_id', self.client.session)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    @patch(
        'resources_app.email_auth.send_mail',
        side_effect=OSError('SMTP unavailable'),
    )
    def test_registration_reports_email_failure_without_leaving_account(self, _send_mail):
        response = self.client.post(
            '/register/',
            {
                'username': 'mailfailure',
                'first_name': 'Mail',
                'last_name': 'Failure',
                'email': 'mailfailure@example.com',
                'phone': '08098765432',
                'registration_number': 'HIT-2026-003',
                'password1': 'SafeCoursePass!882',
                'password2': 'SafeCoursePass!882',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'could not send your verification email')
        self.assertFalse(
            get_user_model().objects.filter(username='mailfailure').exists()
        )
        self.assertFalse(
            StudentProfile.objects.filter(
                registration_number='HIT-2026-003',
            ).exists()
        )
        _send_mail.assert_called_once()

    def test_registration_rejects_duplicate_registration_number(self):
        response = self.client.post(
            '/register/',
            {
                'username': 'duplicate',
                'first_name': 'New',
                'last_name': 'Student',
                'email': 'new@example.com',
                'phone': '08098765432',
                'registration_number': self.profile.registration_number,
                'password1': 'SafeCoursePass!882',
                'password2': 'SafeCoursePass!882',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already in use')
        self.assertFalse(get_user_model().objects.filter(username='duplicate').exists())


class SubscriptionAndGoogleAuthTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='member',
            email='member@example.com',
            password='MemberPass!882',
        )
        force_login_verified(self.client, self.user)

    def test_newsletter_signup_is_case_insensitive_and_idempotent(self):
        response = self.client.post(
            '/subscribe/newsletter/',
            {'email': ' Member@Example.com '},
        )
        self.assertRedirects(response, '/')
        response = self.client.post(
            '/subscribe/newsletter/',
            {'email': 'member@example.com'},
        )
        self.assertRedirects(response, '/')
        self.assertEqual(NewsletterSubscription.objects.count(), 1)
        self.assertEqual(
            NewsletterSubscription.objects.get().email,
            'member@example.com',
        )

    def test_invalid_newsletter_email_is_rejected(self):
        response = self.client.post(
            '/subscribe/newsletter/',
            {'email': 'not-an-email'},
        )

        self.assertRedirects(response, '/')
        self.assertEqual(NewsletterSubscription.objects.count(), 0)

    def test_membership_page_shows_monthly_price_and_provider_status(self):
        response = self.client.get('/membership/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '₦5000')
        self.assertContains(response, 'PAYSTACK_PLAN_CODE')
        self.assertContains(response, 'STRIPE_SECRET_KEY')

    def test_subscription_checkout_rejects_unknown_provider(self):
        response = self.client.post(
            '/membership/checkout/',
            {'provider': 'unknown'},
        )

        self.assertRedirects(response, '/membership/')
        self.assertEqual(SubscriptionCheckout.objects.count(), 0)

    @override_settings(STRIPE_SECRET_KEY='')
    def test_stripe_checkout_without_test_key_fails_clearly(self):
        response = self.client.post(
            '/membership/checkout/',
            {'provider': SubscriptionCheckout.Provider.STRIPE},
        )

        self.assertRedirects(response, '/membership/')
        checkout = SubscriptionCheckout.objects.get()
        self.assertEqual(checkout.status, SubscriptionCheckout.Status.FAILED)
        self.assertContains(self.client.get('/membership/'), 'STRIPE_SECRET_KEY')

    @override_settings(PAYSTACK_SECRET_KEY='', PAYSTACK_PLAN_CODE='')
    def test_paystack_checkout_without_configuration_fails_clearly(self):
        response = self.client.post(
            '/membership/checkout/',
            {'provider': SubscriptionCheckout.Provider.PAYSTACK},
        )

        self.assertRedirects(response, '/membership/')
        checkout = SubscriptionCheckout.objects.get()
        self.assertEqual(checkout.status, SubscriptionCheckout.Status.FAILED)
        self.assertContains(self.client.get('/membership/'), 'PAYSTACK_SECRET_KEY')

    @override_settings(STRIPE_SECRET_KEY='sk_test_portal')
    @patch('resources_app.portal_views.create_stripe_checkout')
    def test_stripe_checkout_redirects_to_provider(self, create_checkout):
        create_checkout.return_value = 'https://checkout.stripe.com/test-session'

        response = self.client.post(
            '/membership/checkout/',
            {'provider': SubscriptionCheckout.Provider.STRIPE},
        )

        self.assertRedirects(
            response,
            'https://checkout.stripe.com/test-session',
            fetch_redirect_response=False,
        )
        self.assertEqual(create_checkout.call_count, 1)

    def test_google_sign_in_button_is_only_shown_when_credentials_exist(self):
        response = self.client.get('/accounts/login/')
        self.assertNotContains(response, 'Continue with Google')

        with override_settings(
            SOCIALACCOUNT_PROVIDERS={
                'google': {
                    'APP': {'client_id': 'test-client', 'secret': 'test-secret'}
                }
            }
        ):
            response = self.client.get('/accounts/login/')

        self.assertContains(response, 'Continue with Google')
        self.assertContains(response, '/accounts/google/login/')

    @override_settings(PAYSTACK_SECRET_KEY='sk_test_webhook')
    def test_paystack_webhook_activates_verified_matching_checkout(self):
        checkout = SubscriptionCheckout.objects.create(
            user=self.user,
            provider=SubscriptionCheckout.Provider.PAYSTACK,
            reference='paystack-test-reference',
        )
        payload = json.dumps(
            {
                'event': 'charge.success',
                'data': {
                    'reference': checkout.reference,
                    'status': 'success',
                    'amount': 500_000,
                    'currency': 'NGN',
                    'customer': {
                        'email': self.user.email,
                        'customer_code': 'CUS_test',
                    },
                    'subscription': {'subscription_code': 'SUB_test'},
                },
            }
        ).encode()
        signature = hmac.new(
            b'sk_test_webhook',
            payload,
            hashlib.sha512,
        ).hexdigest()

        response = self.client.post(
            '/webhooks/paystack/',
            data=payload,
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, 200)
        subscription = PortalSubscription.objects.get(user=self.user)
        self.assertEqual(subscription.status, PortalSubscription.Status.ACTIVE)
        self.assertEqual(subscription.provider_subscription_id, 'SUB_test')
        checkout.refresh_from_db()
        self.assertEqual(checkout.status, SubscriptionCheckout.Status.SUCCEEDED)

    @override_settings(PAYSTACK_SECRET_KEY='sk_test_webhook')
    def test_paystack_webhook_rejects_invalid_signature(self):
        response = self.client.post(
            '/webhooks/paystack/',
            data=b'{"event":"charge.success","data":{}}',
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE='invalid',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(PortalSubscription.objects.exists())

    def test_member_sees_active_plan_status(self):
        PortalSubscription.objects.create(
            user=self.user,
            provider=PortalSubscription.Provider.STRIPE,
            status=PortalSubscription.Status.ACTIVE,
        )

        response = self.client.get('/membership/')

        self.assertContains(response, 'You’re subscribed')
        self.assertContains(response, 'Active through Stripe')
