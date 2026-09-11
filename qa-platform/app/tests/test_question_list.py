from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.views.generic import ListView

from app.models import Answer, Question, Tag, Vote
from app.views import QuestionListView

User = get_user_model()


class QuestionListViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='password123')
        self.url = reverse('app:question_list')

    def test_view_is_class_based(self):
        self.assertTrue(issubclass(QuestionListView, ListView))

    def test_question_list_status_code_by_name(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_question_list_status_code_at_root(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_question_list_uses_correct_templates(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'questions/question_list.html')
        self.assertTemplateUsed(response, 'base.html')

    def test_question_list_empty_state(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['questions'], [])
        self.assertContains(response, 'No questions asked yet')

    def test_question_list_displays_question_data(self):
        tag1 = Tag.objects.create(name='python')
        tag2 = Tag.objects.create(name='django')

        question = Question.objects.create(
            title='How to optimize Django queries?',
            description='I want to learn about select_related and prefetch_related.',
            author=self.user
        )
        question.tags.add(tag1, tag2)

        Answer.objects.create(
            question=question,
            author=self.user,
            content='Use prefetch_related for M2M and reverse relations.'
        )

        ct = ContentType.objects.get_for_model(Question)
        Vote.objects.create(
            user=self.user,
            content_type=ct,
            object_id=question.pk,
            value=Vote.UPVOTE
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'How to optimize Django queries?')
        self.assertContains(response, 'select_related')
        self.assertContains(response, 'alice')
        self.assertContains(response, '#python')
        self.assertContains(response, '#django')
        self.assertContains(response, '1')  # Vote count / score
        self.assertContains(response, '1')  # Answer count

    def test_question_list_ordering_newest_first(self):
        q1 = Question.objects.create(
            title='First Question',
            description='First description',
            author=self.user
        )
        q2 = Question.objects.create(
            title='Second Question',
            description='Second description',
            author=self.user
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        questions = list(response.context['questions'])
        self.assertEqual(questions, [q2, q1])
