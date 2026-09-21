from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.views.generic import CreateView

from app.forms import RegistrationForm
from app.views import RegisterView

User = get_user_model()


class RegisterViewTest(TestCase):
    def setUp(self):
        self.url = reverse('app:register')
        self.valid_data = {
            'username': 'newdeveloper',
            'email': 'dev@example.com',
            'password1': 'StrongP@ssw0rd123!',
            'password2': 'StrongP@ssw0rd123!',
        }

    def test_view_is_class_based(self):
        self.assertTrue(issubclass(RegisterView, CreateView))

    def test_registration_page_status_and_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')
        self.assertTemplateUsed(response, 'base.html')
        self.assertIsInstance(response.context['form'], RegistrationForm)

    def test_valid_registration_creates_user(self):
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get(username='newdeveloper')
        self.assertEqual(user.email, 'dev@example.com')
        self.assertRedirects(response, reverse('app:question_list'))

    def test_password_is_hashed_securely(self):
        self.client.post(self.url, self.valid_data)
        user = User.objects.get(username='newdeveloper')
        self.assertNotEqual(user.password, 'StrongP@ssw0rd123!')
        self.assertTrue(user.check_password('StrongP@ssw0rd123!'))
        self.assertTrue(user.password.startswith('pbkdf2_sha256$') or '$' in user.password)

    def test_password_confirmation_mismatch_rejected(self):
        data = self.valid_data.copy()
        data['password2'] = 'DifferentPassword123!'
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)
        form = response.context['form']
        self.assertTrue(form.has_error('password2'))

    def test_duplicate_username_rejected(self):
        User.objects.create_user(username='newdeveloper', email='existing@example.com', password='password123')
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
        form = response.context['form']
        self.assertTrue(form.has_error('username'))

    def test_missing_username_rejected(self):
        data = self.valid_data.copy()
        data['username'] = ''
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)
        form = response.context['form']
        self.assertTrue(form.has_error('username'))

    def test_missing_email_rejected(self):
        data = self.valid_data.copy()
        data['email'] = ''
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)
        form = response.context['form']
        self.assertTrue(form.has_error('email'))

    def test_invalid_email_format_rejected(self):
        data = self.valid_data.copy()
        data['email'] = 'not-an-email'
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)
        form = response.context['form']
        self.assertTrue(form.has_error('email'))

    def test_user_cannot_register_as_staff_or_superuser(self):
        data = self.valid_data.copy()
        data['is_staff'] = True
        data['is_superuser'] = True
        self.client.post(self.url, data)
        user = User.objects.get(username='newdeveloper')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_user_is_automatically_logged_in_and_welcome_message_displayed(self):
        response = self.client.post(self.url, self.valid_data, follow=True)
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertEqual(response.context['user'].username, 'newdeveloper')
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn('Welcome to Q&A Platform, newdeveloper!', str(messages[0]))
        self.assertContains(response, 'Welcome to Q&amp;A Platform, newdeveloper!')
        self.assertContains(response, 'Your account has been created.')

    def test_invalid_registration_does_not_create_user(self):
        data = {
            'username': '',
            'email': '',
            'password1': '',
            'password2': '',
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)
