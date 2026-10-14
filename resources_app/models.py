from django.conf import settings
from django.db import models


ASSIGNMENT_ATTACHMENT_MAX_FILE_BYTES = 4 * 1024 * 1024
ASSIGNMENT_ATTACHMENT_MAX_FILES = 5
ASSIGNMENT_ATTACHMENT_MAX_TOTAL_BYTES = 4 * 1024 * 1024


class StudentProfile(models.Model):
    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        NON_BINARY = 'non_binary', 'Non-binary'
        PREFER_NOT_TO_SAY = 'prefer_not_to_say', 'Prefer not to say'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    phone = models.CharField(max_length=15)
    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        db_default=Gender.PREFER_NOT_TO_SAY,
    )
    legacy_registration_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        default=None,
        db_column='registration_number',
    )
    profile_picture = models.ImageField(
        upload_to='profiles/',
        default='profiles/default.png',
        blank=True,
    )

    def __str__(self):
        return self.user.get_full_name() or self.user.get_username()


class Course(models.Model):
    code = models.CharField(max_length=10, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='courses_taught',
    )
    duration_weeks = models.PositiveIntegerField(default=8)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.title}'


class Enrollment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACTIVE = 'ACTIVE', 'Active'
        COMPLETED = 'COMPLETED', 'Completed'

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='enrollments',
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments',
    )
    enrollment_date = models.DateField(auto_now_add=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'course'],
                name='unique_student_course_enrollment',
            ),
        ]
        ordering = ['-enrollment_date', 'course__code']

    def __str__(self):
        return f'{self.student.user.get_username()} enrolled in {self.course.code}'


class CourseAssignment(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    title = models.CharField(max_length=200)
    instructions = models.TextField()
    due_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_course_assignments',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', '-created_at']

    def __str__(self):
        return f'{self.course.code}: {self.title}'


class AssignmentSubmission(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        GRADED = 'graded', 'Graded'

    assignment = models.ForeignKey(
        CourseAssignment,
        on_delete=models.CASCADE,
        related_name='submissions',
    )
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='assignment_submissions',
    )
    answer = models.TextField()
    submitted_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    grade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    feedback = models.TextField(blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graded_assignment_submissions',
    )

    class Meta:
        ordering = ['-submitted_at']
        constraints = [
            models.UniqueConstraint(
                fields=['assignment', 'student'],
                name='unique_assignment_student_submission',
            ),
        ]

    def __str__(self):
        return f'{self.student.user.get_username()}: {self.assignment.title}'


class AssignmentSubmissionAttachment(models.Model):
    submission = models.ForeignKey(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        related_name='attachments',
    )
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    file_data = models.BinaryField(
        max_length=ASSIGNMENT_ATTACHMENT_MAX_FILE_BYTES,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at', 'pk']

    def __str__(self):
        return self.file_name


class LearningResource(models.Model):
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    description = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='resources',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class NewsletterSubscription(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.email


class SubscriptionCheckout(models.Model):
    class Provider(models.TextChoices):
        PAYSTACK = 'paystack', 'Paystack'
        STRIPE = 'stripe', 'Stripe'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCEEDED = 'succeeded', 'Succeeded'
        FAILED = 'failed', 'Failed'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription_checkouts',
    )
    provider = models.CharField(max_length=10, choices=Provider.choices)
    reference = models.CharField(max_length=255, unique=True)
    provider_checkout_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.provider}: {self.reference}'


class PortalSubscription(models.Model):
    class Provider(models.TextChoices):
        PAYSTACK = 'paystack', 'Paystack'
        STRIPE = 'stripe', 'Stripe'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        PAST_DUE = 'past_due', 'Past due'
        CANCELED = 'canceled', 'Canceled'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='portal_subscription',
    )
    provider = models.CharField(max_length=10, choices=Provider.choices)
    provider_customer_id = models.CharField(max_length=255, blank=True)
    provider_subscription_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    current_period_end = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.get_username()} - {self.status_label}'

    @property
    def status_label(self):
        return self.Status(self.status).label
