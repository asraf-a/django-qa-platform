from django import forms

from app.models import Question, Tag


class QuestionForm(forms.ModelForm):
    tags = forms.CharField(
        required=False,
        help_text="Separate tags with commas (e.g. python, django, web development)",
        widget=forms.TextInput(
            attrs={
                'class': 'w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm text-gray-900 placeholder-gray-400 transition-colors',
                'placeholder': 'e.g. python, django, web development',
            }
        )
    )

    class Meta:
        model = Question
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(
                attrs={
                    'class': 'w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm text-gray-900 placeholder-gray-400 transition-colors',
                    'placeholder': 'What is your programming question? Be specific.',
                }
            ),
            'description': forms.Textarea(
                attrs={
                    'rows': 8,
                    'class': 'w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm text-gray-900 placeholder-gray-400 transition-colors font-sans',
                    'placeholder': 'Include all the details someone would need to answer your question, such as context, expected behavior, and code snippets.',
                }
            ),
        }

    def save(self, commit=True):
        question = super().save(commit=commit)
        tags_data = self.cleaned_data.get('tags', '')

        tag_objects = []
        if tags_data:
            tag_names = [name.strip() for name in tags_data.split(',') if name.strip()]
            for name in tag_names:
                tag = Tag.objects.filter(name__iexact=name).first()
                if not tag:
                    tag = Tag.objects.create(name=name)
                tag_objects.append(tag)

        if commit:
            question.tags.set(tag_objects)
        else:
            old_save_m2m = self.save_m2m

            def save_m2m():
                old_save_m2m()
                question.tags.set(tag_objects)

            self.save_m2m = save_m2m

        return question
