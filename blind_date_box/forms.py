# forms.py
from django import forms
from .models import Profile, Blog, Comment


class AvatarUploadForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar', 'nickname']


class BlogForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = ['title', 'content', 'image']  # 添加image字段
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '请输入博客标题...'
            }),
            'content': forms.Textarea(attrs={'rows': 5, 'placeholder': '请输入博客内容...'}),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-file',
                'accept': 'image/*'
            })
        }
        labels = {
            'title': '标题',
            'content': '内容',
            'image': '博客图片'
        }


class CommentForm(forms.ModelForm):
    parent_id = forms.IntegerField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = Comment
        fields = ['content', 'parent_id']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 2, 'placeholder': '写下你的评论...'}),
        }