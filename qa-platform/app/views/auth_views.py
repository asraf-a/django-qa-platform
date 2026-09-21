from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView

from app.forms import RegistrationForm

User = get_user_model()


class RegisterView(CreateView):
    model = User
    form_class = RegistrationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('app:question_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(
            self.request,
            f"Welcome to Q&A Platform, {self.object.username}! Your account has been created."
        )
        return response


class UserLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    pass
