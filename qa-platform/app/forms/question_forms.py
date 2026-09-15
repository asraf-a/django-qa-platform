from django import forms

from app.models import Question, Tag


class QuestionForm(forms.ModelForm):
    tags = forms.CharField(
        required=False,
        help_text="Separate tags with commas (e.g. python, django, web development)",
    )

    class Meta:
        model = Question
        fields = ['title', 'description']

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
