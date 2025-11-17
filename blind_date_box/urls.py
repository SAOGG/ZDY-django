from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path('users/', views.users_table_view, name='users_table'),
    path("login/email/", views.email_login_view, name="email_login"),
    path("login/email/send_code/", views.send_login_code_view, name="send_login_code"),
]
