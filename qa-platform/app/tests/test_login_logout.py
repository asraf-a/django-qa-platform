from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView, LogoutView
from django.test import TestCase
from django.urls import reverse

from app.views import UserLoginView, UserLogoutView

User = get_user_model()


class UserLoginLogoutTest(TestCase):
    def setUp(self):
        self.login_url = reverse('app:login')
        self.logout_url = reverse('app:logout')
        self.username = 'testdeveloper'
        self.password = 'ComplexP@ssw0rd123!'
        self.user = User.objects.create_user(
            username=self.username,
            email='testdeveloper@example.com',
            password=self.password
        )

    def test_login_view_is_class_based(self):
        self.assertTrue(issubclass(UserLoginView, LoginView))

    def test_logout_view_is_class_based(self):
        self.assertTrue(issubclass(UserLogoutView, LogoutView))

    def test_login_page_renders_status_200_and_template(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')
        self.assertTemplateUsed(response, 'base.html')
        self.assertContains(response, 'Sign in to your account')

    def test_valid_credentials_successfully_authenticates_user(self):
        data = {
            'username': self.username,
            'password': self.password,
        }
        response = self.client.post(self.login_url, data)
        self.assertRedirects(response, reverse('app:question_list'))
        # Verify session has authenticated user
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_invalid_password_rejected(self):
        data = {
            'username': self.username,
            'password': 'WrongPassword999!',
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(response, 'Please enter a correct username and password')

    def test_nonexistent_username_rejected(self):
        data = {
            'username': 'ghostuser',
            'password': self.password,
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(response, 'Please enter a correct username and password')

    def test_empty_credentials_rejected(self):
        data = {
            'username': '',
            'password': '',
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        form = response.context['form']
        self.assertTrue(form.has_error('username'))
        self.assertTrue(form.has_error('password'))

    def test_next_parameter_redirects_to_target_page(self):
        target_url = reverse('app:question_create')
        login_with_next = f"{self.login_url}?next={target_url}"
        
        # Verify GET preserves next in template
        response = self.client.get(login_with_next)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'name="next" value="{target_url}"')

        # POST with next parameter
        data = {
            'username': self.username,
            'password': self.password,
            'next': target_url,
        }
        response = self.client.post(login_with_next, data)
        self.assertRedirects(response, target_url)

    def test_authenticated_user_can_logout(self):
        self.client.login(username=self.username, password=self.password)
        self.assertIn('_auth_user_id', self.client.session)

        response = self.client.post(self.logout_url)
        self.assertRedirects(response, reverse('app:question_list'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_navigation_displays_anonymous_links(self):
        response = self.client.get(reverse('app:question_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Log in')
        self.assertContains(response, 'Register')
        self.assertNotContains(response, 'Log out')

    def test_navigation_displays_authenticated_links(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('app:question_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.username)
        self.assertContains(response, 'Log out')
        self.assertNotContains(response, 'Log in')

    def test_registration_flow_unaffected(self):
        register_url = reverse('app:register')
        reg_data = {
            'username': 'seconduser',
            'email': 'second@example.com',
            'password1': 'StrongSecret1234!',
            'password2': 'StrongSecret1234!',
        }
        response = self.client.post(register_url, reg_data)
        self.assertEqual(User.objects.filter(username='seconduser').count(), 1)
        self.assertRedirects(response, reverse('app:question_list'))
