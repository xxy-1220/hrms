"""Django 后台注册（便于课程演示时直接查看数据）。

文件职责：
    把 app01 里的模型注册到 Django 自带后台（Admin）。注册后，拥有 is_staff 的账号
    可以在浏览器打开 /admin/，像操作 Excel 一样增删改查部门、员工、考勤等数据，
    不需要写任何前端代码。这里还配置了列表显示哪些列、按什么筛选、能搜索哪些字段。

项目位置：
    d:\\ems\\program\\app01\\admin.py，属于业务应用 app01；
    Django 启动时会自动发现本文件并加载其中的 @admin.register 装饰器。

对应任务书：
    T1 环境与初始化（INSTALLED_APPS 中的 django.contrib.admin）；
    T2~T9（各部门/员工/考勤/薪资/公告/任务模型的后台查看能力）；
    T5 RBAC（用户、角色、权限的后台管理，便于演示权限数据来源）；
    T12 测试与答辩演示（直接查看数据库真实数据）。

# 讲解要点：
# 1. 登录后点击右上角用户下拉菜单里的“Django 后台”，会打开 /admin/ 页面，
#    里面按“部门、员工、考勤记录、薪资记录、公告、任务、用户、角色、权限”分组列出所有表。
#    这些分组就是本文件下面每个 @admin.register(...) 注册出来的。
# 2. 点进“员工”列表，页面顶部有搜索框，右侧有按部门/性别筛选的下拉；
#    列显示姓名、年龄、性别、手机号、部门、入职日期、余额——对应 EmployeeAdmin 的
#    search_fields、list_filter、list_display。
# 3. 点进“用户”编辑页，除了 Django 自带字段，还会多出“扩展信息”一栏（手机号、部门、角色、
#    超级管理员标识），这就是 CustomUserAdmin.fieldsets 追加的部分；
# 4. 点进“角色”编辑页，权限是一个左右穿梭框（filter_horizontal），
#    方便把“员工查看/员工编辑”等权限一次性授给角色，对应 RoleAdmin.filter_horizontal。
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Announcement,
    Attendance,
    Department,
    Employee,
    Knowledge,
    Permission,
    Role,
    Salary,
    Task,
    User,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    fieldsets = UserAdmin.fieldsets + (
        ('扩展信息', {'fields': ('phone', 'depart', 'roles', 'is_super_admin')}),
    )
    list_display = ('username', 'email', 'depart', 'is_super_admin', 'is_staff')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):

    list_display = ('title', 'created_at')
    search_fields = ('title',)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):

    list_display = ('name', 'age', 'gender', 'phone', 'depart', 'hire_date', 'balance')
    list_filter = ('depart', 'gender')
    search_fields = ('name', 'phone')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):

    list_display = ('employee', 'date', 'clock_in', 'clock_out', 'status')
    list_filter = ('status', 'date')


@admin.register(Salary)
class SalaryAdmin(admin.ModelAdmin):

    list_display = ('employee', 'month', 'base_salary', 'bonus', 'deduction', 'total')
    list_filter = ('month',)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):

    list_display = ('title', 'publisher', 'publish_time', 'is_top')
    list_filter = ('is_top',)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):

    list_display = ('title', 'level', 'owner', 'created_at')
    list_filter = ('level',)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):

    list_display = ('name', 'code')
    filter_horizontal = ('permissions',)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):

    list_display = ('code', 'name', 'module')
    list_filter = ('module',)


@admin.register(Knowledge)
class KnowledgeAdmin(admin.ModelAdmin):

    list_display = ('category', 'title', 'created_at')
    list_filter = ('category',)
    search_fields = ('title', 'content', 'keywords')
