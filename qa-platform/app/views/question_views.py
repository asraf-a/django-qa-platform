from urllib.parse import urlencode

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from app.forms import AnswerCommentForm, AnswerForm, QuestionCommentForm, QuestionForm
from app.models import Answer, Comment, Question, Tag
from .mixins import AuthorRequiredMixin, BaseVoteView


class QuestionListView(ListView):
    model = Question
    template_name = 'questions/question_list.html'
    context_object_name = 'questions'
    paginate_by = 10

    def get_queryset(self):
        queryset = (
            Question.objects
            .select_related('author')
            .prefetch_related('tags', 'answers', 'votes')
        )
        tags = self.request.GET.getlist('tag')
        if tags:
            queryset = queryset.filter(tags__slug__in=tags).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_slugs = self.request.GET.getlist('tag')
        all_tags = list(Tag.objects.all())

        for tag in all_tags:
            tag.is_selected = tag.slug in selected_slugs
            if tag.is_selected:
                remaining = [s for s in selected_slugs if s != tag.slug]
            else:
                remaining = selected_slugs + [tag.slug]
            tag.toggle_url = (
                f"?{urlencode({'tag': remaining}, doseq=True)}"
                if remaining
                else reverse('app:question_list')
            )

        context['all_tags'] = all_tags
        context['selected_slugs'] = selected_slugs
        context['selected_tags'] = [t for t in all_tags if t.is_selected]
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

