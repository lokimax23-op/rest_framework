import logging
import secrets
import smtplib
import time

from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.dispatch import receiver
from django.urls import reverse
from django.utils.crypto import salted_hmac
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)

LOGIN_CODE_LIFETIME = 600
LOGIN_CODE_MAX_ATTEMPTS = 5
LOGIN_CODE_RESEND_COOLDOWN = 60
LOGIN_CODE_MAX_SENDS = 3


def send_signup_verification(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verification_url = request.build_absolute_uri(
        reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
    )
    sent = send_mail(
        'Verify your HiiT student account',
        (
            f'Hello {user.get_username()},\n\n'
            'Verify your email address to activate your HiiT student account:\n'
            f'{verification_url}\n\n'
            'If you did not create this account, you can ignore this email.'
        ),
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    if sent != 1:
        raise OSError('The verification email was not accepted for delivery.')


def _login_code_digest(code):
    return salted_hmac(
        'resources_app.email_two_factor',
        code,
        secret=settings.SECRET_KEY,
    ).hexdigest()


def issue_login_code(request, user):
    if not user.email:
        request.session['email_2fa_code_hash'] = ''
        request.session['email_2fa_delivery_error'] = (
            'Your account has no email address. Contact the administrator.'
        )
        return False

    code = f'{secrets.randbelow(1_000_000):06d}'
    request.session['email_2fa_code_hash'] = _login_code_digest(code)
    request.session['email_2fa_expires_at'] = int(time.time()) + LOGIN_CODE_LIFETIME
    request.session['email_2fa_sent_at'] = int(time.time())
    request.session['email_2fa_delivery_error'] = ''
    try:
        sent = send_mail(
            'Your HiiT login verification code',
            (
                f'Your HiiT login verification code is {code}.\n\n'
                'It expires in 10 minutes. If you did not try to sign in, '
                'you can ignore this email.'
            ),
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        if sent != 1:
            raise OSError('The login code email was not accepted for delivery.')
    except (OSError, smtplib.SMTPException, ValueError):
        request.session['email_2fa_code_hash'] = ''
        request.session['email_2fa_delivery_error'] = (
            'We could not send the verification email. Try sending a new code.'
        )
        logger.exception('Could not send a login verification email.')
        return False
    return True


@receiver(user_logged_in, dispatch_uid='resources_app.email_two_factor')
def start_email_two_factor(sender, request, user, **kwargs):
    request.session['email_2fa_pending'] = True
    request.session['email_2fa_attempts'] = 0
    request.session['email_2fa_send_count'] = 1
    request.session.pop('email_2fa_next_url', None)
    issue_login_code(request, user)
