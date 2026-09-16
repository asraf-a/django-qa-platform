from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, UpdateView

from app.forms import AnswerForm
from app.models import Answer, Question
from .mixins import AuthorRequiredMixin


class AnswerCreateView(LoginRequiredMixin, CreateView):
    model = Answer
    form_class = AnswerForm
    template_name = 'questions/question_detail.html'

    def get_question(self):
        return get_object_or_404(
            Question.objects.select_related('author').prefetch_related(
                'tags',
                'votes',
                Prefetch(
                    'answers',
                    queryset=Answer.objects.select_related('author').prefetch_related('votes')
                )
            ),
            pk=self.kwargs['pk']
        )

    def get(self, request, *args, **kwargs):
        return redirect('app:question_detail', pk=self.kwargs['pk'])

    def form_valid(self, form):
        form.instance.question = get_object_or_404(Question, pk=self.kwargs['pk'])
        form.instance.author = self.request.user
        return super().form_valid(form)

    def form_invalid(self, form):
        question = self.get_question()
        return self.render_to_response(
            self.get_context_data(question=question, answer_form=form)
        )

    def get_success_url(self):
        return reverse('app:question_detail', kwargs={'pk': self.kwargs['pk']})


class AnswerUpdateView(LoginRequiredMixin, AuthorRequiredMixin, UpdateView):
    model = Answer
    form_class = AnswerForm
    template_name = 'answers/answer_edit.html'
    context_object_name = 'answer'

    def get_queryset(self):
        return Answer.objects.select_related('question', 'author')

    def get_success_url(self):
        return reverse('app:question_detail', kwargs={'pk': self.object.question.pk})


class AnswerDeleteView(LoginRequiredMixin, AuthorRequiredMixin, DeleteView):
    model = Answer
    template_name = 'answers/answer_confirm_delete.html'
    context_object_name = 'answer'

    def get_queryset(self):
        return Answer.objects.select_related('question', 'author')

    def get_success_url(self):
        return reverse('app:question_detail', kwargs={'pk': self.object.question_id})
