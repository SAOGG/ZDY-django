from django.shortcuts import render,redirect
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
