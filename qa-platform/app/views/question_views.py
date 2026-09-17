from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from app.forms import AnswerCommentForm, AnswerForm, QuestionCommentForm, QuestionForm
from app.models import Answer, Comment, Question, Vote
from .mixins import AuthorRequiredMixin


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
            vote = self.object.votes.filter(user=self.request.user).first()
            if vote:
                user_vote = vote.value
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


class QuestionVoteView(LoginRequiredMixin, SingleObjectMixin, View):
    model = Question

    def get_vote_value(self, request):
        try:
            value = int(request.POST.get('value', 0))
            if value in (Vote.UPVOTE, Vote.DOWNVOTE):
                return value
        except (ValueError, TypeError):
            pass
        return None

    def apply_vote(self, user, question, value):
        content_type = ContentType.objects.get_for_model(Question)
        vote = Vote.objects.filter(
            user=user,
            content_type=content_type,
            object_id=question.pk
        ).first()

        if vote:
            if vote.value == value:
                vote.delete()
            else:
                vote.value = value
                vote.save(update_fields=['value', 'updated_at'])
        else:
            Vote.objects.create(
                user=user,
                content_type=content_type,
                object_id=question.pk,
                value=value
            )

    def post(self, request, *args, **kwargs):
        question = self.get_object()
        vote_value = self.get_vote_value(request)
        if vote_value is not None:
            self.apply_vote(request.user, question, vote_value)
        return redirect('app:question_detail', pk=question.pk)

    def get(self, request, *args, **kwargs):
        question = self.get_object()
        return redirect('app:question_detail', pk=question.pk)
