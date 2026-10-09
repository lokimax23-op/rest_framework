import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import redirect, render, resolve_url
from django.utils.crypto import constant_time_compare
from django.utils.encoding import force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode
from django.views.decorators.http import require_http_methods

from .email_auth import (
    LOGIN_CODE_MAX_ATTEMPTS,
    LOGIN_CODE_MAX_SENDS,
    LOGIN_CODE_RESEND_COOLDOWN,
    _login_code_digest,
    issue_login_code,
    send_account_activity_notification,
)

User = get_user_model()


def verify_email(request, uidb64, token):
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, 'This email verification link is invalid or has expired.')
        return redirect('login')

    if not user.is_active:
        user.is_active = True
        user.save(update_fields=['is_active'])
        messages.success(request, 'Your email is verified. You can now log in securely.')
    else:
        messages.info(request, 'Your email is already verified. You can log in.')
    return redirect('login')


@require_http_methods(['GET', 'POST'])
def verify_login_email(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if not request.session.get('email_2fa_pending'):
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == 'POST':
        if request.POST.get('action') == 'resend':
            sent_at = request.session.get('email_2fa_sent_at', 0)
            send_count = request.session.get('email_2fa_send_count', 0)
            if send_count >= LOGIN_CODE_MAX_SENDS:
                messages.error(
                    request,
                    'You have reached the code resend limit. Sign in again to retry.',
                )
            elif time.time() - sent_at < LOGIN_CODE_RESEND_COOLDOWN:
                messages.error(request, 'Please wait before requesting another code.')
            else:
                request.session['email_2fa_send_count'] = send_count + 1
                if issue_login_code(request, request.user):
                    request.session['email_2fa_attempts'] = 0
                    messages.success(request, 'A new verification code has been sent.')
                else:
                    messages.error(
                        request,
                        request.session.get(
                            'email_2fa_delivery_error',
                            'We could not send your verification email.',
                        ),
                    )
        else:
            code = request.POST.get('code', '').strip()
            expires_at = request.session.get('email_2fa_expires_at', 0)
            code_hash = request.session.get('email_2fa_code_hash', '')
            if time.time() > expires_at:
                messages.error(request, 'That code has expired. Request a new code.')
            elif not code_hash or not constant_time_compare(
                code_hash,
                _login_code_digest(code),
            ):
                attempts = request.session.get('email_2fa_attempts', 0) + 1
                request.session['email_2fa_attempts'] = attempts
                if attempts >= LOGIN_CODE_MAX_ATTEMPTS:
                    logout(request)
                    messages.error(request, 'Too many incorrect codes. Please sign in again.')
                    return redirect('login')
                messages.error(request, 'That verification code is incorrect.')
            else:
                request.session['email_2fa_pending'] = False
                send_account_activity_notification(request.user, 'login')
                next_url = request.session.pop('email_2fa_next_url', '')
                if next_url and url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(next_url)
                return redirect(resolve_url(settings.LOGIN_REDIRECT_URL))

    return render(
        request,
        'portal/verify_login_email.html',
        {
            'page_title': 'Verify your login',
            'delivery_error': request.session.get('email_2fa_delivery_error', ''),
        },
    )
