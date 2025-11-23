from django import forms
from .models import Profile, Blog, Comment


class AvatarUploadForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar', 'nickname']


class BlogForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = ['title', 'content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5}),
        }


class CommentForm(forms.ModelForm):
    parent_id = forms.IntegerField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = Comment
        fields = ['content', 'parent_id']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 2, 'placeholder': '写下你的评论...'}),
        }