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
    path('upload-avatar/', views.upload_avatar_view, name='upload_avatar'),
    path('create-blog/', views.create_blog_view, name='create_blog'),
    path('blog/<uuid:blog_id>/', views.blog_detail_view, name='blog_detail'),
    path('blind-date/', views.blind_date_view, name='blind_date'),
]
# 开发环境下提供媒体文件访问
#if settings.DEBUG:
   # urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)