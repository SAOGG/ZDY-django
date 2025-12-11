# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.files.storage import default_storage
from .models import Profile, Blog, Comment, Message, models, Friend
from .forms import AvatarUploadForm, BlogForm, CommentForm
from django.db.models import Q, Count
import random
# 在 views.py 中添加以下功能

from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Count


# 新增：博客编辑视图
@login_required(login_url="login")
def edit_blog_view(request, blog_id):
    """编辑博客视图"""
    blog = get_object_or_404(Blog, id=blog_id)

    # 检查权限：只有作者可以编辑自己的博客
    if blog.author != request.user:
        messages.error(request, "您没有权限编辑此博客")
        return redirect('blog_detail', blog_id=blog.id)

    if request.method == 'POST':
        form = BlogForm(request.POST, request.FILES, instance=blog)
        if form.is_valid():
            form.save()
            messages.success(request, "博客更新成功")
            return redirect('blog_detail', blog_id=blog.id)
        else:
            handle_form_errors(request, form)
    else:
        form = BlogForm(instance=blog)

    return render(request, 'edit_blog.html', {'form': form, 'blog': blog})


# 新增：删除博客视图
@login_required(login_url="login")
def delete_blog_view(request, blog_id):
    """删除博客视图"""
    blog = get_object_or_404(Blog, id=blog_id)

    # 检查权限：只有作者可以删除自己的博客
    if blog.author != request.user and not request.user.is_staff:
        messages.error(request, "您没有权限删除此博客")
        return redirect('blog_detail', blog_id=blog.id)

    if request.method == 'POST':
        blog.delete()
        messages.success(request, "博客删除成功")
        return redirect('my_blogs')

    return render(request, 'confirm_delete.html', {'object': blog, 'type': '博客'})


# 新增：删除评论视图
@login_required(login_url="login")
def delete_comment_view(request, comment_id):
    """删除评论视图"""
    comment = get_object_or_404(Comment, id=comment_id)

    # 检查权限：评论作者或博客作者或管理员可以删除评论
    if not (comment.author == request.user or
            comment.blog.author == request.user or
            request.user.is_staff):
        return HttpResponseForbidden("您没有权限删除此评论")

    blog_id = comment.blog.id
    comment.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    messages.success(request, "评论删除成功")
    return redirect('blog_detail', blog_id=blog_id)


# 新增：我的博客视图
@login_required(login_url="login")
def my_blogs_view(request):
    """我的博客列表视图"""
    blogs = Blog.objects.filter(author=request.user).order_by('-created_at')

    # 统计信息
    total_blogs = blogs.count()
    total_comments = Comment.objects.filter(blog__author=request.user).count()
    total_views = 0
    for blog in blogs:
        total_views += getattr(blog, 'views', 0)

    return render(request, 'my_blog.html', {
        'blogs': blogs,
        'total_blogs': total_blogs,
        'total_comments': total_comments,
        'total_views': total_views
    })


# 新增：用户详情页视图
def user_profile_view(request, user_id):
    """用户详情页视图"""
    profile_user = get_object_or_404(User, id=user_id)
    profile = getattr(profile_user, 'profile', None)

    # 获取用户的博客
    user_blogs = Blog.objects.filter(author=profile_user).order_by('-created_at')[:5]

    # 检查是否是好友
    is_friend = False
    if request.user.is_authenticated and request.user != profile_user:
        is_friend = Friend.objects.filter(
            (Q(from_user=request.user, to_user=profile_user) |
             Q(from_user=profile_user, to_user=request.user)),
            status='accepted'
        ).exists()

    # 检查是否已发送好友请求
    friend_request_sent = False
    if request.user.is_authenticated:
        friend_request_sent = Friend.objects.filter(
            from_user=request.user,
            to_user=profile_user,
            status='pending'
        ).exists()

    # 用户统计信息
    blog_count = Blog.objects.filter(author=profile_user).count()
    comment_count = Comment.objects.filter(author=profile_user).count()

    return render(request, 'user_profile.html', {
        'profile_user': profile_user,
        'profile': profile,
        'user_blogs': user_blogs,
        'blog_count': blog_count,
        'comment_count': comment_count,
        'is_friend': is_friend,
        'friend_request_sent': friend_request_sent,
        'is_own_profile': request.user == profile_user
    })


# 新增：搜索用户博客视图
@login_required(login_url="login")
def search_user_blogs_view(request, user_id):
    """搜索特定用户的博客"""
    profile_user = get_object_or_404(User, id=user_id)
    search_query = request.GET.get('q', '')

    blogs = Blog.objects.filter(author=profile_user)

    if search_query:
        blogs = blogs.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query)
        )

    blogs = blogs.order_by('-created_at')

    return render(request, 'users_blog.html', {
        'profile_user': profile_user,
        'blogs': blogs,
        'search_query': search_query
    })


# 新增：主题切换视图
def toggle_theme_view(request):
    """切换主题视图"""
    if request.method == 'POST':
        current_theme = request.session.get('theme', 'light')
        new_theme = 'dark' if current_theme == 'light' else 'light'
        request.session['theme'] = new_theme

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'theme': new_theme})

    return JsonResponse({'success': False})


# 通用函数：处理表单错误信息
def handle_form_errors(request, form):
    for field, errors in form.errors.items():
        for err in errors:
            messages.error(request, f"{field}: {err}")


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


def register_view(request):
    """GET: 显示注册页；POST: 验证并保存用户，注册成功后自动登录并跳转主页"""
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user = authenticate(
                request,
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password1"]
            )
            if user:
                login(request, user)
                messages.success(request, "注册并登录成功。")
                return redirect("home")
            else:
                messages.warning(request, "注册成功，但自动登录失败，请手动登录。")
                return redirect("login")
        else:
            handle_form_errors(request, form)
    else:
        form = RegistrationForm()
    return render(request, "register.html", {"form": form})


def login_view(request):
    """GET: 显示登录页；POST: 使用AuthenticationForm登录"""
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "登录成功。")
            next_url = request.GET.get("next") or request.POST.get("next")
            return redirect(next_url) if next_url else redirect("home")
        else:
            handle_form_errors(request, form)
    else:
        form = AuthenticationForm()
    return render(request, "login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "已退出登录。")
    return redirect("home")


@user_passes_test(lambda u: u.is_staff, login_url="login")
def users_table_view(request):
    User = get_user_model()
    users = User.objects.all().values('id', 'username', 'email', 'date_joined', 'is_staff', 'is_active')
    return render(request, 'users_table.html', {'users': users})


class EmailCodeSendForm(forms.Form):
    email = forms.EmailField(required=True)


class EmailCodeLoginForm(forms.Form):
    code = forms.CharField(required=True, max_length=10)


def _generate_code(length=6):
    return ''.join(str(random.randint(0, 9)) for _ in range(length))


def send_login_code_view(request):
    """POST: 接收邮箱，验证用户存在后发送验证码，验证码缓存5分钟，60秒频率限制"""
    if request.method != "POST":
        return redirect("email_login")

    form = EmailCodeSendForm(request.POST)
    if not form.is_valid():
        handle_form_errors(request, form)
        return redirect("email_login")

    email = form.cleaned_data["email"].lower()
    user = User.objects.filter(email__iexact=email).first()
    if not user:
        messages.error(request, "该邮箱未注册。")
        return redirect("email_login")

    cooldown_key = f"login_code_cooldown_{email}"
    if cache.get(cooldown_key):
        messages.error(request, "请稍后再请求验证码（间隔60秒）。")
        return redirect("email_login")

    code = _generate_code(6)
    code_key = f"login_code_{email}"
    cache.set(code_key, code, 300)  # 保存5分钟
    cache.set(cooldown_key, True, 60)  # 60秒冷却

    # 发送邮件
    subject = "登录验证码"
    message = f"您本次登录的验证码为：{code}，5分钟内有效。若非本人操作请忽略。"
    try:
        send_mail(subject, message, None, [email], fail_silently=False)
        request.session['email_for_login'] = email
        messages.success(request, "验证码已发送，请检查邮箱（包括垃圾箱）。")
    except Exception as e:
        messages.error(request, f"发送邮件失败：{e}")
        cache.delete(code_key)
        cache.delete(cooldown_key)
        request.session.pop('email_for_login', None)

    return redirect("email_login")


def email_login_view(request):
    """GET: 显示邮箱验证码登录页；POST: 验证邮箱+验证码并登录"""
    if request.method == "POST":
        form = EmailCodeLoginForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"].strip()
            email = request.session.get('email_for_login')

            if not email:
                messages.error(request, "未检测到要登录的邮箱，请先发送验证码。")
                return redirect("email_login")

            code_key = f"login_code_{email}"
            cached_code = cache.get(code_key)
            if not cached_code:
                messages.error(request, "验证码不存在或已过期，请重新发送。")
                return redirect("email_login")

            if cached_code != code:
                messages.error(request, "验证码错误。")
                return redirect("email_login")

            user = User.objects.filter(email__iexact=email).first()
            if not user:
                messages.error(request, "对应用户不存在。")
                return redirect("email_login")

            # 清除验证码防止重放
            cache.delete(code_key)
            request.session.pop('email_for_login', None)
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            messages.success(request, "登录成功。")
            return redirect("home")
        else:
            handle_form_errors(request, form)
            return redirect("email_login")
    else:
        send_form = EmailCodeSendForm()
        login_form = EmailCodeLoginForm()
        session_email = request.session.get('email_for_login')
        return render(request, "login_email.html", {
            "send_form": send_form,
            "login_form": login_form,
            "session_email": session_email
        })


@login_required(login_url="login")
def upload_avatar_view(request):
    """头像上传视图"""
    profile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = AvatarUploadForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "头像已更新")
            return redirect('home')
    else:
        form = AvatarUploadForm(instance=profile)
    return render(request, 'upload_avatar.html', {'form': form})


@login_required(login_url="login")
def create_blog_view(request):
    """博客创建视图 - 添加图片上传支持"""
    if request.method == 'POST':
        form = BlogForm(request.POST, request.FILES)  # 添加request.FILES以处理图片
        if form.is_valid():
            blog = form.save(commit=False)
            blog.author = request.user
            blog.save()
            messages.success(request, "博客发布成功")
            return redirect('home')
        else:
            handle_form_errors(request, form)
    else:
        form = BlogForm()
    return render(request, 'create_blog.html', {'form': form})


# 在 views.py 中修改 blog_detail_view 函数
def blog_detail_view(request, blog_id):
    """博客详情及评论视图 - 添加图片显示"""
    # 使用 select_related 和 prefetch_related 优化查询性能
    blog = get_object_or_404(Blog.objects.select_related('author'), id=blog_id)

    # 预取评论、回复和相关用户资料
    comments = blog.comments.filter(parent=None).select_related(
        'author',
        'author__profile'  # 预取评论者的资料
    ).prefetch_related(
        'replies__author__profile',  # 预取回复者的资料
        'replies__parent__author__profile'  # 预取被回复者的资料
    ).order_by('created_at')

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid() and request.user.is_authenticated:
            comment = form.save(commit=False)
            comment.blog = blog
            comment.author = request.user
            parent_id = request.POST.get('parent_id')  # 从POST获取parent_id
            if parent_id:
                try:
                    parent_comment = Comment.objects.get(id=parent_id)
                    comment.parent = parent_comment
                except Comment.DoesNotExist:
                    pass
            comment.save()
            messages.success(request, "评论发布成功")
            return redirect('blog_detail', blog_id=blog.id)
        else:
            handle_form_errors(request, form)
    else:
        form = CommentForm()

    return render(request, 'blog_detail.html', {
        'blog': blog,
        'comments': comments,
        'form': form
    })

@login_required(login_url="login")
def blind_date_view(request):
    """相亲盲盒视图，显示随机用户信息"""
    # 排除当前用户的随机用户
    other_users = User.objects.exclude(id=request.user.id)
    if other_users.exists():
        random_user = random.choice(other_users)
        profile = getattr(random_user, 'profile', None)

        # 基础信息
        nickname = profile.nickname if (profile and profile.nickname) else random_user.username
        avatar = profile.avatar if (profile and profile.avatar) else None

        # 详细信息
        age = profile.age if (profile and profile.age) else "未填写"
        gender = dict(Profile.GENDER_CHOICES).get(profile.gender, "未填写") if profile else "未填写"
        height = f"{profile.height}cm" if (profile and profile.height) else "未填写"
        weight = f"{profile.weight}kg" if (profile and profile.weight) else "未填写"
        hobbies = profile.hobbies if (profile and profile.hobbies) else "未填写"
    else:
        random_user = nickname = avatar = None
        age = gender = height = weight = hobbies = None

    return render(request, 'blind_date.html', {
        'random_user': random_user,
        'nickname': nickname,
        'avatar': avatar,
        'age': age,
        'gender': gender,
        'height': height,
        'weight': weight,
        'hobbies': hobbies
    })


@login_required(login_url="login")
def home_view(request):
    """主页视图，包含博客列表、未读消息和好友请求数量，支持搜索和筛选"""
    # 获取查询参数
    search_query = request.GET.get('q', '')
    filter_type = request.GET.get('filter', 'latest')

    # 获取博客列表
    blogs = Blog.objects.all()

    # 搜索功能
    if search_query:
        blogs = blogs.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query)
        )

    # 筛选功能
    if filter_type == 'popular':
        # 按评论数排序（最热）
        blogs = blogs.annotate(comment_count=Count('comments')).order_by('-comment_count', '-created_at')
    elif filter_type == 'following':
        # 只显示关注的人的博客
        # 假设用户有关注功能，这里先实现一个简单的版本
        # 可以根据实际需求调整
        if request.user.is_authenticated:
            # 获取用户的好友列表
            friends = Friend.objects.filter(
                Q(from_user=request.user, status='accepted') |
                Q(to_user=request.user, status='accepted')
            )
            # 提取好友的用户ID
            friend_ids = []
            for friend in friends:
                if friend.from_user == request.user:
                    friend_ids.append(friend.to_user.id)
                else:
                    friend_ids.append(friend.from_user.id)

            blogs = blogs.filter(author_id__in=friend_ids).order_by('-created_at')
        else:
            blogs = Blog.objects.none()
    else:
        # 默认按最新排序
        blogs = blogs.order_by('-created_at')

    # 统计信息
    unread_count = Message.objects.filter(receiver=request.user, is_read=False).count()
    friend_request_count = Friend.objects.filter(to_user=request.user, status='pending').count()

    return render(request, "home.html", {
        "user": request.user,
        "blogs": blogs,
        "unread_count": unread_count,
        "friend_request_count": friend_request_count
    })

@login_required(login_url="login")
def edit_profile_view(request):
    """个人资料编辑视图"""
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # 获取表单数据
        nickname = request.POST.get('nickname', '').strip()
        age = request.POST.get('age')
        gender = request.POST.get('gender', '').strip()

        # 必填项验证
        if not all([nickname, age, gender]):
            messages.error(request, "昵称、年龄、性别为必填项！")
            return redirect('edit_profile')

        # 保存基础信息
        profile.nickname = nickname
        profile.age = age
        profile.gender = gender
        profile.height = request.POST.get('height') or None
        profile.weight = request.POST.get('weight') or None
        profile.hobbies = request.POST.get('hobbies', '').strip()

        # 保存头像（如有上传）
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']

        profile.save()
        messages.success(request, "个人信息保存成功！")
        return redirect('home')

    return render(request, 'edit_profile.html', {'profile': profile})


@login_required(login_url="login")
def messages_list_view(request):
    """私信列表视图，显示所有有过对话的用户"""
    sent_users = Message.objects.filter(sender=request.user).values_list('receiver', flat=True).distinct()
    received_users = Message.objects.filter(receiver=request.user).values_list('sender', flat=True).distinct()
    chat_user_ids = set(sent_users) | set(received_users)
    chat_users = User.objects.filter(id__in=chat_user_ids)

    return render(request, 'messages_list.html', {'chat_users': chat_users})


@login_required(login_url="login")
def message_detail_view(request, user_id):
    """私信详情视图，处理消息发送和显示历史"""
    other_user = get_object_or_404(User, id=user_id)

    # 标记消息为已读
    Message.objects.filter(
        sender=other_user,
        receiver=request.user,
        is_read=False
    ).update(is_read=True)

    # 获取对话历史
    messages = Message.objects.filter(
        models.Q(sender=request.user, receiver=other_user) |
        models.Q(sender=other_user, receiver=request.user)
    ).order_by('created_at')

    # 检查是否是好友
    is_friend = Friend.objects.filter(
        models.Q(from_user=request.user, to_user=other_user, status='accepted') |
        models.Q(from_user=other_user, to_user=request.user, status='accepted')
    ).exists()

    # 非好友消息限制
    message_limit = 2
    sent_count = 0
    if not is_friend:
        sent_count = Message.objects.filter(sender=request.user, receiver=other_user).count()
        has_replied = Message.objects.filter(sender=other_user, receiver=request.user).exists()

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            # 检查发送权限
            if not is_friend and not has_replied and sent_count >= message_limit:
                messages.error(request, "未添加好友，只能发送2条消息，请等待对方回复或添加好友")
                return redirect('message_detail', user_id=other_user.id)

            Message.objects.create(
                sender=request.user,
                receiver=other_user,
                content=content
            )
            return redirect('message_detail', user_id=other_user.id)

    return render(request, 'message_detail.html', {
        'other_user': other_user,
        'messages': messages,
        'is_friend': is_friend,
        'sent_count': sent_count,
        'message_limit': message_limit
    })


@login_required(login_url="login")
def add_friend_view(request, user_id):
    """添加好友视图"""
    other_user = get_object_or_404(User, id=user_id)

    if Friend.objects.filter(from_user=request.user, to_user=other_user).exists():
        messages.info(request, "已发送好友请求")
    else:
        Friend.objects.create(from_user=request.user, to_user=other_user)
        messages.success(request, "好友请求已发送")

    return redirect('blind_date')


@login_required(login_url="login")
def handle_friend_request_view(request, request_id, action):
    """处理好友请求（接受/拒绝）"""
    friend_request = get_object_or_404(Friend, id=request_id, to_user=request.user)

    if action == 'accept':
        friend_request.status = 'accepted'
        friend_request.save()
        messages.success(request, "已接受好友请求")
    elif action == 'reject':
        friend_request.delete()
        messages.info(request, "已拒绝好友请求")

    return redirect('friend_requests')


@login_required(login_url="login")
def friend_requests_view(request):
    """好友请求列表视图"""
    requests = Friend.objects.filter(to_user=request.user, status='pending')
    return render(request, 'friend_requests.html', {'requests': requests})