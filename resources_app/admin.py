from django.contrib import admin

from .models import (
    Course,
    Enrollment,
    LearningResource,
    NewsletterSubscription,
    PortalSubscription,
    StudentProfile,
    SubscriptionCheckout,
)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('registration_number', 'user', 'phone')
    search_fields = ('registration_number', 'user__username', 'user__email')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'instructor', 'duration_weeks')
    list_filter = ('duration_weeks',)
    search_fields = ('code', 'title', 'description', 'instructor__username')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'enrollment_date', 'status')
    list_filter = ('status', 'enrollment_date')
    search_fields = ('student__registration_number', 'course__code', 'course__title')


@admin.register(LearningResource)
class LearningResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'description', 'author__username')


@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('email',)


@admin.register(PortalSubscription)
class PortalSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'status', 'current_period_end', 'updated_at')
    list_filter = ('provider', 'status')
    search_fields = ('user__username', 'user__email', 'provider_subscription_id')
    readonly_fields = ('provider_customer_id', 'provider_subscription_id', 'updated_at')


@admin.register(SubscriptionCheckout)
class SubscriptionCheckoutAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'status', 'created_at')
    list_filter = ('provider', 'status', 'created_at')
    search_fields = ('user__username', 'user__email', 'reference')
    readonly_fields = ('reference', 'provider_checkout_id', 'created_at')
