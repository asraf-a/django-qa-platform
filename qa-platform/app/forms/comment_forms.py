from django import forms

from app.models import Comment


class BaseCommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content', 'parent']
        widgets = {
            'parent': forms.HiddenInput(),
        }

    def clean_content(self):
        content = self.cleaned_data.get('content', '').strip()
        if not content:
            raise forms.ValidationError("Comment content cannot be empty.")
        return content


class QuestionCommentForm(BaseCommentForm):
    pass


class AnswerCommentForm(BaseCommentForm):
    pass


class CommentEditForm(BaseCommentForm):
    class Meta(BaseCommentForm.Meta):
        fields = ['content']
        widgets = {}
