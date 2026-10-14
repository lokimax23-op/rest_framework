from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import get_valid_filename

from .models import (
    ASSIGNMENT_ATTACHMENT_MAX_FILE_BYTES,
    ASSIGNMENT_ATTACHMENT_MAX_FILES,
    ASSIGNMENT_ATTACHMENT_MAX_TOTAL_BYTES,
    CourseAssignment,
)

ALLOWED_ASSIGNMENT_ATTACHMENT_EXTENSIONS = {
    '.csv',
    '.doc',
    '.docx',
    '.jpeg',
    '.jpg',
    '.pdf',
    '.png',
    '.ppt',
    '.pptx',
    '.txt',
    '.xls',
    '.xlsx',
}


class CourseAssignmentForm(forms.ModelForm):
    due_date = forms.DateField(
        required=False,
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
    )

    class Meta:
        model = CourseAssignment
        fields = ('title', 'instructions', 'due_date')
        widgets = {
            'instructions': forms.Textarea(attrs={'rows': 5}),
        }


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []
        if isinstance(data, (list, tuple)):
            return [
                super(MultipleFileField, self).clean(item, initial)
                for item in data
            ]
        return [super().clean(data, initial)]


class AssignmentAnswerForm(forms.Form):
    answer = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'rows': 8,
                'placeholder': 'Write your answer here...',
            }
        ),
    )
    attachments = MultipleFileField(
        required=False,
        widget=MultipleFileInput(
            attrs={
                'multiple': True,
                'accept': ','.join(sorted(ALLOWED_ASSIGNMENT_ATTACHMENT_EXTENSIONS)),
            }
        ),
        help_text=(
            'Attach up to 5 PDF, Office, text, CSV, PNG, or JPEG files. '
            'Each submission is limited to 4 MB total.'
        ),
    )
    replace_attachments = forms.BooleanField(
        required=False,
        label='Replace my existing attached files with the files selected above',
    )

    def clean_attachments(self):
        attachments = self.cleaned_data['attachments']
        if len(attachments) > ASSIGNMENT_ATTACHMENT_MAX_FILES:
            raise ValidationError('Attach no more than 5 files per submission.')

        total_size = 0
        for attachment in attachments:
            extension = Path(
                attachment.name.replace('\\', '/')
            ).suffix.lower()
            if extension not in ALLOWED_ASSIGNMENT_ATTACHMENT_EXTENSIONS:
                raise ValidationError(
                    'Unsupported file type. Use PDF, Office, text, CSV, '
                    'PNG, or JPEG files.'
                )
            if attachment.size > ASSIGNMENT_ATTACHMENT_MAX_FILE_BYTES:
                raise ValidationError(
                    'Each attached file must be 4 MB or smaller.'
                )
            total_size += attachment.size

        if total_size > ASSIGNMENT_ATTACHMENT_MAX_TOTAL_BYTES:
            raise ValidationError(
                'Attached files must total 4 MB or less per submission.'
            )
        return attachments


class AssignmentGradeForm(forms.ModelForm):
    grade = forms.DecimalField(
        min_value=0,
        max_value=100,
        max_digits=5,
        decimal_places=2,
    )

    class Meta:
        model = AssignmentSubmission
        fields = ('grade', 'feedback')
        widgets = {
            'feedback': forms.Textarea(attrs={'rows': 3}),
        }
