"""登录、注销与图片验证码视图。

职责（对应任务书 T4 登录认证，兼顾 T13 安全加固）：
  1. login_view：渲染登录页，校验“用户名 + 密码 + 图片验证码”，成功后建立会话；
  2. logout_view：退出登录并清空 Session；
  3. captcha_view：动态生成 PNG 验证码图片，并把正确答案暂存到 Session。

安全设计：验证码校验后 pop 删除（一次性、防重放）；输入统一 .upper() 实现
不区分大小写；next 参数用 url_has_allowed_host_and_scheme 做白名单校验，防止
开放重定向；@never_cache 禁止浏览器缓存登录页与验证码图片。
"""

# 讲解要点：
# 1. 页面现象：登录页验证码图片点一下就会换成新字符，因为 captcha_view 每次请求
#    都生成新 code、覆盖 Session 答案并返回新 PNG；前端用 ?t=时间戳 绕开缓存。
# 2. 页面现象：验证码输错时页面红字提示“验证码错误或已过期”，即使密码正确也
#    登不进去 —— 代码先比对验证码并 pop 删除，不通过就不会执行 authenticate()。
# 3. 页面现象：验证码字母大小写都能通过 —— 生成端只含大写字符，校验端用 .upper()。
# 4. 页面现象：已登录再访问 /login/ 会直接回首页；未登录访问 /employees/ 会跳到
#    /login/?next=/employees/，登录后自动回到员工列表（由 _safe_next_url 决定）。

import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache

from app01.forms import LoginForm
from app01.utils.captcha import generate_captcha_code, render_captcha_image

logger = logging.getLogger('app01')


def _safe_next_url(request):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return reverse('dashboard')


@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = LoginForm(request.POST or None)
    if request.method == 'POST':
        session_code = request.session.pop('captcha_code', '')
        input_code = request.POST.get('captcha', '').strip().upper()

        if not session_code or input_code != session_code:
            form.add_error('captcha', '验证码错误或已过期，请点击图片刷新')
        elif form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is None:
                form.add_error(None, '用户名或密码错误')
                logger.warning('登录失败：用户名=%s IP=%s', username, request.META.get('REMOTE_ADDR'))
            elif not user.is_active:
                form.add_error(None, '账号已被禁用，请联系管理员')
            else:
                login(request, user)
                logger.info('登录成功：%s', user.username)
                messages.success(request, f'欢迎回来，{user.get_full_name() or user.username}！')
                return redirect(_safe_next_url(request))

    return render(
        request,
        'app01/login.html',
        {'form': form, 'next': request.GET.get('next', '')},
    )


def logout_view(request):
    if request.user.is_authenticated:
        logger.info('注销登录：%s', request.user.username)
    logout(request)
    return redirect('login')


@never_cache
def captcha_view(request):
    code = generate_captcha_code(4)
    request.session['captcha_code'] = code
    image = render_captcha_image(code)
    response = HttpResponse(image, content_type='image/png')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    return response
