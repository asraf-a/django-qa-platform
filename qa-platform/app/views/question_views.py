from django.db.models import Prefetch
from django.views.generic import DetailView, ListView

from app.models import Answer, Question


class QuestionListView(ListView):
    model = Question
    template_name = 'questions/question_list.html'
    context_object_name = 'questions'

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
                'answers',
                queryset=Answer.objects.select_related('author').prefetch_related('votes')
            )
        )
