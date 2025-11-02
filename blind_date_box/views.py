from django.shortcuts import render,redirect
from django.contrib.auth.forms import UserCreationForm,AuthenticationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
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
def users_table_view(request):
    User = get_user_model()
    # 使用 values() 减少模板属性访问开销
    users = User.objects.all().values('id', 'username', 'email', 'date_joined', 'is_staff', 'is_active')
    return render(request, 'users_table.html', {'users': users})
@user_passes_test(lambda u: u.is_staff, login_url="login")
def users_table_view(request):
    User = get_user_model()
    users = User.objects.all().values('id', 'username', 'email', 'date_joined', 'is_staff', 'is_active')
    return render(request, 'users_table.html', {'users': users})