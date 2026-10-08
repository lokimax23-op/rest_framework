from django.shortcuts import redirect
from django.urls import reverse


class EmailTwoFactorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.session.get('email_2fa_pending'):
            allowed_paths = (
                reverse('verify_login_email'),
                reverse('logout'),
                '/static/',
            )
            if not any(
                request.path_info == path or request.path_info.startswith(path)
                for path in allowed_paths
            ):
                request.session.setdefault(
                    'email_2fa_next_url',
                    request.get_full_path(),
                )
                return redirect('verify_login_email')
        return self.get_response(request)
