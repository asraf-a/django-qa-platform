from urllib.parse import urlencode

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django_filters.views import FilterView

from app.filters import QuestionFilter
from app.forms import AnswerCommentForm, AnswerForm, QuestionCommentForm, QuestionForm
from app.models import Answer, Comment, Question, Tag, Vote
from .mixins import AuthorRequiredMixin, BaseVoteView, DeleteSuccessMessageMixin


class QuestionListView(FilterView):
    model = Question
    filterset_class = QuestionFilter
    strict = False
    template_name = 'questions/question_list.html'
    context_object_name = 'questions'
    paginate_by = 10

    def _build_url(self, tags=None, sort=None):
        params = {}
        q = self.request.GET.get('q')
        if q:
            params['q'] = q
        if tags:
            params['tag'] = tags
        if sort and sort != 'newest':
            params['sort'] = sort
        return f"?{urlencode(params, doseq=True)}" if params else reverse('app:question_list')

    def get_queryset(self):
        return (
            Question.objects
            .select_related('author')
            .prefetch_related('tags', 'answers', 'votes')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_slugs = self.request.GET.getlist('tag')
        sort = self.filterset.current_sort
        all_tags = list(Tag.objects.all())

        for tag in all_tags:
            tag.is_selected = tag.slug in selected_slugs
            remaining = [s for s in selected_slugs if s != tag.slug] if tag.is_selected else selected_slugs + [tag.slug]
            tag.toggle_url = self._build_url(tags=remaining, sort=sort)

        context['all_tags'] = all_tags
        context['selected_slugs'] = selected_slugs
        context['selected_tags'] = [t for t in all_tags if t.is_selected]
        context['all_tags_url'] = self._build_url(sort=sort)
        context['current_sort'] = sort
        context['sort_tabs'] = [
            {
                'key': key,
                'label': label,
                'is_active': sort == key,
                'url': self._build_url(tags=selected_slugs, sort=key),
            }
            for key, label in QuestionFilter.SORT_OPTIONS.items()
        ]
        return context


class QuestionDetailView(DetailView):
    model = Question
    template_name = 'questions/question_detail.html'
    context_object_name = 'question'

    def get_queryset(self):
        comment_prefetch = Prefetch(
            'comments',
            queryset=Comment.objects.select_related('author').prefetch_related(
                'votes',
                'replies__author',
                'replies__votes'
            )
        )
        return Question.objects.select_related('author').prefetch_related(
            'tags',
            'votes',
            comment_prefetch,
            Prefetch(
                'answers',
                queryset=Answer.objects.select_related('author').prefetch_related(
                    'votes',
                    comment_prefetch
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

        user_id = self.request.user.id if self.request.user.is_authenticated else None

        def attach_user_vote(item):
            item.user_vote = (
                next((v.value for v in item.votes.all() if v.user_id == user_id), None)
                if user_id
                else None
            )

        attach_user_vote(self.object)
        context['user_vote'] = self.object.user_vote

        for answer in self.object.answers.all():
            attach_user_vote(answer)
            for comment in answer.comments.all():
                attach_user_vote(comment)
                for reply in comment.replies.all():
                    attach_user_vote(reply)

        for comment in self.object.comments.all():
            attach_user_vote(comment)
            for reply in comment.replies.all():
                attach_user_vote(reply)

        return context



class QuestionCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Question
    form_class = QuestionForm
    template_name = 'questions/question_form.html'
    success_message = "Question created successfully."

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('app:question_detail', kwargs={'pk': self.object.pk})


class QuestionUpdateView(LoginRequiredMixin, AuthorRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Question
    form_class = QuestionForm
    template_name = 'questions/question_edit.html'
    context_object_name = 'question'
    success_message = "Question updated successfully."

    def get_success_url(self):
        return reverse('app:question_detail', kwargs={'pk': self.object.pk})


class QuestionDeleteView(LoginRequiredMixin, AuthorRequiredMixin, DeleteSuccessMessageMixin, DeleteView):
    model = Question
    template_name = 'questions/question_confirm_delete.html'
    context_object_name = 'question'
    success_url = reverse_lazy('app:question_list')
    success_message = "Question deleted successfully."


class QuestionVoteView(BaseVoteView):
    model = Question

    def _get_redirect_url(self, question):
        return reverse('app:question_detail', kwargs={'pk': question.pk})

