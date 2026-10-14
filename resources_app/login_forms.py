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
        username = self.cleaned_data.get('username', '').strip()
        if '@' in username:
            matching_usernames = list(
                User.objects.filter(email__iexact=username)
                .values_list('username', flat=True)[:2]
            )
            if len(matching_usernames) == 1:
                username = matching_usernames[0]
        if username:
            exact_match = User.objects.filter(username=username).values_list(
                'username', flat=True
            ).first()
            if exact_match:
                username = exact_match
            else:
                matching_usernames = list(
                    User.objects.filter(username__iexact=username)
                    .values_list('username', flat=True)[:2]
                )
                if len(matching_usernames) == 1:
                    username = matching_usernames[0]
        self.cleaned_data['username'] = username
        return super().clean()
