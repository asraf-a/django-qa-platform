from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView

from app.forms import QuestionCommentForm
from app.models import Answer, Comment, Question


class QuestionCommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = QuestionCommentForm
    template_name = 'questions/question_detail.html'

    def get_question(self):
        return get_object_or_404(
            Question.objects.select_related('author').prefetch_related(
                'tags',
                'votes',
                Prefetch(
                    'comments',
                    queryset=Comment.objects.select_related('author').prefetch_related('replies__author')
                ),
                Prefetch(
                    'answers',
                    queryset=Answer.objects.select_related('author').prefetch_related('votes')
                )
            ),
            pk=self.kwargs['pk']
        )

    def get(self, request, *args, **kwargs):
        return redirect('app:question_detail', pk=self.kwargs['pk'])

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.instance.question = get_object_or_404(Question, pk=self.kwargs['pk'])
        form.instance.author = self.request.user
        return form

    def form_valid(self, form):
        form.instance.question = get_object_or_404(Question, pk=self.kwargs['pk'])
        form.instance.author = self.request.user
        return super().form_valid(form)

    def form_invalid(self, form):
        question = self.get_question()
        return self.render_to_response(
            self.get_context_data(question=question, comment_form=form)
        )

    def get_success_url(self):
        return reverse('app:question_detail', kwargs={'pk': self.kwargs['pk']})
