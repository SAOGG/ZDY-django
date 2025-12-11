# models.py
from django.db import models
from django.contrib.auth.models import User
import uuid


class Profile(models.Model):
    GENDER_CHOICES = (
        ('male', '男'),
        ('female', '女'),
        ('other', '其他'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    nickname = models.CharField(max_length=100, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    height = models.PositiveIntegerField(blank=True, null=True, help_text="身高(cm)")
    weight = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True, help_text="体重(kg)")
    hobbies = models.TextField(blank=True, null=True, help_text="爱好，用逗号分隔")

    def __str__(self):
        return f"{self.user.username}的资料"

    def get_gender_text(self):
        return dict(self.GENDER_CHOICES).get(self.gender, "未填写")


class Blog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blogs')
    title = models.CharField(max_length=200)
    content = models.TextField()
    # 添加图片字段
    image = models.ImageField(upload_to='blog_images/', blank=True, null=True, verbose_name="博客图片")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views = models.PositiveIntegerField(default=0)

    # 如果需要 likes 字段也添加
    likes = models.PositiveIntegerField(default=0)
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Comment(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author.username}的评论"


class Friend(models.Model):
    STATUS_CHOICES = (
        ('pending', '待确认'),
        ('accepted', '已接受'),
    )

    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']