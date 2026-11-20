"""项目根路由（URL 总入口）。

文件职责：
    把浏览器地址栏里的 URL 映射到对应的处理函数（视图）。本文件只做两件事：
    一是把 /admin/ 交给 Django 自带后台，二是把其余所有地址交给业务应用 app01.urls。
    可以理解为“前台总服务台”：先看是不是去后台，不是就全部转给业务部门。

项目位置：
    d:\\ems\\program\\hrms\\urls.py，由 settings.py 的 ROOT_URLCONF='hrms.urls' 指定，
    是请求进入 Django 后的第一站。

对应任务书：
    T1 环境与初始化（URL 路由骨架）；
    T4 登录、T5 RBAC、T6 考勤、T7 薪资、T8 公告、T9 AJAX、T10 图表（具体业务路由都在 app01/urls.py）；
    T13 安全（/admin/ 入口与媒体文件在开发环境下的受控暴露）。

# 讲解要点：
# 1. 浏览器输入 127.0.0.1:8000/ 会进入首页概览；输入 /login/ 进入登录页；
#    输入 /admin/ 进入 Django 自带后台（需要 is_staff 账号）——这些地址分流就发生在本文件。
# 2. 侧边栏的“部门管理 / 员工管理 / 考勤管理 / 薪资管理 / 公告管理 / 任务管理 / 用户授权 / 角色权限”
#    全部由 app01/urls.py 负责，本文件用 include() 把 / 开头的请求整体转交过去。
# 3. 员工列表页里的头像图片地址形如 /media/avatar/2026/03/xxx.jpg，
#    开发环境下由本文件末尾的 static() 路由提供访问；部署时通常改由 Nginx 提供。
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app01.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
