from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, UpdateView

from app.forms import AnswerCommentForm, CommentEditForm, QuestionCommentForm
from app.models import Answer, Comment, Question
from .mixins import AuthorRequiredMixin


class BaseCommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    template_name = 'questions/question_detail.html'
    target_attr = None  # 'question' or 'answer'


    def get_target(self):
        raise NotImplementedError

    def get_question_id(self, target):
        raise NotImplementedError

    def get_full_question(self, question_id):
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
                    queryset=Answer.objects.select_related('author').prefetch_related(
                        'votes',
                        Prefetch(
                            'comments',
                            queryset=Comment.objects.select_related('author').prefetch_related('replies__author')
                        )
                    )
                )
            ),
            pk=question_id
        )

    def get(self, request, *args, **kwargs):
        target = self.get_target()
        return redirect('app:question_detail', pk=self.get_question_id(target))

    def setup_comment_instance(self, form, target):
        setattr(form.instance, self.target_attr, target)
        if self.target_attr == 'answer':
            form.instance.question = None
        form.instance.author = self.request.user

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        self.setup_comment_instance(form, self.get_target())
        return form

    def form_valid(self, form):
        self.setup_comment_instance(form, self.get_target())
        return super().form_valid(form)

    def get_success_url(self):
        target = self.get_target()
        return reverse('app:question_detail', kwargs={'pk': self.get_question_id(target)})


class QuestionCommentCreateView(BaseCommentCreateView):
    form_class = QuestionCommentForm
    target_attr = 'question'

    def get_target(self):
        return get_object_or_404(Question, pk=self.kwargs['pk'])

    def get_question_id(self, target):
        return target.pk

    def get_question(self):
        return self.get_full_question(self.kwargs['pk'])

    def form_invalid(self, form):
        return self.render_to_response(
            self.get_context_data(
                question=self.get_full_question(self.kwargs['pk']),
                comment_form=form
            )
        )


class AnswerCommentCreateView(BaseCommentCreateView):
    form_class = AnswerCommentForm
    target_attr = 'answer'

    def get_target(self):
        return get_object_or_404(
            Answer.objects.select_related('question'),
            pk=self.kwargs['pk']
        )

    def get_question_id(self, target):
        return target.question_id

    def get_answer(self):
        return self.get_target()

    def form_invalid(self, form):
        target = self.get_target()
        return self.render_to_response(
            self.get_context_data(
                question=self.get_full_question(target.question_id),
                failed_answer_id=target.pk,
                answer_comment_form=form,
            )
        )


class CommentUpdateView(LoginRequiredMixin, AuthorRequiredMixin, UpdateView):
    model = Comment
    form_class = CommentEditForm
    template_name = 'comments/comment_edit.html'
    context_object_name = 'comment'

    def get_queryset(self):
        return Comment.objects.select_related('author', 'question', 'answer__question', 'parent')

    def get_question(self):
        comment = getattr(self, 'object', None) or self.get_object()
        if comment.question:
            return comment.question
        if comment.answer:
            return comment.answer.question
        root = comment.get_root_target()
        if isinstance(root, Question):
            return root
        elif isinstance(root, Answer):
            return root.question
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['question'] = self.get_question()
        return context

    def get_success_url(self):
        question = self.get_question()
        return reverse('app:question_detail', kwargs={'pk': question.pk})
