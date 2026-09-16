from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.views.generic import DeleteView

from app.models import Answer, Question
from app.views import AnswerDeleteView

User = get_user_model()


class AnswerDeleteViewTest(TestCase):
    def setUp(self):
        self.question_author = User.objects.create_user(username='alice', password='password123')
        self.answer_author = User.objects.create_user(username='bob', password='password123')
        self.other_user = User.objects.create_user(username='charlie', password='password123')

        self.question = Question.objects.create(
            title='How does answer deletion work?',
            description='Testing the answer deletion functionality and authorization.',
            author=self.question_author,
        )
        self.answer = Answer.objects.create(
            question=self.question,
            author=self.answer_author,
            content='This is Bob\'s answer to be deleted.',
        )

        self.delete_url = reverse('app:answer_delete', kwargs={'pk': self.answer.pk})
        self.detail_url = reverse('app:question_detail', kwargs={'pk': self.question.pk})

    def test_view_is_class_based_delete_view(self):
        self.assertTrue(issubclass(AnswerDeleteView, DeleteView))

    def test_anonymous_user_redirected_to_login_on_get(self):
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
        self.assertIn(f'next={self.delete_url}', response.url)

    def test_anonymous_user_redirected_to_login_on_post(self):
        response = self.client.post(self.delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
        self.assertTrue(Answer.objects.filter(pk=self.answer.pk).exists())

    def test_author_can_access_delete_confirmation_page(self):
        self.client.login(username='bob', password='password123')
        response = self.client.get(self.delete_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'answers/answer_confirm_delete.html')
        self.assertTemplateUsed(response, 'base.html')
        self.assertContains(response, 'Delete Answer')
        self.assertContains(response, 'How does answer deletion work?')
        self.assertContains(response, 'This is Bob&#x27;s answer to be deleted.')
        self.assertContains(response, 'This action is permanent and cannot be undone.')

    def test_non_author_forbidden_on_get(self):
        self.client.login(username='charlie', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Answer.objects.filter(pk=self.answer.pk).exists())

    def test_non_author_forbidden_on_post(self):
        self.client.login(username='charlie', password='password123')
        response = self.client.post(self.delete_url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Answer.objects.filter(pk=self.answer.pk).exists())

    def test_question_author_cannot_delete_another_users_answer(self):
        # Alice is the question author, but Bob is the answer author
        self.client.login(username='alice', password='password123')
        response = self.client.post(self.delete_url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Answer.objects.filter(pk=self.answer.pk).exists())

    def test_get_request_does_not_delete_answer(self):
        self.client.login(username='bob', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Answer.objects.filter(pk=self.answer.pk).exists())

    def test_successful_post_deletes_answer_and_redirects_to_question_detail(self):
        self.client.login(username='bob', password='password123')
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, self.detail_url)
        self.assertFalse(Answer.objects.filter(pk=self.answer.pk).exists())
        self.assertEqual(self.question.answers.count(), 0)

    def test_cancel_link_points_to_question_detail(self):
        self.client.login(username='bob', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.detail_url)

    def test_delete_button_visible_to_author_on_detail_page(self):
        self.client.login(username='bob', password='password123')
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.delete_url)
        self.assertContains(response, 'Delete')

    def test_delete_button_hidden_from_non_author(self):
        self.client.login(username='charlie', password='password123')
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.delete_url)

    def test_delete_button_hidden_from_question_author(self):
        self.client.login(username='alice', password='password123')
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.delete_url)

    def test_delete_button_hidden_from_anonymous_user(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.delete_url)

    def test_404_for_nonexistent_answer(self):
        nonexistent_url = reverse('app:answer_delete', kwargs={'pk': 99999})
        self.client.login(username='bob', password='password123')

        get_response = self.client.get(nonexistent_url)
        self.assertEqual(get_response.status_code, 404)

        post_response = self.client.post(nonexistent_url)
        self.assertEqual(post_response.status_code, 404)
