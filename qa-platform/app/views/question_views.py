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

    def _get_requested_tag_slugs(self):
        raw_tags = self.request.GET.getlist('tag')
        tag_slugs = []
        for item in raw_tags:
            for t in item.split(','):
                t = t.strip()
                if t and t not in tag_slugs:
                    tag_slugs.append(t)
        return tag_slugs

    def _get_selected_tags(self):
        if not hasattr(self, '_cached_selected_tags'):
            tag_slugs = self._get_requested_tag_slugs()
            selected_tags = []
            has_invalid_tag = False
            for slug in tag_slugs:
                tag = Tag.objects.filter(slug=slug).first() or Tag.objects.filter(name__iexact=slug).first()
                if tag:
                    if tag not in selected_tags:
                        selected_tags.append(tag)
                else:
                    has_invalid_tag = True
            self._cached_selected_tags = selected_tags
            self._cached_has_invalid_tag = has_invalid_tag
        return self._cached_selected_tags, self._cached_has_invalid_tag

    def get_queryset(self):
        queryset = Question.objects.select_related('author').prefetch_related('tags', 'answers', 'votes').all()
        selected_tags, has_invalid_tag = self._get_selected_tags()
        tag_slugs = self._get_requested_tag_slugs()
        if tag_slugs and not selected_tags:
            return queryset.none()
        if selected_tags:
            queryset = queryset.filter(tags__in=selected_tags).distinct()
        return queryset


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_tags, has_invalid_tag = self._get_selected_tags()
        tag_slugs = self._get_requested_tag_slugs()

        tag_query_string = ''.join(f'&tag={s}' for s in tag_slugs)
        all_tags = list(Tag.objects.all())
        selected_slugs_set = {t.slug for t in selected_tags}

        all_tags_data = []
        for tag in all_tags:
            if tag.slug in selected_slugs_set:
                remaining = [s for s in tag_slugs if s != tag.slug and s.lower() != tag.name.lower()]
                toggle_url = ('?' + '&'.join(f'tag={s}' for s in remaining)) if remaining else '?'
                is_selected = True
            else:
                new_slugs = tag_slugs + [tag.slug]
                toggle_url = '?' + '&'.join(f'tag={s}' for s in new_slugs)
                is_selected = False
            all_tags_data.append({
                'tag': tag,
                'is_selected': is_selected,
                'toggle_url': toggle_url,
            })

        active_filters = []
        for tag in selected_tags:
            remaining = [s for s in tag_slugs if s != tag.slug and s.lower() != tag.name.lower()]
            remove_url = ('?' + '&'.join(f'tag={s}' for s in remaining)) if remaining else '?'
            active_filters.append({
                'name': tag.name,
                'slug': tag.slug,
                'remove_url': remove_url,
                'is_valid': True,
            })
        for slug in tag_slugs:
            if not any(t.slug == slug or t.name.lower() == slug.lower() for t in selected_tags):
                remaining = [s for s in tag_slugs if s != slug]
                remove_url = ('?' + '&'.join(f'tag={s}' for s in remaining)) if remaining else '?'
                active_filters.append({
                    'name': slug,
                    'slug': slug,
                    'remove_url': remove_url,
                    'is_valid': False,
                })

        context['selected_tags'] = selected_tags
        context['selected_tag'] = selected_tags[0] if len(selected_tags) == 1 else None
        context['tag_param'] = tag_slugs[0] if tag_slugs else ''
        context['tag_slugs'] = tag_slugs
        context['tag_query_string'] = tag_query_string
        context['all_tags_data'] = all_tags_data
        context['all_tags'] = all_tags
        context['active_filters'] = active_filters
        context['has_invalid_tag'] = has_invalid_tag
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

