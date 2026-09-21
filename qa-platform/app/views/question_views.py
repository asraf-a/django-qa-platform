from urllib.parse import urlencode

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import IntegerField, OuterRef, Prefetch, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from app.forms import AnswerCommentForm, AnswerForm, QuestionCommentForm, QuestionForm
from app.models import Answer, Comment, Question, Tag, Vote
from .mixins import AuthorRequiredMixin, BaseVoteView, DeleteSuccessMessageMixin


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

        sort = self.request.GET.get('sort', 'newest')
        if sort == 'most_voted':
            ct = ContentType.objects.get_for_model(Question)
            vote_subquery = (
                Vote.objects
                .filter(content_type=ct, object_id=OuterRef('pk'))
                .values('object_id')
                .annotate(total=Sum('value'))
                .values('total')
            )
            queryset = queryset.annotate(
                vote_score=Coalesce(Subquery(vote_subquery, output_field=IntegerField()), Value(0))
            ).order_by('-vote_score', '-created_at')
        elif sort == 'unanswered':
            queryset = queryset.filter(answers__isnull=True).order_by('-created_at')
        else:
            queryset = queryset.order_by('-created_at')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_slugs = self.request.GET.getlist('tag')
        sort = self.request.GET.get('sort', 'newest')
        if sort not in ('newest', 'most_voted', 'unanswered'):
            sort = 'newest'

        all_tags = list(Tag.objects.all())

        for tag in all_tags:
            tag.is_selected = tag.slug in selected_slugs
            if tag.is_selected:
                remaining = [s for s in selected_slugs if s != tag.slug]
            else:
                remaining = selected_slugs + [tag.slug]

            params = {}
            if remaining:
                params['tag'] = remaining
            if sort != 'newest':
                params['sort'] = sort
            query_str = urlencode(params, doseq=True)
            tag.toggle_url = f"?{query_str}" if query_str else reverse('app:question_list')

        # Generate sort tabs while preserving active tag filters
        sort_options = [
            ('newest', 'Newest'),
            ('most_voted', 'Most Voted'),
            ('unanswered', 'Unanswered'),
        ]
        sort_tabs = []
        for sort_key, sort_label in sort_options:
            params = {}
            if selected_slugs:
                params['tag'] = selected_slugs
            if sort_key != 'newest':
                params['sort'] = sort_key
            query_str = urlencode(params, doseq=True)
            sort_tabs.append({
                'key': sort_key,
                'label': sort_label,
                'is_active': sort == sort_key,
                'url': f"?{query_str}" if query_str else reverse('app:question_list'),
            })

        # URL for "All" tag reset that preserves current sort
        all_tags_params = {'sort': sort} if sort != 'newest' else {}
        context['all_tags_url'] = (
            f"?{urlencode(all_tags_params)}"
            if all_tags_params
            else reverse('app:question_list')
        )

        context['all_tags'] = all_tags
        context['selected_slugs'] = selected_slugs
        context['selected_tags'] = [t for t in all_tags if t.is_selected]
        context['current_sort'] = sort
        context['sort_tabs'] = sort_tabs
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

