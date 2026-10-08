from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction

from allauth.socialaccount.forms import SignupForm as SocialSignupForm

from .models import StudentProfile

User = get_user_model()


class StudentRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=15)
    registration_number = forms.CharField(max_length=20)
    profile_picture = forms.ImageField(required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'phone',
            'registration_number',
        )

    def clean_registration_number(self):
        registration_number = self.cleaned_data['registration_number']
        if StudentProfile.objects.filter(
            registration_number=registration_number
        ).exists():
            raise forms.ValidationError('This registration number is already in use.')
        return registration_number

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = False
        if commit:
            user.save()
            self.save_m2m()
            StudentProfile.objects.create(
                user=user,
                phone=self.cleaned_data['phone'],
                registration_number=self.cleaned_data['registration_number'],
                profile_picture=(
                    self.cleaned_data.get('profile_picture')
                    or 'profiles/default.png'
                ),
            )
        return user


class NewsletterSubscriptionForm(forms.Form):
    email = forms.EmailField()


class HiiTSocialSignupForm(SocialSignupForm):
    phone = forms.CharField(max_length=15)
    registration_number = forms.CharField(max_length=20)

    def clean_registration_number(self):
        registration_number = self.cleaned_data['registration_number']
        if StudentProfile.objects.filter(
            registration_number=registration_number
        ).exists():
            raise forms.ValidationError('This registration number is already in use.')
        return registration_number

    @transaction.atomic
    def custom_signup(self, request, user):
        _ = request
        StudentProfile.objects.create(
            user=user,
            phone=self.cleaned_data['phone'],
            registration_number=self.cleaned_data['registration_number'],
        )
