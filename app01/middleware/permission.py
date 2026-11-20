"""接口级权限校验装饰器与免登录路径配置。

职责（对应任务书 T5 权限控制，涉及 T13 安全加固）：
  1. EXEMPT_PATHS / is_exempt_path：告诉登录拦截中间件哪些路径不用登录；
  2. require_perm(*codes)：视图装饰器，要求用户具备全部指定权限编码，
     未登录 → 跳登录页；已登录但缺权限 → 渲染 403 页面。
权限编码形如 '模块:动作'，例如 department:view / employee:add / salary:delete。

术语：RBAC = 基于角色的访问控制（用户 → 角色 → 权限），本项目通过 User.roles
得到权限集合后调用 has_perm_code；装饰器 = 给视图套一层“先检查再执行”的包装，
@wraps 用来保留原函数的名字和文档；403 = 已登录但没有权限。
"""

# 讲解要点：
# 1. 页面现象：普通员工手动输入 /departments/，页面显示红色“403 没有访问权限”，
#    下方列出“所需权限：department:view” —— 就是 require_perm 渲染 403.html。
# 2. 页面现象：没登录时敲任何业务地址，先看到登录页而不是 403 —— 装饰器第一个
#    判断就是 is_authenticated，未登录统一跳登录页。
# 3. 页面现象：部门管理员侧边栏没有“系统管理”，硬敲 /system/users/ 也会得到
#    403 —— 菜单隐藏靠模板标签，真正兜底靠这里的装饰器（双保险）。
# 4. 页面现象：登录页、验证码、静态 CSS 都能匿名访问 —— 靠 is_exempt_path 的
#    精确匹配加 startswith 前缀放行；新增免登录接口要同步改这里。

from functools import wraps

from django.shortcuts import redirect, render

EXEMPT_PATHS = (
    '/login/',
    '/logout/',
    '/captcha/',
    # AI 公共接口：免登录也能演示
    '/ai/knowledge/ask/',
    '/ai/jd/generate/',
)


def is_exempt_path(path):
    if path in EXEMPT_PATHS:
        return True
    return (
        path.startswith('/static/')
        or path.startswith('/media/')
        or path.startswith('/admin/')
    )


def require_perm(*codes):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect(f'/login/?next={request.get_full_path()}')
            if not all(user.has_perm_code(code) for code in codes):
                return render(
                    request,
                    'app01/403.html',
                    {'required_codes': codes},
                    status=403,
                )
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
