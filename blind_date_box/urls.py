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
    path('edit-profile/', views.edit_profile_view, name='edit_profile'),
    path('messages/', views.messages_list_view, name='messages_list'),
    path('messages/<int:user_id>/', views.message_detail_view, name='message_detail'),
    path('add-friend/<int:user_id>/', views.add_friend_view, name='add_friend'),
    path('friend-requests/', views.friend_requests_view, name='friend_requests'),
    path('handle-request/<int:request_id>/<str:action>/', views.handle_friend_request_view, name='handle_friend_request'),
    path('my-blogs/', views.my_blogs_view, name='my_blogs'),
    path('blog/<uuid:blog_id>/edit/', views.edit_blog_view, name='edit_blog'),
    path('blog/<uuid:blog_id>/delete/', views.delete_blog_view, name='delete_blog'),
    path('comments/<uuid:comment_id>/delete/', views.delete_comment_view, name='delete_comment'),
    path('profile/<int:user_id>/', views.user_profile_view, name='user_profile'),
    path('user/<int:user_id>/blogs/', views.search_user_blogs_view, name='search_user_blogs'),
    path('toggle-theme/', views.toggle_theme_view, name='toggle_theme'),
]
# 开发环境下提供媒体文件访问
#if settings.DEBUG:
   # urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)