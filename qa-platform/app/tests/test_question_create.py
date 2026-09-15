from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.views.generic import CreateView

from app.forms import QuestionForm
from app.models import Question, Tag
from app.views import QuestionCreateView

User = get_user_model()


class QuestionCreateViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='password123')
        self.url = reverse('app:question_create')

    def test_view_is_class_based_create_view(self):
        self.assertTrue(issubclass(QuestionCreateView, CreateView))

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_authenticated_user_can_access_form(self):
        self.client.login(username='alice', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'questions/question_form.html')
        self.assertTemplateUsed(response, 'base.html')
        self.assertIsInstance(response.context['form'], QuestionForm)

    def test_successful_question_creation(self):
        self.client.login(username='alice', password='password123')
        data = {
            'title': 'How to use Django CreateView?',
            'description': 'Can someone show a clean example of CreateView with forms?',
            'tags': 'django, python',
        }
        response = self.client.post(self.url, data)
        self.assertEqual(Question.objects.count(), 1)
        question = Question.objects.first()
        self.assertEqual(question.title, 'How to use Django CreateView?')
        self.assertEqual(question.description, 'Can someone show a clean example of CreateView with forms?')
        self.assertEqual(question.author, self.user)
        self.assertEqual(question.tags.count(), 2)
        tag_names = set(question.tags.values_list('name', flat=True))
        self.assertEqual(tag_names, {'django', 'python'})
        self.assertRedirects(response, reverse('app:question_detail', kwargs={'pk': question.pk}))

    def test_author_automatically_assigned_to_logged_in_user(self):
        other_user = User.objects.create_user(username='bob', password='password123')
        self.client.login(username='alice', password='password123')
        data = {
            'title': 'Question authored by Alice',
            'description': 'Checking author assignment.',
            'author': other_user.pk,  # Even if someone attempts to inject author
        }
        self.client.post(self.url, data)
        question = Question.objects.get(title='Question authored by Alice')
        self.assertEqual(question.author, self.user)
        self.assertNotEqual(question.author, other_user)

    def test_tags_creation_and_reuse(self):
        existing_tag = Tag.objects.create(name='python')
        self.client.login(username='alice', password='password123')
        data = {
            'title': 'Reusing existing tag',
            'description': 'This should reuse python and create newtag.',
            'tags': 'python, newtag',
        }
        self.client.post(self.url, data)
        question = Question.objects.get(title='Reusing existing tag')
        self.assertEqual(Tag.objects.count(), 2)  # 'python' was reused, 'newtag' was created
        self.assertIn(existing_tag, question.tags.all())

    def test_multi_word_tags_split_only_by_comma(self):
        self.client.login(username='alice', password='password123')
        data = {
            'title': 'Multi word tags test',
            'description': 'Testing tags with spaces separated only by commas.',
            'tags': 'python, django, web development',
        }
        self.client.post(self.url, data)
        question = Question.objects.get(title='Multi word tags test')
        self.assertEqual(question.tags.count(), 3)
        tag_names = set(question.tags.values_list('name', flat=True))
        self.assertEqual(tag_names, {'python', 'django', 'web development'})

    def test_tags_trims_whitespace(self):
        self.client.login(username='alice', password='password123')
        data = {
            'title': 'Whitespace trimming test',
            'description': 'Testing tag trimming.',
            'tags': '  python  ,   machine learning   ,   ',
        }
        self.client.post(self.url, data)
        question = Question.objects.get(title='Whitespace trimming test')
        tag_names = set(question.tags.values_list('name', flat=True))
        self.assertEqual(tag_names, {'python', 'machine learning'})

    def test_question_creation_without_tags(self):
        self.client.login(username='alice', password='password123')
        data = {
            'title': 'Question with no tags',
            'description': 'Tags are optional.',
            'tags': '',
        }
        response = self.client.post(self.url, data)
        question = Question.objects.get(title='Question with no tags')
        self.assertEqual(question.tags.count(), 0)
        self.assertRedirects(response, reverse('app:question_detail', kwargs={'pk': question.pk}))

    def test_missing_title_rejected(self):
        self.client.login(username='alice', password='password123')
        data = {
            'title': '',
            'description': 'Valid description',
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Question.objects.count(), 0)
        form = response.context['form']
        self.assertFormError(form, 'title', 'This field is required.')

    def test_missing_description_rejected(self):
        self.client.login(username='alice', password='password123')
        data = {
            'title': 'Valid title',
            'description': '',
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Question.objects.count(), 0)
        form = response.context['form']
        self.assertFormError(form, 'description', 'This field is required.')
