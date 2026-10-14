from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UsernameField

User = get_user_model()


class StudentAuthenticationForm(AuthenticationForm):
    username = UsernameField(
        label='Username or email',
        widget=forms.TextInput(
            attrs={'autofocus': True, 'autocomplete': 'username'}
        ),
    )

    def clean(self):
        username = self.cleaned_data.get('username', '')
        if '@' in username:
            matching_usernames = list(
                User.objects.filter(email__iexact=username)
                .values_list('username', flat=True)[:2]
            )
            if len(matching_usernames) == 1:
                self.cleaned_data['username'] = matching_usernames[0]
        return super().clean()
