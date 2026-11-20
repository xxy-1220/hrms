"""登录拦截中间件：未登录访问受保护页面时自动跳转登录页。

职责（对应任务书 T4 登录认证，涉及 T13 安全加固）：
在“请求进入视图之前”统一检查是否登录；未登录且访问的不是白名单路径时，
直接 302 跳转到 /login/?next=原始地址，避免每个视图重复写 @login_required。
注册位置：hrms/settings.py 的 MIDDLEWARE 列表（LoginRequiredMiddleware）。

术语：中间件 = Django 的请求/响应管道，每个请求依次穿过每一层，适合做全局统一
的事；__init__ 只在启动时执行一次，__call__ 每个请求都会执行。
"""

# 讲解要点：
# 1. 页面现象：未登录直接在地址栏敲 /employees/，页面立刻变成登录页，地址后面
#    多了 ?next=/employees/；登录成功后自动回到员工列表。
# 2. 页面现象：登录页、验证码图片、静态样式都能正常加载，不会被反复跳转 ——
#    因为 is_exempt_path 白名单放行了 /login/、/logout/、/captcha/、/static/、
#    /media/、/admin/，避免“登录页要求先登录”的死循环。
# 3. 页面现象：登录后访问 /admin/ 也能进去（若账号是 staff），说明 /admin/
#    被前缀匹配放行，不和 Django 自带后台的登录机制打架。
# 4. 答辩补充：本中间件只判断“有没有登录”，不判断“有没有权限”；
#    具体权限校验在 middleware/permission.py 的 require_perm 装饰器里做。

from django.conf import settings
from django.shortcuts import redirect

from .permission import is_exempt_path


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated and not is_exempt_path(request.path_info):
            login_url = settings.LOGIN_URL
            next_url = request.get_full_path()
            return redirect(f'{login_url}?next={next_url}')
        return self.get_response(request)
