"""
URL configuration for rest project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from resources_app import auth_views as portal_auth_views
from resources_app import portal_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', portal_views.portal_home, name='home'),
    path('courses/', portal_views.course_catalog, name='course_catalog'),
    path(
        'courses/<int:course_id>/enroll/',
        portal_views.enroll_course,
        name='enroll_course',
    ),
    path('dashboard/', portal_views.student_dashboard, name='student_dashboard'),
    path('register/', portal_views.register, name='register'),
    path(
        'accounts/verify-email/<str:uidb64>/<str:token>/',
        portal_auth_views.verify_email,
        name='verify_email',
    ),
    path(
        'accounts/verify-login/',
        portal_auth_views.verify_login_email,
        name='verify_login_email',
    ),
    path(
        'subscribe/newsletter/',
        portal_views.newsletter_subscribe,
        name='newsletter_subscribe',
    ),
    path(
        'membership/',
        portal_views.subscription_manage,
        name='subscription_manage',
    ),
    path(
        'membership/checkout/',
        portal_views.subscription_checkout,
        name='subscription_checkout',
    ),
    path(
        'membership/paystack/return/',
        portal_views.paystack_return,
        name='paystack_return',
    ),
    path(
        'membership/stripe/return/',
        portal_views.stripe_return,
        name='stripe_return',
    ),
    path(
        'webhooks/paystack/',
        portal_views.paystack_webhook,
        name='paystack_webhook',
    ),
    path(
        'webhooks/stripe/',
        portal_views.stripe_webhook,
        name='stripe_webhook',
    ),
    path(
        'accounts/login/',
        auth_views.LoginView.as_view(template_name='portal/login.html'),
        name='login',
    ),
    path('accounts/logout/', portal_views.logout_view, name='logout'),
    path('accounts/', include('allauth.urls')),
    path('', include('restapp.urls')),
    path('resources/', include('resources_app.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
