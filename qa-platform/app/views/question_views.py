from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from app.forms import AnswerCommentForm, AnswerForm, QuestionCommentForm, QuestionForm
from app.models import Answer, Comment, Question
from .mixins import AuthorRequiredMixin, BaseVoteView


class QuestionListView(ListView):
    model = Question
    template_name = 'questions/question_list.html'
    context_object_name = 'questions'
    paginate_by = 10

    def get_queryset(self):
        return Question.objects.select_related('author').prefetch_related('tags', 'answers', 'votes').all()


class QuestionDetailView(DetailView):
    model = Question
    template_name = 'questions/question_detail.html'
    context_object_name = 'question'

    def get_queryset(self):
        return Question.objects.select_related('author').prefetch_related(
            'tags',
            'votes',
            Prefetch(
                'comments',
                queryset=Comment.objects.select_related('author').prefetch_related('replies__author')
            ),
            Prefetch(
                'answers',
                queryset=Answer.objects.select_related('author').prefetch_related(
                    'votes',
                    Prefetch(
                        'comments',
                        queryset=Comment.objects.select_related('author').prefetch_related('replies__author')
                    )
                )
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'answer_form' not in context:
            context['answer_form'] = AnswerForm()
        if 'comment_form' not in context:
            context['comment_form'] = QuestionCommentForm()
        if 'answer_comment_form' not in context:
            context['answer_comment_form'] = AnswerCommentForm()
        user_vote = None
        if self.request.user.is_authenticated:
            user_id = self.request.user.id
            user_vote = next(
                (v.value for v in self.object.votes.all() if v.user_id == user_id),
                None
            )
            for answer in self.object.answers.all():
                answer.user_vote = next(
                    (v.value for v in answer.votes.all() if v.user_id == user_id),
                    None
                )
        context['user_vote'] = user_vote
        return context



class QuestionCreateView(LoginRequiredMixin, CreateView):
    model = Question
    form_class = QuestionForm
    template_name = 'questions/question_form.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('app:question_detail', kwargs={'pk': self.object.pk})


class QuestionUpdateView(LoginRequiredMixin, AuthorRequiredMixin, UpdateView):
    model = Question
    form_class = QuestionForm
    template_name = 'questions/question_edit.html'
    context_object_name = 'question'

    def get_success_url(self):
        return reverse('app:question_detail', kwargs={'pk': self.object.pk})


class QuestionDeleteView(LoginRequiredMixin, AuthorRequiredMixin, DeleteView):
    model = Question
    template_name = 'questions/question_confirm_delete.html'
    context_object_name = 'question'
    success_url = reverse_lazy('app:question_list')


class QuestionVoteView(BaseVoteView):
    model = Question

    def _get_redirect_url(self, question):
        return reverse('app:question_detail', kwargs={'pk': question.pk})

