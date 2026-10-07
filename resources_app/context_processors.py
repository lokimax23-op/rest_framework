from django.conf import settings


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
        'paystack_configured': bool(
            settings.PAYSTACK_SECRET_KEY and settings.PAYSTACK_PLAN_CODE
        ),
        'stripe_configured': bool(settings.STRIPE_SECRET_KEY),
    }
