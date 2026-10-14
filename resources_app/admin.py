from django.contrib import admin

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


class AssignmentSubmissionInline(admin.TabularInline):
    model = AssignmentSubmission
    extra = 0
    fields = ('student', 'status', 'grade', 'feedback', 'submitted_at')
    readonly_fields = ('student', 'submitted_at')


@admin.register(CourseAssignment)
class CourseAssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'due_date', 'created_by', 'created_at')
    list_filter = ('course', 'due_date')
    search_fields = ('title', 'instructions', 'course__code', 'course__title')
    inlines = (AssignmentSubmissionInline,)


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'student', 'status', 'grade', 'submitted_at')
    list_filter = ('status', 'assignment__course', 'submitted_at')
    search_fields = (
        'assignment__title',
        'student__user__username',
        'student__user__email',
        'answer',
        'feedback',
    )
    readonly_fields = ('submitted_at', 'graded_at')


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'gender', 'phone')
    list_filter = ('gender',)
    search_fields = ('user__username', 'user__email')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'instructor', 'duration_weeks')
    list_filter = ('duration_weeks',)
    search_fields = ('code', 'title', 'description', 'instructor__username')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'enrollment_date', 'status')
    list_filter = ('status', 'enrollment_date')
    search_fields = (
        'student__user__username',
        'student__user__email',
        'course__code',
        'course__title',
    )


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
