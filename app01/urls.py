"""业务路由。

职责（对应任务书 T2 部门管理、T3 员工管理、T4 登录认证、T5 权限控制（RBAC）、
T6 考勤管理、T7 薪资管理、T8 公告管理、T9 任务管理（AJAX）、T10 数据统计可视化）：
把浏览器地址栏里的 URL 分发给 app01/views 下对应的视图函数，是 Django MTV
模式中“哪个网址交给哪个视图”的一层（URLconf）。

术语：MTV = Model 模型 / Template 模板 / View 视图；URLconf 负责 URL 到视图的映射。
"""

# 讲解要点：
# 1. 页面现象：登录后侧边栏点“员工管理”，地址跳到 /employees/ 并显示员工列表 ——
#    就是下面 path('employees/', employee_views.employee_list) 这一行在分发请求。
# 2. 页面现象：未登录直接敲 /employees/ 会跳到 /login/?next=/employees/，
#    因为只有 /login/、/logout/、/captcha/ 等白名单路径免登录。
# 3. 页面现象：员工列表翻页后地址是 /employees/?page=2&q=张，路由仍只匹配
#    '/employees/'，问号后的查询串由视图通过 request.GET 读取。
# 4. 页面现象：部门管理员看不到“系统管理”菜单，硬敲 /system/users/ 会进 403 页 ——
#    菜单靠模板标签隐藏，真正的拦截在各视图的 @require_perm 装饰器。

from django.urls import path

from app01.views import (
    announcement as announcement_views,
    attendance as attendance_views,
    auth as auth_views,
    dashboard as dashboard_views,
    department as department_views,
    employee as employee_views,
    rbac as rbac_views,
    salary as salary_views,
    task as task_views,
    ai as ai_views,
)

urlpatterns = [
    path('', dashboard_views.dashboard, name='dashboard'),
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),
    path('captcha/', auth_views.captcha_view, name='captcha'),

    path('departments/', department_views.department_list, name='department_list'),
    path('departments/add/', department_views.department_add, name='department_add'),
    path('departments/<int:pk>/edit/', department_views.department_edit, name='department_edit'),
    path('departments/<int:pk>/delete/', department_views.department_delete, name='department_delete'),

    path('employees/', employee_views.employee_list, name='employee_list'),
    path('employees/add/', employee_views.employee_add, name='employee_add'),
    path('employees/<int:pk>/edit/', employee_views.employee_edit, name='employee_edit'),
    path('employees/<int:pk>/delete/', employee_views.employee_delete, name='employee_delete'),

    path('attendances/', attendance_views.attendance_list, name='attendance_list'),
    path('attendances/add/', attendance_views.attendance_add, name='attendance_add'),
    path('attendances/<int:pk>/edit/', attendance_views.attendance_edit, name='attendance_edit'),
    path('attendances/<int:pk>/delete/', attendance_views.attendance_delete, name='attendance_delete'),

    path('salaries/', salary_views.salary_list, name='salary_list'),
    path('salaries/add/', salary_views.salary_add, name='salary_add'),
    path('salaries/<int:pk>/edit/', salary_views.salary_edit, name='salary_edit'),
    path('salaries/<int:pk>/delete/', salary_views.salary_delete, name='salary_delete'),

    path('announcements/', announcement_views.announcement_list, name='announcement_list'),
    path('announcements/add/', announcement_views.announcement_add, name='announcement_add'),
    path('announcements/<int:pk>/edit/', announcement_views.announcement_edit, name='announcement_edit'),
    path('announcements/<int:pk>/delete/', announcement_views.announcement_delete, name='announcement_delete'),
    path(
        'announcements/<int:pk>/toggle-top/',
        announcement_views.announcement_toggle_top,
        name='announcement_toggle_top',
    ),

    path('tasks/', task_views.task_list, name='task_list'),
    path('tasks/create/', task_views.task_create_ajax, name='task_create_ajax'),
    path('tasks/<int:pk>/delete/', task_views.task_delete, name='task_delete'),

    path('stats/departments/', dashboard_views.department_chart_data, name='department_chart_data'),
    path('stats/salaries/', dashboard_views.salary_chart_data, name='salary_chart_data'),

    path('system/users/', rbac_views.rbac_user_list, name='rbac_user_list'),
    path('system/users/<int:pk>/roles/', rbac_views.rbac_user_edit, name='rbac_user_edit'),
    path('system/roles/', rbac_views.rbac_role_list, name='rbac_role_list'),
    path('system/roles/add/', rbac_views.rbac_role_add, name='rbac_role_add'),
    path('system/roles/<int:pk>/edit/', rbac_views.rbac_role_edit, name='rbac_role_edit'),
    path('system/roles/<int:pk>/delete/', rbac_views.rbac_role_delete, name='rbac_role_delete'),

    # AI 智能助手（T2~T7）
    path('ai/jd/', ai_views.ai_jd_page, name='ai_jd_page'),
    path('ai/knowledge/', ai_views.ai_knowledge_page, name='ai_knowledge_page'),
    path('ai/chat/', ai_views.ai_chat_floating, name='ai_chat_floating'),
    path('ai/chat/history/', ai_views.ai_chat_history, name='ai_chat_history'),
    path('ai/chat/sse/', ai_views.ai_chat_sse, name='ai_chat_sse'),
    path('ai/jd/generate/', ai_views.jd_generate, name='ai_jd_generate'),
    path('ai/knowledge/ask/', ai_views.knowledge_ask, name='ai_knowledge_ask'),
    path('ai/review/', ai_views.employee_review, name='ai_employee_review'),
]
