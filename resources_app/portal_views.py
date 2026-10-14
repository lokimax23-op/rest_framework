import json
import logging
import secrets
import smtplib

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .assignment_forms import (
    AssignmentAnswerForm,
    AssignmentGradeForm,
    CourseAssignmentForm,
)
from .email_auth import (
    send_account_activity_notification,
    send_signup_verification,
)
from .forms import NewsletterSubscriptionForm, StudentRegistrationForm
from .models import (
    AssignmentSubmission,
    Course,
    CourseAssignment,
    Enrollment,
    LearningResource,
    NewsletterSubscription,
    PortalSubscription,
    StudentProfile,
    SubscriptionCheckout,
)
from .payments import (
    activate_subscription,
    create_paystack_checkout,
    create_stripe_checkout,
    external_object_id,
    is_paystack_configured,
    is_stripe_configured,
    paystack_mode,
    set_subscription_status_by_provider_id,
    stripe_mode,
    valid_paystack_signature,
    verify_paystack_transaction,
)

logger = logging.getLogger(__name__)


def portal_home(request):
    context = {
        'courses': (
            Course.objects.select_related('instructor')
            .annotate(learner_count=Count('enrollments'))
            .order_by('-learner_count', 'code')[:6]
        ),
        'course_count': Course.objects.count(),
        'student_count': StudentProfile.objects.count(),
        'resource_count': LearningResource.objects.count(),
        'resources': LearningResource.objects.select_related('author')[:3],
    }
    return render(request, 'portal/home.html', context)


def course_catalog(request):
    search_query = request.GET.get('q', '').strip()
    courses = Course.objects.select_related('instructor').annotate(
        learner_count=Count('enrollments')
    )
    if search_query:
        courses = courses.filter(
            Q(code__icontains=search_query)
            | Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(instructor__first_name__icontains=search_query)
            | Q(instructor__last_name__icontains=search_query)
        )

    if request.GET.get('format') == 'json':
        return JsonResponse(
            {
                'courses': [
                    {
                        'id': course.pk,
                        'code': course.code,
                        'title': course.title,
                        'description': course.description,
                        'duration_weeks': course.duration_weeks,
                        'learner_count': getattr(course, 'learner_count'),
                        'instructor': (
                            course.instructor.get_full_name()
                            or course.instructor.get_username()
                            if course.instructor
                            else 'To be announced'
                        ),
                        'enrollment_url': f'/courses/{course.pk}/enroll/',
                    }
                    for course in courses
                ]
            }
        )

    context = {
        'courses': courses,
        'search_query': search_query,
        'page_title': 'HiiT Course Catalog',
    }
    return render(request, 'portal/course_catalog.html', context)


@login_required
def student_dashboard(request):
    profile = StudentProfile.objects.filter(user=request.user).first()
    if profile is None:
        if request.user.is_staff:
            return redirect('admin:index')
        messages.error(
            request,
            'Your account does not have a student profile. Please contact the branch administrator.',
        )
        return redirect('home')

    enrollments = (
        Enrollment.objects.filter(student=profile)
        .select_related('course', 'course__instructor')
    )
    return render(
        request,
        'portal/dashboard.html',
        {
            'profile': profile,
            'enrollments': enrollments,
            'page_title': 'Student Dashboard',
        },
    )


@login_required
def enroll_course(request, course_id):
    if request.method != 'POST':
        return redirect('course_catalog')
    course = get_object_or_404(Course, pk=course_id)
    profile = StudentProfile.objects.filter(user=request.user).first()
    if profile is None:
        if request.user.is_staff:
            return redirect('admin:index')
        messages.error(
            request,
            'Your account does not have a student profile. Please contact the branch administrator.',
        )
        return redirect('course_catalog')

    _, created = Enrollment.objects.get_or_create(
        student=profile,
        course=course,
        defaults={'status': Enrollment.Status.ACTIVE},
    )
    if created:
        messages.success(request, f'Successfully enrolled in {course.title}!')
    else:
        messages.info(request, f'You are already registered for {course.title}.')
    return redirect('student_dashboard')


def _can_manage_course_assignments(user, course):
    return user.is_staff or course.instructor_id == user.pk


@login_required
def course_assignments(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    can_manage = _can_manage_course_assignments(request.user, course)
    profile = StudentProfile.objects.filter(user=request.user).first()
    is_enrolled = bool(
        profile
        and Enrollment.objects.filter(student=profile, course=course).exists()
    )
    if not can_manage and not is_enrolled:
        raise PermissionDenied

    form = CourseAssignmentForm()
    if request.method == 'POST':
        if not can_manage:
            raise PermissionDenied
        form = CourseAssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.course = course
            assignment.created_by = request.user
            assignment.save()
            messages.success(request, 'Assignment created for this course.')
            return redirect('course_assignments', course_id=course.pk)

    assignments = list(
        CourseAssignment.objects.filter(course=course).prefetch_related(
            'submissions__student__user'
        )
    )
    assignment_rows = []
    for assignment in assignments:
        submissions = list(assignment.submissions.all())
        if can_manage:
            for submission in submissions:
                submission.grade_form = AssignmentGradeForm(instance=submission)
        own_submission = next(
            (
                submission
                for submission in submissions
                if profile and submission.student_id == profile.pk
            ),
            None,
        )
        assignment_rows.append(
            {
                'assignment': assignment,
                'own_submission': own_submission,
                'submissions': submissions if can_manage else [],
                'answer_form': (
                    AssignmentAnswerForm(instance=own_submission)
                    if profile and is_enrolled and not can_manage
                    else None
                ),
            }
        )

    return render(
        request,
        'portal/course_assignments.html',
        {
            'course': course,
            'assignments': assignment_rows,
            'can_manage': can_manage,
            'form': form,
            'page_title': f'{course.code} assignments',
        },
    )


@login_required
@require_POST
def submit_assignment_answer(request, course_id, assignment_id):
    course = get_object_or_404(Course, pk=course_id)
    assignment = get_object_or_404(
        CourseAssignment,
        pk=assignment_id,
        course=course,
    )
    profile = StudentProfile.objects.filter(user=request.user).first()
    if profile is None or not Enrollment.objects.filter(
        student=profile,
        course=course,
    ).exists():
        raise PermissionDenied
    if _can_manage_course_assignments(request.user, course):
        raise PermissionDenied

    submission = AssignmentSubmission.objects.filter(
        assignment=assignment,
        student=profile,
    ).first()
    form = AssignmentAnswerForm(request.POST, instance=submission)
    if not form.is_valid():
        messages.error(request, 'Enter your answer before submitting.')
        return redirect('course_assignments', course_id=course.pk)

    saved_submission = form.save(commit=False)
    saved_submission.assignment = assignment
    saved_submission.student = profile
    saved_submission.status = AssignmentSubmission.Status.SUBMITTED
    saved_submission.grade = None
    saved_submission.feedback = ''
    saved_submission.graded_at = None
    saved_submission.graded_by = None
    saved_submission.save()
    messages.success(request, 'Your assignment answer has been submitted.')
    return redirect('course_assignments', course_id=course.pk)


@login_required
@require_POST
def grade_assignment_submission(
    request,
    course_id,
    assignment_id,
    submission_id,
):
    course = get_object_or_404(Course, pk=course_id)
    if not _can_manage_course_assignments(request.user, course):
        raise PermissionDenied
    assignment = get_object_or_404(
        CourseAssignment,
        pk=assignment_id,
        course=course,
    )
    submission = get_object_or_404(
        AssignmentSubmission,
        pk=submission_id,
        assignment=assignment,
    )
    form = AssignmentGradeForm(request.POST, instance=submission)
    if not form.is_valid():
        messages.error(request, 'Enter a grade from 0 to 100.')
        return redirect('course_assignments', course_id=course.pk)

    graded_submission = form.save(commit=False)
    graded_submission.status = AssignmentSubmission.Status.GRADED
    graded_submission.graded_at = timezone.now()
    graded_submission.graded_by = request.user
    graded_submission.save()
    messages.success(request, 'Grade and feedback saved.')
    return redirect('course_assignments', course_id=course.pk)


def register(request):
    if request.user.is_authenticated:
        return redirect('student_dashboard')
    form = StudentRegistrationForm(
        request.POST if request.method == 'POST' else None,
    )
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        try:
            send_signup_verification(request, user)
        except (OSError, smtplib.SMTPException, ValueError):
            logger.exception('Could not send a student account verification email.')
            user.delete()
            form.add_error(
                None,
                'We could not send your verification email. Please try again later.',
            )
        else:
            send_account_activity_notification(user, 'signup')
            messages.success(
                request,
                'Your account was created. Check your email to verify it before logging in.',
            )
            return redirect('login')
    return render(
        request,
        'portal/register.html',
        {'form': form, 'page_title': 'Create Student Account'},
    )


@login_required
def logout_view(request):
    if request.method != 'POST':
        return redirect('home')
    logout(request)
    messages.success(request, 'You have been signed out.')
    return redirect('home')


@require_POST
def newsletter_subscribe(request):
    form = NewsletterSubscriptionForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Enter a valid email address to subscribe.')
        return redirect('home')

    subscription, created = NewsletterSubscription.objects.get_or_create(
        email=form.cleaned_data['email'].lower(),
        defaults={'is_active': True},
    )
    if not created and not subscription.is_active:
        subscription.is_active = True
        subscription.save(update_fields=['is_active'])
    messages.success(request, 'You are subscribed to HiiT learning updates.')
    return redirect('home')


@login_required
def subscription_manage(request):
    subscription = PortalSubscription.objects.filter(user=request.user).first()
    return render(
        request,
        'portal/subscription.html',
        {
            'subscription': subscription,
            'page_title': 'Membership subscription',
            'paystack_configured': is_paystack_configured(),
            'stripe_configured': is_stripe_configured(),
            'paystack_mode': paystack_mode(),
            'stripe_mode': stripe_mode(),
        },
    )


@login_required
@require_POST
def subscription_checkout(request):
    provider = request.POST.get('provider', '')
    if provider not in {
        SubscriptionCheckout.Provider.PAYSTACK,
        SubscriptionCheckout.Provider.STRIPE,
    }:
        messages.error(request, 'Choose Paystack or Stripe to continue.')
        return redirect('subscription_manage')

    existing = PortalSubscription.objects.filter(
        user=request.user,
        status=PortalSubscription.Status.ACTIVE,
    ).first()
    if existing:
        messages.info(request, 'You already have an active portal membership.')
        return redirect('subscription_manage')

    checkout = SubscriptionCheckout.objects.create(
        user=request.user,
        provider=provider,
        reference=secrets.token_urlsafe(24),
    )
    try:
        if provider == SubscriptionCheckout.Provider.PAYSTACK:
            checkout_url = create_paystack_checkout(request, checkout)
        else:
            checkout_url = create_stripe_checkout(request, checkout)
    except (ValueError, RuntimeError, stripe.StripeError) as exc:
        checkout.status = SubscriptionCheckout.Status.FAILED
        checkout.save(update_fields=['status'])
        messages.error(request, str(exc))
        return redirect('subscription_manage')

    return redirect(checkout_url)


@login_required
def paystack_return(request):
    reference = request.GET.get('reference', '').strip()
    checkout = SubscriptionCheckout.objects.filter(
        reference=reference,
        user=request.user,
        provider=SubscriptionCheckout.Provider.PAYSTACK,
    ).first()
    if checkout is None:
        messages.error(request, 'We could not find that Paystack checkout.')
        return redirect('subscription_manage')

    try:
        transaction = verify_paystack_transaction(reference)
    except (ValueError, RuntimeError) as exc:
        messages.error(request, str(exc))
        return redirect('subscription_manage')

    customer_data = transaction.get('customer')
    if not isinstance(customer_data, dict):
        customer_data = {}
    paid_correctly = (
        transaction.get('reference') == checkout.reference
        and transaction.get('status') == 'success'
        and transaction.get('amount') == settings.PORTAL_SUBSCRIPTION_AMOUNT_KOBO
        and str(transaction.get('currency', '')).upper() == 'NGN'
        and str(customer_data.get('email', '')).lower() == request.user.email.lower()
    )
    if not paid_correctly:
        checkout.status = SubscriptionCheckout.Status.FAILED
        checkout.save(update_fields=['status'])
        messages.error(request, 'Payment is not confirmed for this account.')
        return redirect('subscription_manage')

    subscription_data = transaction.get('subscription')
    activate_subscription(
        request.user,
        PortalSubscription.Provider.PAYSTACK,
        subscription_id=(
            subscription_data.get('subscription_code', '')
            if isinstance(subscription_data, dict)
            else ''
        ),
        customer_id=(
            customer_data.get('customer_code', '')
            if isinstance(customer_data, dict)
            else ''
        ),
    )
    checkout.status = SubscriptionCheckout.Status.SUCCEEDED
    checkout.save(update_fields=['status'])
    messages.success(request, 'Your HiiT monthly membership is active.')
    return redirect('subscription_manage')


@login_required
def stripe_return(request):
    session_id = request.GET.get('session_id', '').strip()
    if not is_stripe_configured() or not session_id:
        messages.error(request, 'The Stripe checkout could not be verified.')
        return redirect('subscription_manage')

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.StripeError:
        messages.error(request, 'Stripe could not verify this checkout session.')
        return redirect('subscription_manage')

    metadata = session.metadata or {}
    checkout = SubscriptionCheckout.objects.filter(
        pk=metadata.get('checkout_id'),
        provider_checkout_id=session.id,
        user=request.user,
        provider=SubscriptionCheckout.Provider.STRIPE,
    ).first()
    if checkout is None:
        messages.error(request, 'This Stripe checkout does not belong to your account.')
        return redirect('subscription_manage')

    if (
        session.status != 'complete'
        or session.payment_status not in {'paid', 'no_payment_required'}
        or session.amount_total != settings.PORTAL_SUBSCRIPTION_AMOUNT_KOBO
        or session.currency != 'ngn'
    ):
        messages.info(request, 'Payment is still being confirmed by Stripe.')
        return redirect('subscription_manage')

    activate_subscription(
        request.user,
        PortalSubscription.Provider.STRIPE,
        subscription_id=external_object_id(session.subscription),
        customer_id=external_object_id(session.customer),
    )
    checkout.status = SubscriptionCheckout.Status.SUCCEEDED
    checkout.save(update_fields=['status'])
    messages.success(request, 'Your HiiT monthly membership is active.')
    return redirect('subscription_manage')


@csrf_exempt
@require_POST
def paystack_webhook(request):
    if not valid_paystack_signature(request):
        return JsonResponse({'detail': 'Invalid Paystack signature.'}, status=400)
    try:
        event = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Invalid JSON body.'}, status=400)

    if event.get('event') == 'charge.success':
        data = event.get('data', {})
        if not isinstance(data, dict):
            return JsonResponse({'detail': 'Invalid Paystack event data.'}, status=400)
        checkout = SubscriptionCheckout.objects.filter(
            reference=data.get('reference'),
            provider=SubscriptionCheckout.Provider.PAYSTACK,
        ).select_related('user').first()
        customer = data.get('customer', {})
        if not isinstance(customer, dict):
            customer = {}
        if checkout and (
            data.get('status') == 'success'
            and data.get('amount') == settings.PORTAL_SUBSCRIPTION_AMOUNT_KOBO
            and str(data.get('currency', '')).upper() == 'NGN'
            and str(customer.get('email', '')).lower()
            == checkout.user.email.lower()
        ):
            subscription_data = data.get('subscription')
            activate_subscription(
                checkout.user,
                PortalSubscription.Provider.PAYSTACK,
                subscription_id=(
                    subscription_data.get('subscription_code', '')
                    if isinstance(subscription_data, dict)
                    else ''
                ),
                customer_id=customer.get('customer_code', ''),
            )
            checkout.status = SubscriptionCheckout.Status.SUCCEEDED
            checkout.save(update_fields=['status'])
    elif event.get('event') in {'invoice.payment_failed', 'invoice.payment_success'}:
        data = event.get('data', {})
        if not isinstance(data, dict):
            return JsonResponse({'detail': 'Invalid Paystack event data.'}, status=400)
        subscription_data = data.get('subscription', {})
        subscription_code = (
            subscription_data.get('subscription_code', '')
            if isinstance(subscription_data, dict)
            else ''
        )
        status = (
            PortalSubscription.Status.PAST_DUE
            if event['event'] == 'invoice.payment_failed'
            else PortalSubscription.Status.ACTIVE
        )
        set_subscription_status_by_provider_id(
            PortalSubscription.Provider.PAYSTACK,
            subscription_code,
            status,
        )
    elif event.get('event') == 'subscription.disable':
        data = event.get('data', {})
        subscription_code = data.get('subscription_code', '')
        set_subscription_status_by_provider_id(
            PortalSubscription.Provider.PAYSTACK,
            subscription_code,
            PortalSubscription.Status.CANCELED,
        )
    return HttpResponse(status=200)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    if not settings.STRIPE_WEBHOOK_SECRET:
        return JsonResponse(
            {'detail': 'Stripe webhook secret is not configured.'},
            status=503,
        )
    try:
        event = stripe.Webhook.construct_event(
            request.body,
            request.headers.get('stripe-signature', ''),
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe.SignatureVerificationError):
        return JsonResponse({'detail': 'Invalid Stripe webhook signature.'}, status=400)

    if event.type == 'checkout.session.completed':
        session = event.data.object
        metadata = session.get('metadata') or {}
        checkout = SubscriptionCheckout.objects.filter(
            pk=metadata.get('checkout_id'),
            provider_checkout_id=session.get('id'),
            provider=SubscriptionCheckout.Provider.STRIPE,
        ).select_related('user').first()
        if checkout and (
            session.get('payment_status') in {'paid', 'no_payment_required'}
            and session.get('amount_total') == settings.PORTAL_SUBSCRIPTION_AMOUNT_KOBO
            and session.get('currency') == 'ngn'
        ):
            activate_subscription(
                checkout.user,
                PortalSubscription.Provider.STRIPE,
                subscription_id=external_object_id(session.get('subscription')),
                customer_id=external_object_id(session.get('customer')),
            )
            checkout.status = SubscriptionCheckout.Status.SUCCEEDED
            checkout.save(update_fields=['status'])
    elif event.type == 'invoice.payment_failed':
        invoice = event.data.object
        subscription_id = invoice.get('subscription')
        PortalSubscription.objects.filter(
            provider=PortalSubscription.Provider.STRIPE,
            provider_subscription_id=str(subscription_id or ''),
        ).update(status=PortalSubscription.Status.PAST_DUE)
    elif event.type == 'customer.subscription.deleted':
        provider_subscription = event.data.object
        PortalSubscription.objects.filter(
            provider=PortalSubscription.Provider.STRIPE,
            provider_subscription_id=str(provider_subscription.get('id', '')),
        ).update(status=PortalSubscription.Status.CANCELED)
    elif event.type == 'customer.subscription.updated':
        provider_subscription = event.data.object
        status_map = {
            'active': PortalSubscription.Status.ACTIVE,
            'past_due': PortalSubscription.Status.PAST_DUE,
            'canceled': PortalSubscription.Status.CANCELED,
        }
        raw_status = provider_subscription.get('status')
        subscription_status = (
            status_map.get(raw_status) if isinstance(raw_status, str) else None
        )
        if subscription_status:
            PortalSubscription.objects.filter(
                provider=PortalSubscription.Provider.STRIPE,
                provider_subscription_id=str(provider_subscription.get('id', '')),
            ).update(status=subscription_status)
    return HttpResponse(status=200)
