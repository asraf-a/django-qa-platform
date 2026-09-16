from django import forms

from app.models import Answer


class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ['content']

    def clean_content(self):
        content = self.cleaned_data.get('content', '').strip()
        if not content:
            raise forms.ValidationError("Answer content cannot be empty.")
        return content
