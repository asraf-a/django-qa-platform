from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.views.generic import DeleteView

from app.models import Question, Tag
from app.views import QuestionDeleteView

User = get_user_model()


class QuestionDeleteViewTest(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username='author', password='password123')
        self.other_user = User.objects.create_user(username='otheruser', password='password123')

        self.tag = Tag.objects.create(name='python')

        self.question = Question.objects.create(
            title='Question to be deleted',
            description='This question will be deleted in the tests.',
            author=self.author,
        )
        self.question.tags.add(self.tag)

        self.delete_url = reverse('app:question_delete', kwargs={'pk': self.question.pk})
        self.detail_url = reverse('app:question_detail', kwargs={'pk': self.question.pk})
        self.list_url = reverse('app:question_list')

    def test_view_is_class_based_delete_view(self):
        self.assertTrue(issubclass(QuestionDeleteView, DeleteView))

    def test_anonymous_user_redirected_to_login(self):
        # GET request
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
        self.assertIn(f'next={self.delete_url}', response.url)

        # POST request
        post_response = self.client.post(self.delete_url)
        self.assertEqual(post_response.status_code, 302)
        self.assertIn('/accounts/login/', post_response.url)
        self.assertTrue(Question.objects.filter(pk=self.question.pk).exists())

    def test_author_can_access_delete_confirmation_page(self):
        self.client.login(username='author', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'questions/question_confirm_delete.html')
        self.assertTemplateUsed(response, 'base.html')
        self.assertContains(response, 'Delete Question')
        self.assertContains(response, 'Question to be deleted')
        self.assertContains(response, 'This action is permanent and cannot be undone.')

    def test_non_author_forbidden_on_get(self):
        self.client.login(username='otheruser', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Question.objects.filter(pk=self.question.pk).exists())

    def test_non_author_forbidden_on_post(self):
        self.client.login(username='otheruser', password='password123')
        response = self.client.post(self.delete_url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Question.objects.filter(pk=self.question.pk).exists())

    def test_get_request_does_not_delete_question(self):
        self.client.login(username='author', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Question.objects.filter(pk=self.question.pk).exists())

    def test_successful_post_deletes_question_and_redirects(self):
        self.client.login(username='author', password='password123')
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, self.list_url)
        self.assertFalse(Question.objects.filter(pk=self.question.pk).exists())

    def test_cancel_link_points_to_question_detail(self):
        self.client.login(username='author', password='password123')
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.detail_url)

    def test_delete_button_visible_to_author_on_detail_page(self):
        self.client.login(username='author', password='password123')
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.delete_url)
        self.assertContains(response, 'Delete')

    def test_delete_button_hidden_from_non_author(self):
        self.client.login(username='otheruser', password='password123')
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.delete_url)

    def test_delete_button_hidden_from_anonymous_user(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.delete_url)
