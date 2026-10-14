from django.conf import settings

from .payments import (
    is_paystack_configured,
    is_stripe_configured,
    paystack_mode,
    stripe_mode,
)


def portal_context(request):
    _ = request
    return {
        'google_auth_enabled': bool(
            settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['client_id']
            and settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['secret']
        ),
        'subscription_price_ngn': (
            settings.PORTAL_SUBSCRIPTION_AMOUNT_KOBO // 100
        ),
        'paystack_configured': is_paystack_configured(),
        'stripe_configured': is_stripe_configured(),
        'paystack_mode': paystack_mode(),
        'stripe_mode': stripe_mode(),
    }
