from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.forms import UserCreationForm,AuthenticationForm
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
from .models import Profile, Blog, Comment,Message,models,Friend
from .forms import AvatarUploadForm, BlogForm, CommentForm
import random
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
    """
    GET: 显示注册页
    POST: 验证并保存用户（包含 email），注册成功后自动登录并跳转主页
    """
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # 认证并登录
            user = authenticate(request, username=form.cleaned_data["username"], password=form.cleaned_data["password1"])
            if user:
                login(request, user)
                messages.success(request, "注册并登录成功。")
                return redirect("home")
            else:
                messages.warning(request, "注册成功，但自动登录失败，请手动登录。")
                return redirect("login")
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f"{field}: {err}")
    else:
        form = RegistrationForm()
    return render(request, "register.html", {"form": form})

def login_view(request):
    """
    GET: 显示登录页
    POST: 使用 AuthenticationForm 登录
    """
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "登录成功。")
            next_url = request.GET.get("next") or request.POST.get("next")
            if next_url:
                return redirect(next_url)
            return redirect("home")
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f"{field}: {err}")
    else:
        form = AuthenticationForm()
    return render(request, "login.html", {"form": form})

def logout_view(request):
    logout(request)
    messages.info(request, "已退出登录。")
    return redirect("home")

@login_required(login_url="login")
def home_view(request):
    return render(request, "home.html", {"user": request.user})
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
    return ''.join(str(random.randint(0,9)) for _ in range(length))

def send_login_code_view(request):
    """
    POST: 接收邮箱，验证用户存在后发送验证码，验证码缓存 5 分钟。
    简单频率限制：每 60 秒只能请求一次
    """
    if request.method != "POST":
        return redirect("email_login")
    form = EmailCodeSendForm(request.POST)
    if not form.is_valid():
        for f, errs in form.errors.items():
            for e in errs:
                messages.error(request, f"{f}: {e}")
        return redirect("email_login")

    email = form.cleaned_data["email"].lower()
    user = User.objects.filter(email__iexact=email).first()
    if not user:
        messages.error(request, "该邮箱未注册。")
        return redirect("email_login")

    cooldown_key = f"login_code_cooldown_{email}"
    if cache.get(cooldown_key):
        messages.error(request, "请稍后再请求验证码（间隔 60 秒）。")
        return redirect("email_login")

    code = _generate_code(6)
    code_key = f"login_code_{email}"
    # 保存 5 分钟
    cache.set(code_key, code, 300)
    # 60 秒冷却
    cache.set(cooldown_key, True, 60)

    # 发送邮件
    subject = "登录验证码"
    message = f"您本次登录的验证码为：{code}，5 分钟内有效。若非本人操作请忽略。"
    try:
        send_mail(subject, message, None, [email], fail_silently=False)
        request.session['email_for_login'] = email
        messages.success(request, "验证码已发送，请检查邮箱（包括垃圾箱）。")
    except Exception as e:
        messages.error(request, f"发送邮件失败：{e}")
        # 清理缓存以便重试
        cache.delete(code_key)
        cache.delete(cooldown_key)
        request.session.pop('email_for_login', None)

    return redirect("email_login")

def email_login_view(request):
    """
    GET: 显示邮箱验证码登录页（包含发送验证码的表单）
    POST: 验证邮箱+验证码，成功则直接 login 并跳转主页
    """
    if request.method == "POST":
        form = EmailCodeLoginForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"].strip()
            email = request.session.get('email_for_login')
            if not email:
                messages.error(request, "未检测到要登录的邮箱，请先发送验证码。")
                return redirect("email_login")
            code_key = f"login_code_{email}"
            cached = cache.get(code_key)
            if not cached:
                messages.error(request, "验证码不存在或已过期，请重新发送。")
                return redirect("email_login")
            if cached != code:
                messages.error(request, "验证码错误。")
                return redirect("email_login")
            user = User.objects.filter(email__iexact=email).first()
            if not user:
                messages.error(request, "对应用户不存在。")
                return redirect("email_login")
            # 清除验证码以防重放
            cache.delete(code_key)
            request.session.pop('email_for_login', None)
            # 直接登录用户（设置 backend）
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            messages.success(request, "登录成功。")
            return redirect("home")
        else:
            for f, errs in form.errors.items():
                for e in errs:
                    messages.error(request, f"{f}: {e}")
            return redirect("email_login")
    else:
        send_form = EmailCodeSendForm()
        login_form = EmailCodeLoginForm()
        session_email = request.session.get('email_for_login')
        return render(request, "login_email.html", {"send_form": send_form, "login_form": login_form,"session_email": session_email})


# 头像上传视图
@login_required(login_url="login")
def upload_avatar_view(request):
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


# 博客相关视图
@login_required(login_url="login")
def create_blog_view(request):
    if request.method == 'POST':
        form = BlogForm(request.POST)
        if form.is_valid():
            blog = form.save(commit=False)
            blog.author = request.user
            blog.save()
            messages.success(request, "博客发布成功")
            return redirect('home')
    else:
        form = BlogForm()
    return render(request, 'create_blog.html', {'form': form})


def blog_detail_view(request, blog_id):
    blog = get_object_or_404(Blog, id=blog_id)
    comments = blog.comments.filter(parent=None)  # 只获取顶级评论
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid() and request.user.is_authenticated:
            comment = form.save(commit=False)
            comment.blog = blog
            comment.author = request.user
            parent_id = form.cleaned_data.get('parent_id')
            if parent_id:
                parent_comment = Comment.objects.get(id=parent_id)
                comment.parent = parent_comment
            comment.save()
            return redirect('blog_detail', blog_id=blog.id)
    else:
        form = CommentForm()
    return render(request, 'blog_detail.html', {
        'blog': blog,
        'comments': comments,
        'form': form
    })


# 相亲盲盒视图
@login_required(login_url="login")
def blind_date_view(request):
    # 排除当前用户的随机用户
    other_users = User.objects.exclude(id=request.user.id)
    if other_users.exists():
        random_user = random.choice(other_users)
        # 获取用户昵称，没有则用用户名
        profile = getattr(random_user, 'profile', None)
        nickname = profile.nickname if profile and profile.nickname else random_user.username
        avatar = profile.avatar if profile and profile.avatar else None
    else:
        random_user = None
        nickname = None
        avatar = None

    return render(request, 'blind_date.html', {
        'random_user': random_user,
        'nickname': nickname,
        'avatar': avatar
    })


# 更新主页视图，添加博客列表
@login_required(login_url="login")
def home_view(request):
    blogs = Blog.objects.all()  # 获取所有博客
    return render(request, "home.html", {
        "user": request.user,
        "blogs": blogs
    })


# 个人资料编辑视图
@login_required(login_url="login")
def edit_profile_view(request):
    # 自动为当前用户创建/获取个人资料（首次访问自动生成空资料）
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # 1. 获取表单数据（带必填验证）
        nickname = request.POST.get('nickname', '').strip()
        age = request.POST.get('age')
        gender = request.POST.get('gender', '').strip()

        # 必填项验证
        if not nickname or not age or not gender:
            messages.error(request, "昵称、年龄、性别为必填项！")
            return redirect('edit_profile')

        # 2. 保存基础信息
        profile.nickname = nickname
        profile.age = age
        profile.gender = gender
        profile.height = request.POST.get('height') if request.POST.get('height') else None
        profile.weight = request.POST.get('weight') if request.POST.get('weight') else None
        profile.hobbies = request.POST.get('hobbies', '').strip()

        # 3. 保存头像（如有上传）
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']

        # 4. 提交到数据库
        profile.save()
        messages.success(request, "个人信息保存成功！")
        return redirect('home')  # 保存后返回主页

    # GET请求：渲染填写页面
    return render(request, 'edit_profile.html', {'profile': profile})

# 私信列表视图
@login_required(login_url="login")
def messages_list_view(request):
    # 获取所有有过对话的用户
    sent_messages = Message.objects.filter(sender=request.user).values('receiver').distinct()
    received_messages = Message.objects.filter(receiver=request.user).values('sender').distinct()

    user_ids = set()
    for msg in sent_messages:
        user_ids.add(msg['receiver'])
    for msg in received_messages:
        user_ids.add(msg['sender'])

    chat_users = User.objects.filter(id__in=user_ids)
    return render(request, 'messages_list.html', {'chat_users': chat_users})


# 私信详情视图
@login_required(login_url="login")
def message_detail_view(request, user_id):
    other_user = get_object_or_404(User, id=user_id)

    # 标记消息为已读
    Message.objects.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)

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

    # 非好友限制：只允许发送2条消息
    message_limit = 2
    sent_count = 0
    if not is_friend:
        sent_count = Message.objects.filter(sender=request.user, receiver=other_user).count()
        has_replied = Message.objects.filter(sender=other_user, receiver=request.user).exists()

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            # 检查是否可以发送消息
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


# 添加好友视图
@login_required(login_url="login")
def add_friend_view(request, user_id):
    other_user = get_object_or_404(User, id=user_id)

    # 检查是否已经是好友或已发送请求
    if Friend.objects.filter(from_user=request.user, to_user=other_user).exists():
        messages.info(request, "已发送好友请求")
        return redirect('blind_date')

    Friend.objects.create(from_user=request.user, to_user=other_user)
    messages.success(request, "好友请求已发送")
    return redirect('blind_date')


# 处理好友请求
@login_required(login_url="login")
def handle_friend_request_view(request, request_id, action):
    friend_request = get_object_or_404(Friend, id=request_id, to_user=request.user)

    if action == 'accept':
        friend_request.status = 'accepted'
        friend_request.save()
        messages.success(request, "已接受好友请求")
    elif action == 'reject':
        friend_request.delete()
        messages.info(request, "已拒绝好友请求")

    return redirect('friend_requests')


# 好友请求列表
@login_required(login_url="login")
def friend_requests_view(request):
    requests = Friend.objects.filter(to_user=request.user, status='pending')
    return render(request, 'friend_requests.html', {'requests': requests})


# 更新相亲盲盒视图，显示更多个人信息
@login_required(login_url="login")
def blind_date_view(request):
    # 排除当前用户的随机用户
    other_users = User.objects.exclude(id=request.user.id)
    if other_users.exists():
        random_user = random.choice(other_users)
        # 获取用户资料
        profile = getattr(random_user, 'profile', None)
        nickname = profile.nickname if profile and profile.nickname else random_user.username
        avatar = profile.avatar if profile and profile.avatar else None

        # 个人信息
        age = profile.age if profile and profile.age else "未填写"
        gender = dict(Profile.GENDER_CHOICES).get(profile.gender, "未填写") if profile else "未填写"
        height = f"{profile.height}cm" if profile and profile.height else "未填写"
        weight = f"{profile.weight}kg" if profile and profile.weight else "未填写"
        hobbies = profile.hobbies if profile and profile.hobbies else "未填写"
    else:
        random_user = None
        nickname = None
        avatar = None
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


# 更新主页视图，添加私信入口
@login_required(login_url="login")
def home_view(request):
    blogs = Blog.objects.all().order_by('-created_at')
    # 获取未读消息数量
    unread_count = Message.objects.filter(receiver=request.user, is_read=False).count()
    # 获取未处理的好友请求数量
    friend_request_count = Friend.objects.filter(to_user=request.user, status='pending').count()

    return render(request, "home.html", {
        "user": request.user,
        "blogs": blogs,
        "unread_count": unread_count,
        "friend_request_count": friend_request_count
    })