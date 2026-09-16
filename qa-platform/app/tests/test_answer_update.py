from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.views.generic import UpdateView

from app.forms import AnswerForm
from app.models import Answer, Question
from app.views import AnswerUpdateView

User = get_user_model()


class AnswerUpdateViewTest(TestCase):
    def setUp(self):
        self.question_author = User.objects.create_user(username='alice', password='password123')
        self.answer_author = User.objects.create_user(username='bob', password='password123')
        self.other_user = User.objects.create_user(username='charlie', password='password123')

        self.question = Question.objects.create(
            title='How does answer editing work?',
            description='Testing the answer editing functionality and authorization.',
            author=self.question_author
        )
        self.answer = Answer.objects.create(
            question=self.question,
            author=self.answer_author,
            content='Initial answer content by Bob.'
        )

        self.edit_url = reverse('app:answer_edit', kwargs={'pk': self.answer.pk})
        self.detail_url = reverse('app:question_detail', kwargs={'pk': self.question.pk})

    def test_view_is_class_based_update_view(self):
        self.assertTrue(issubclass(AnswerUpdateView, UpdateView))

    def test_anonymous_user_redirected_to_login(self):
        # GET request
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
        self.assertIn(f'next={self.edit_url}', response.url)

        # POST request
        post_response = self.client.post(self.edit_url, {'content': 'Hacked by anonymous.'})
        self.assertEqual(post_response.status_code, 302)
        self.assertIn('/accounts/login/', post_response.url)
        self.answer.refresh_from_db()
        self.assertEqual(self.answer.content, 'Initial answer content by Bob.')

    def test_author_can_access_edit_page(self):
        self.client.login(username='bob', password='password123')
        response = self.client.get(self.edit_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'answers/answer_edit.html')
        self.assertTemplateUsed(response, 'base.html')
        self.assertIsInstance(response.context['form'], AnswerForm)
        self.assertEqual(response.context['answer'], self.answer)

    def test_form_prepopulated_with_existing_content(self):
        self.client.login(username='bob', password='password123')
        response = self.client.get(self.edit_url)

        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertEqual(form.initial['content'], 'Initial answer content by Bob.')
        self.assertContains(response, 'Initial answer content by Bob.')

    def test_non_author_forbidden_on_get(self):
        self.client.login(username='charlie', password='password123')
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 403)

    def test_non_author_forbidden_on_post(self):
        self.client.login(username='charlie', password='password123')
        response = self.client.post(self.edit_url, {'content': 'Modified by non-author Charlie.'})
        self.assertEqual(response.status_code, 403)

        self.answer.refresh_from_db()
        self.assertEqual(self.answer.content, 'Initial answer content by Bob.')

    def test_author_can_update_answer_content(self):
        self.client.login(username='bob', password='password123')
        response = self.client.post(self.edit_url, {'content': 'Updated answer content with more useful details.'})

        self.assertRedirects(response, self.detail_url)
        self.answer.refresh_from_db()
        self.assertEqual(self.answer.content, 'Updated answer content with more useful details.')

    def test_answer_author_remains_unchanged_after_edit(self):
        self.client.login(username='bob', password='password123')
        response = self.client.post(self.edit_url, {
            'content': 'Attempting to change author.',
            'author': self.other_user.pk
        })
        self.assertRedirects(response, self.detail_url)
        self.answer.refresh_from_db()
        self.assertEqual(self.answer.author, self.answer_author)
        self.assertEqual(self.answer.question, self.question)

    def test_empty_answer_rejected(self):
        self.client.login(username='bob', password='password123')
        response = self.client.post(self.edit_url, {'content': ''})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'answers/answer_edit.html')
        form = response.context['form']
        self.assertFormError(form, 'content', 'This field is required.')

        self.answer.refresh_from_db()
        self.assertEqual(self.answer.content, 'Initial answer content by Bob.')

    def test_whitespace_only_answer_rejected(self):
        self.client.login(username='bob', password='password123')
        response = self.client.post(self.edit_url, {'content': '   \n\t   '})

        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFormError(form, 'content', 'This field is required.')

        self.answer.refresh_from_db()
        self.assertEqual(self.answer.content, 'Initial answer content by Bob.')

    def test_edit_nonexistent_answer_returns_404(self):
        self.client.login(username='bob', password='password123')
        invalid_url = reverse('app:answer_edit', kwargs={'pk': 99999})
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, 404)

    def test_edit_button_visible_to_answer_author_on_question_detail(self):
        self.client.login(username='bob', password='password123')
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.edit_url)

    def test_edit_button_hidden_from_non_author_on_question_detail(self):
        self.client.login(username='charlie', password='password123')
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.edit_url)

    def test_edit_button_hidden_from_anonymous_user_on_question_detail(self):
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.edit_url)
