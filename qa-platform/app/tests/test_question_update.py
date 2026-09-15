from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.views.generic import UpdateView

from app.forms import QuestionForm
from app.models import Question, Tag
from app.views import QuestionUpdateView

User = get_user_model()


class QuestionUpdateViewTest(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username='author', password='password123')
        self.other_user = User.objects.create_user(username='otheruser', password='password123')

        self.tag1 = Tag.objects.create(name='python')
        self.tag2 = Tag.objects.create(name='django')

        self.question = Question.objects.create(
            title='Initial Question Title',
            description='Initial Question Description',
            author=self.author,
        )
        self.question.tags.add(self.tag1, self.tag2)

        self.edit_url = reverse('app:question_edit', kwargs={'pk': self.question.pk})
        self.detail_url = reverse('app:question_detail', kwargs={'pk': self.question.pk})

    def test_view_is_class_based_update_view(self):
        self.assertTrue(issubclass(QuestionUpdateView, UpdateView))

    def test_anonymous_user_redirected_to_login(self):
        # GET request
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
        self.assertIn(f'next={self.edit_url}', response.url)

        # POST request
        post_response = self.client.post(self.edit_url, {'title': 'New', 'description': 'Desc'})
        self.assertEqual(post_response.status_code, 302)
        self.assertIn('/accounts/login/', post_response.url)

    def test_author_can_access_edit_page(self):
        self.client.login(username='author', password='password123')
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'questions/question_edit.html')
        self.assertTemplateUsed(response, 'base.html')
        self.assertIsInstance(response.context['form'], QuestionForm)

    def test_form_prepopulated_with_existing_data_and_tags(self):
        self.client.login(username='author', password='password123')
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 200)

        # Verify title and description are in the context / form
        form = response.context['form']
        self.assertEqual(form.initial['title'], 'Initial Question Title')
        self.assertEqual(form.initial['description'], 'Initial Question Description')
        initial_tags = {tag.strip() for tag in form.initial['tags'].split(',')}
        self.assertEqual(initial_tags, {'python', 'django'})

        # Verify HTML contains the pre-populated values
        self.assertContains(response, 'Initial Question Title')
        self.assertContains(response, 'Initial Question Description')
        self.assertContains(response, 'django')
        self.assertContains(response, 'python')

    def test_non_author_forbidden_on_get(self):
        self.client.login(username='otheruser', password='password123')
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 403)

    def test_non_author_forbidden_on_post(self):
        self.client.login(username='otheruser', password='password123')
        data = {
            'title': 'Hacked Title',
            'description': 'Hacked Description',
            'tags': 'hacked',
        }
        response = self.client.post(self.edit_url, data)
        self.assertEqual(response.status_code, 403)

        # Verify database was not changed
        self.question.refresh_from_db()
        self.assertEqual(self.question.title, 'Initial Question Title')
        self.assertEqual(self.question.description, 'Initial Question Description')

    def test_author_can_update_title_and_description(self):
        self.client.login(username='author', password='password123')
        data = {
            'title': 'Updated Title by Author',
            'description': 'Updated Description by Author',
            'tags': 'python, django',
        }
        response = self.client.post(self.edit_url, data)
        self.assertRedirects(response, self.detail_url)

        self.question.refresh_from_db()
        self.assertEqual(self.question.title, 'Updated Title by Author')
        self.assertEqual(self.question.description, 'Updated Description by Author')
        self.assertEqual(self.question.author, self.author)

    def test_author_remains_unchanged_even_if_tampered(self):
        self.client.login(username='author', password='password123')
        data = {
            'title': 'Legit Title',
            'description': 'Legit Description',
            'author': self.other_user.pk,
        }
        self.client.post(self.edit_url, data)
        self.question.refresh_from_db()
        self.assertEqual(self.question.author, self.author)

    def test_tags_updated_reused_and_removed(self):
        self.client.login(username='author', password='password123')
        # We start with: python, django
        # We change to: django, web development (python removed, django kept, web development created)
        data = {
            'title': 'Updated Question with New Tags',
            'description': 'Checking tag sync.',
            'tags': 'django, web development',
        }
        response = self.client.post(self.edit_url, data)
        self.assertRedirects(response, self.detail_url)

        self.question.refresh_from_db()
        tag_names = set(self.question.tags.values_list('name', flat=True))
        self.assertEqual(tag_names, {'django', 'web development'})
        self.assertNotIn('python', tag_names)

        # Verify 'web development' Tag object was created and 'django' reused
        self.assertTrue(Tag.objects.filter(name='web development').exists())
        self.assertEqual(Tag.objects.filter(name='django').count(), 1)

    def test_tags_can_be_cleared(self):
        self.client.login(username='author', password='password123')
        data = {
            'title': 'Question without tags now',
            'description': 'All tags removed.',
            'tags': '',
        }
        response = self.client.post(self.edit_url, data)
        self.assertRedirects(response, self.detail_url)

        self.question.refresh_from_db()
        self.assertEqual(self.question.tags.count(), 0)

    def test_invalid_missing_title_rejected(self):
        self.client.login(username='author', password='password123')
        data = {
            'title': '',
            'description': 'Valid description',
        }
        response = self.client.post(self.edit_url, data)
        self.assertEqual(response.status_code, 200)
        self.question.refresh_from_db()
        self.assertEqual(self.question.title, 'Initial Question Title')
        form = response.context['form']
        self.assertTrue(form.has_error('title'))

    def test_invalid_missing_description_rejected(self):
        self.client.login(username='author', password='password123')
        data = {
            'title': 'Valid Title',
            'description': '',
        }
        response = self.client.post(self.edit_url, data)
        self.assertEqual(response.status_code, 200)
        self.question.refresh_from_db()
        self.assertEqual(self.question.description, 'Initial Question Description')
        form = response.context['form']
        self.assertTrue(form.has_error('description'))

    def test_edit_button_visible_to_author(self):
        self.client.login(username='author', password='password123')
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.edit_url)
        self.assertContains(response, 'Edit')

    def test_edit_button_hidden_from_non_author(self):
        self.client.login(username='otheruser', password='password123')
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.edit_url)

    def test_edit_button_hidden_from_anonymous_user(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.edit_url)
