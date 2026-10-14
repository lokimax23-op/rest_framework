from django import forms

from .models import AssignmentSubmission, CourseAssignment


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


class AssignmentAnswerForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ('answer',)
        widgets = {
            'answer': forms.Textarea(
                attrs={
                    'rows': 8,
                    'placeholder': 'Write your answer here...',
                }
            ),
        }


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
