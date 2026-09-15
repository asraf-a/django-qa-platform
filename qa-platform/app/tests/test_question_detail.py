from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.views.generic import DetailView

from app.models import Answer, Question, Tag, Vote
from app.views import QuestionDetailView

User = get_user_model()


class QuestionDetailViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='john', password='password123')
        self.answerer = User.objects.create_user(username='sarah', password='password123')
        self.tag = Tag.objects.create(name='python')

        self.question = Question.objects.create(
            title='How does Django DetailView work?',
            description='I need a detailed explanation of Django DetailView and context.',
            author=self.user
        )
        self.question.tags.add(self.tag)

        self.url = reverse('app:question_detail', kwargs={'pk': self.question.pk})

    def test_view_is_class_based(self):
        self.assertTrue(issubclass(QuestionDetailView, DetailView))

    def test_question_detail_url_by_name(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_question_detail_url_by_path(self):
        response = self.client.get(f'/questions/{self.question.pk}/')
        self.assertEqual(response.status_code, 200)

    def test_question_detail_uses_correct_templates(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'questions/question_detail.html')
        self.assertTemplateUsed(response, 'base.html')

    def test_question_detail_displays_question_content(self):
        ct = ContentType.objects.get_for_model(Question)
        Vote.objects.create(
            user=self.user,
            content_type=ct,
            object_id=self.question.pk,
            value=Vote.UPVOTE
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'How does Django DetailView work?')
        self.assertContains(response, 'I need a detailed explanation of Django DetailView and context.')
        self.assertContains(response, 'john')
        self.assertContains(response, '1 vote')

    def test_question_detail_displays_tags(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '#python')

    def test_question_detail_displays_answers_and_authors(self):
        answer = Answer.objects.create(
            question=self.question,
            author=self.answerer,
            content='DetailView inherits from SingleObjectTemplateResponseMixin and BaseDetailView.'
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1 Answer')
        self.assertContains(response, 'DetailView inherits from SingleObjectTemplateResponseMixin')
        self.assertContains(response, 'sarah')

    def test_question_detail_empty_answer_state(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '0 Answers')
        self.assertContains(response, 'No answers yet')

    def test_question_detail_404_for_nonexistent_question(self):
        invalid_url = reverse('app:question_detail', kwargs={'pk': 99999})
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, 404)

    def test_question_list_links_to_question_detail(self):
        list_url = reverse('app:question_list')
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.url)
