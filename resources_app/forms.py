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
    gender = forms.ChoiceField(choices=StudentProfile.Gender.choices)
    profile_picture = forms.ImageField(required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'phone',
            'gender',
        )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                'An account with this username already exists. Please log in instead.'
            )
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'An account with this email already exists. Please log in or reset your password.'
            )
        return email

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
                gender=self.cleaned_data['gender'],
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
    gender = forms.ChoiceField(choices=StudentProfile.Gender.choices)

    @transaction.atomic
    def custom_signup(self, request, user):
        _ = request
        StudentProfile.objects.create(
            user=user,
            phone=self.cleaned_data['phone'],
            gender=self.cleaned_data['gender'],
        )
