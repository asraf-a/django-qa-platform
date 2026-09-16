from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.views.generic import CreateView

from app.forms import AnswerForm
from app.models import Answer, Question
from app.views import AnswerCreateView

User = get_user_model()


class AnswerCreateViewTest(TestCase):
    def setUp(self):
        self.question_author = User.objects.create_user(username='alice', password='password123')
        self.answer_author = User.objects.create_user(username='bob', password='password123')
        self.other_user = User.objects.create_user(username='charlie', password='password123')

        self.question = Question.objects.create(
            title='How to write tests for Answer creation?',
            description='I need to test Answer creation view and relations thoroughly.',
            author=self.question_author
        )
        self.url = reverse('app:answer_create', kwargs={'pk': self.question.pk})
        self.detail_url = reverse('app:question_detail', kwargs={'pk': self.question.pk})

    def test_view_is_class_based_create_view(self):
        self.assertTrue(issubclass(AnswerCreateView, CreateView))

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.post(self.url, {'content': 'This is an answer from anonymous.'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
        self.assertEqual(Answer.objects.count(), 0)

    def test_get_request_redirects_to_question_detail(self):
        self.client.login(username='bob', password='password123')
        response = self.client.get(self.url)
        self.assertRedirects(response, self.detail_url)

    def test_authenticated_user_can_create_answer(self):
        self.client.login(username='bob', password='password123')
        response = self.client.post(self.url, {'content': 'Here is a comprehensive answer to your question.'})

        self.assertEqual(Answer.objects.count(), 1)
        answer = Answer.objects.first()
        self.assertEqual(answer.content, 'Here is a comprehensive answer to your question.')
        self.assertEqual(answer.question, self.question)
        self.assertEqual(answer.author, self.answer_author)
        self.assertRedirects(response, self.detail_url)

    def test_answer_linked_to_correct_question(self):
        other_question = Question.objects.create(
            title='Another question',
            description='Testing question association.',
            author=self.question_author
        )
        self.client.login(username='bob', password='password123')
        response = self.client.post(self.url, {'content': 'Specific answer for question 1.'})

        self.assertRedirects(response, self.detail_url)
        self.assertEqual(self.question.answers.count(), 1)
        self.assertEqual(other_question.answers.count(), 0)
        self.assertEqual(self.question.answers.first().content, 'Specific answer for question 1.')

    def test_author_automatically_assigned_to_logged_in_user(self):
        self.client.login(username='bob', password='password123')
        # Attempt to spoof author in POST data
        response = self.client.post(self.url, {
            'content': 'Attempting to spoof author.',
            'author': self.other_user.pk
        })
        self.assertRedirects(response, self.detail_url)
        answer = Answer.objects.get(content='Attempting to spoof author.')
        self.assertEqual(answer.author, self.answer_author)
        self.assertNotEqual(answer.author, self.other_user)

    def test_empty_answer_rejected(self):
        self.client.login(username='bob', password='password123')
        response = self.client.post(self.url, {'content': ''})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Answer.objects.count(), 0)
        form = response.context['answer_form']
        self.assertFormError(form, 'content', 'This field is required.')

    def test_whitespace_only_answer_rejected(self):
        self.client.login(username='bob', password='password123')
        response = self.client.post(self.url, {'content': '    \n\t   '})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Answer.objects.count(), 0)
        form = response.context['answer_form']
        self.assertFormError(form, 'content', 'This field is required.')

    def test_invalid_submission_preserves_question_detail_context(self):
        self.client.login(username='bob', password='password123')
        response = self.client.post(self.url, {'content': ''})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'questions/question_detail.html')
        self.assertEqual(response.context['question'], self.question)
        self.assertContains(response, 'How to write tests for Answer creation?')
        self.assertContains(response, 'This field is required.')

    def test_answer_creation_for_nonexistent_question_returns_404(self):
        self.client.login(username='bob', password='password123')
        invalid_url = reverse('app:answer_create', kwargs={'pk': 99999})
        response = self.client.post(invalid_url, {'content': 'Answer for non-existent question.'})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Answer.objects.count(), 0)

    def test_answer_form_appears_on_question_detail_for_authenticated_user(self):
        self.client.login(username='bob', password='password123')
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['answer_form'], AnswerForm)
        self.assertContains(response, f'action="{self.url}"')
        self.assertContains(response, 'Post Your Answer')
        self.assertContains(response, 'name="content"')

    def test_login_prompt_appears_on_question_detail_for_anonymous_user(self):
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, f'action="{self.url}"')
        self.assertContains(response, 'You must be logged in to answer this question.')
        self.assertContains(response, reverse('app:login'))
        self.assertContains(response, reverse('app:register'))

    def test_multiple_answers_by_different_users(self):
        self.client.login(username='bob', password='password123')
        self.client.post(self.url, {'content': 'First answer by Bob.'})

        self.client.login(username='charlie', password='password123')
        self.client.post(self.url, {'content': 'Second answer by Charlie.'})

        self.assertEqual(self.question.answers.count(), 2)
        response = self.client.get(self.detail_url)
        self.assertContains(response, 'First answer by Bob.')
        self.assertContains(response, 'Second answer by Charlie.')
        self.assertContains(response, '2 Answers')
