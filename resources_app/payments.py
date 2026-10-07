import hashlib
import hmac
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import stripe
from django.conf import settings
from django.urls import reverse

from .models import PortalSubscription


def is_paystack_configured():
    return bool(
        settings.PAYSTACK_SECRET_KEY.startswith('sk_test_')
        and settings.PAYSTACK_PLAN_CODE
    )


def is_stripe_configured():
    return settings.STRIPE_SECRET_KEY.startswith('sk_test_')


def external_object_id(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        object_id = value.get('id')
        return object_id if isinstance(object_id, str) else ''
    return ''


def create_paystack_checkout(request, checkout) -> str:
    if not is_paystack_configured():
        raise ValueError(
            'Paystack test mode requires PAYSTACK_SECRET_KEY (sk_test_...) and '
            'PAYSTACK_PLAN_CODE in the environment.'
        )

    payload = json.dumps(
        {
            'email': checkout.user.email,
            'reference': checkout.reference,
            'plan': settings.PAYSTACK_PLAN_CODE,
            'callback_url': request.build_absolute_uri(
                reverse('paystack_return')
            ),
            'metadata': {
                'checkout_id': checkout.pk,
                'user_id': checkout.user_id,
            },
        }
    ).encode()
    api_request = Request(
        'https://api.paystack.co/transaction/initialize',
        data=payload,
        headers={
            'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urlopen(api_request, timeout=15) as response:
            result = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError('Paystack checkout could not be started.') from exc

    if not result.get('status') or not result.get('data', {}).get('authorization_url'):
        raise RuntimeError('Paystack did not return a checkout link.')

    checkout.provider_checkout_id = result['data'].get('access_code', '')
    checkout.save(update_fields=['provider_checkout_id'])
    return result['data']['authorization_url']


def verify_paystack_transaction(reference):
    if not settings.PAYSTACK_SECRET_KEY.startswith('sk_test_'):
        raise ValueError('Paystack test secret key is not configured.')

    api_request = Request(
        f'https://api.paystack.co/transaction/verify/{quote(reference, safe="")}',
        headers={'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'},
    )
    try:
        with urlopen(api_request, timeout=15) as response:
            result = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError('Paystack payment could not be verified.') from exc

    if not result.get('status') or not isinstance(result.get('data'), dict):
        raise RuntimeError('Paystack returned an invalid verification response.')
    return result['data']


def valid_paystack_signature(request):
    secret = settings.PAYSTACK_SECRET_KEY
    if not secret.startswith('sk_test_'):
        return False
    expected = hmac.new(
        secret.encode(),
        request.body,
        hashlib.sha512,
    ).hexdigest()
    received = request.headers.get('x-paystack-signature', '')
    return bool(received) and hmac.compare_digest(expected, received)


def create_stripe_checkout(request, checkout) -> str:
    if not is_stripe_configured():
        raise ValueError(
            'Stripe test mode requires STRIPE_SECRET_KEY (sk_test_...) '
            'in the environment.'
        )

    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.create(
        mode='subscription',
        line_items=[
            {
                'price_data': {
                    'currency': 'ngn',
                    'product_data': {'name': 'HiiT Learning Hub Monthly'},
                    'unit_amount': settings.PORTAL_SUBSCRIPTION_AMOUNT_KOBO,
                    'recurring': {'interval': 'month'},
                },
                'quantity': 1,
            }
        ],
        customer_email=checkout.user.email,
        client_reference_id=str(checkout.user_id),
        metadata={
            'checkout_id': str(checkout.pk),
            'user_id': str(checkout.user_id),
        },
        subscription_data={
            'metadata': {
                'checkout_id': str(checkout.pk),
                'user_id': str(checkout.user_id),
            }
        },
        success_url=request.build_absolute_uri(
            reverse('stripe_return')
        ) + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=request.build_absolute_uri(reverse('subscription_manage')),
    )
    checkout.provider_checkout_id = session.id
    checkout.save(update_fields=['provider_checkout_id'])
    if not session.url:
        raise RuntimeError('Stripe did not return a checkout link.')
    return session.url


def activate_subscription(user, provider, subscription_id='', customer_id=''):
    return PortalSubscription.objects.update_or_create(
        user=user,
        defaults={
            'provider': provider,
            'provider_subscription_id': str(subscription_id or ''),
            'provider_customer_id': str(customer_id or ''),
            'status': PortalSubscription.Status.ACTIVE,
        },
    )[0]


def cancel_subscription(user):
    return PortalSubscription.objects.filter(user=user).update(
        status=PortalSubscription.Status.CANCELED
    )


def set_subscription_status_by_provider_id(provider, subscription_id, status):
    if not subscription_id:
        return 0
    return PortalSubscription.objects.filter(
        provider=provider,
        provider_subscription_id=str(subscription_id),
    ).update(status=status)
