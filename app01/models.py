"""数据模型定义：用户、角色、权限、部门、员工、考勤、薪资、公告、任务。

文件   职责：
    用 Python 类描述数据库表结构，是 MTV 架构里的 M（Model，模型层）。
    Django 的 ORM（对象关系映射）会把这里的每个类自动映射成 MySQL 里的一张表，
    把类里的每个字段映射成表的一列，把类的实例映射成表里的一行记录。
    所以我们不写 SQL，直接写 `Employee.objects.filter(...)` 这样的 Python 代码就能增删改查。

项目位置：
    d:\\ems\\program\\app01\\models.py，属于业务应用 app01；数据库表由 migrations 迁移文件生成。
    views/ 下的视图通过 ORM 读写这些模型，templates/ 下的模板再把数据展示成页面。

对应任务书：
    T2 部门管理（Department）；T3 员工管理（Employee）；
    T4 登录与 T5 RBAC（User / Role / Permission，自定义用户模型 + 多对多授权）；
    T6 考勤（Attendance，上下班时间自动算状态）；T7 薪资（Salary，自动算实发工资）；
    T8 公告（Announcement，发布时间与置顶）；T9 AJAX 任务（Task）；
    T11 ORM 优化（相关查询与 select_related 的基础）。

# 讲解要点：
# 1. 打开侧边栏“部门管理 / 员工管理”列表页，能看到部门名称、员工姓名、年龄、性别、手机号、部门、
#    余额、头像和入职日期——这些列就是 Department 与 Employee 里定义的字段；
#    员工表单里“请选择部门”下拉框来自 Employee.depart 这个外键，头像上传来自 avatar 字段。
# 2. 打开“考勤管理”列表页，会看到状态列显示“按时 / 迟到 / 早退 / 缺勤”。这不是人工填的：
#    Attendance.save() 会调用 compute_status()，按 09:00 上班、18:00 下班规则自动算出来；
#    同一员工同一天重复添加会报错，靠的是 employee+date 的唯一约束。
# 3. 打开“薪资管理”列表页，“实发工资”列总是等于“基本工资 + 奖金 - 扣款”，
#    因为 Salary.save() 在保存前自动调用 compute_total()；表单里也不让手填 total（editable=False）。
# 4. 打开“公告管理”列表页，勾选置顶的公告会排在最前面（Meta.ordering 先按 -is_top 再按发布时间倒序），
#    发布时间无需填写，auto_now_add 会自动记录；登录后侧边栏只显示有权限的菜单、用户授权页能勾选角色，
#    对应的是 Permission / Role / User 之间的多对多关系以及 get_permission_codes() 的权限判断。
"""
from datetime import time

from django.contrib.auth.models import AbstractUser
from django.core.validators import (
    MaxValueValidator,
    MinLengthValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models
from django.utils import timezone


class Department(models.Model):

    title = models.CharField(
        max_length=50, unique=True, verbose_name='部门名称',
        validators=[MinLengthValidator(2, message='部门名称至少 2 个字符')],
    )
    description = models.TextField(blank=True, verbose_name='部门描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '部门'
        verbose_name_plural = verbose_name
        ordering = ['id']

    def __str__(self):
        return self.title


class Permission(models.Model):

    code = models.CharField(max_length=50, unique=True, verbose_name='权限编码')
    name = models.CharField(max_length=50, verbose_name='权限名称')
    module = models.CharField(max_length=20, verbose_name='所属模块')

    class Meta:
        verbose_name = '权限'
        verbose_name_plural = verbose_name
        ordering = ['module', 'code']

    def __str__(self):
        return f'{self.name}({self.code})'


class Role(models.Model):

    name = models.CharField(max_length=30, unique=True, verbose_name='角色名称')
    code = models.CharField(max_length=30, unique=True, verbose_name='角色编码')
    description = models.CharField(max_length=200, blank=True, verbose_name='角色描述')
    permissions = models.ManyToManyField(
        Permission, blank=True, related_name='roles', verbose_name='权限',
    )

    class Meta:
        verbose_name = '角色'
        verbose_name_plural = verbose_name
        ordering = ['id']

    def __str__(self):
        return self.name


class User(AbstractUser):

    phone = models.CharField(max_length=11, blank=True, verbose_name='手机号')
    depart = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='users', verbose_name='所属部门',
    )
    roles = models.ManyToManyField(
        Role, blank=True, related_name='users', verbose_name='角色',
    )
    is_super_admin = models.BooleanField(default=False, verbose_name='超级管理员')

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def get_permission_codes(self):
        if not hasattr(self, '_permission_code_cache'):
            if self.is_super_admin or self.is_superuser:
                codes = set(Permission.objects.values_list('code', flat=True))
            elif self.pk:
                codes = set(
                    Permission.objects.filter(roles__users=self)
                    .values_list('code', flat=True)
                    .distinct()
                )
            else:
                codes = set()
            self._permission_code_cache = codes
        return self._permission_code_cache

    def has_perm_code(self, code):
        if self.is_super_admin or self.is_superuser:
            return True
        return code in self.get_permission_codes()

    def has_any_perm(self, codes):
        return any(self.has_perm_code(code) for code in codes)

    @property
    def is_department_admin(self):
        return not (self.is_super_admin or self.is_superuser) and self.has_perm_code(
            'employee:edit'
        )


class Employee(models.Model):

    GENDER_CHOICES = (
        ('male', '男'),
        ('female', '女'),
    )

    name = models.CharField(
        max_length=20, verbose_name='姓名',
        validators=[MinLengthValidator(2, message='姓名长度需在 2~20 个字符之间')],
    )
    age = models.PositiveSmallIntegerField(
        verbose_name='年龄',
        validators=[
            MinValueValidator(18, message='年龄必须在 18~65 岁之间'),
            MaxValueValidator(65, message='年龄必须在 18~65 岁之间'),
        ],
    )
    gender = models.CharField(
        max_length=10, choices=GENDER_CHOICES, default='male', verbose_name='性别',
    )
    balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(0, message='账户余额不能为负数')],
        verbose_name='账户余额',
    )
    hire_date = models.DateField(default=timezone.localdate, verbose_name='入职时间')
    phone = models.CharField(
        max_length=11, unique=True, verbose_name='手机号',
        validators=[RegexValidator(r'^1[3-9]\d{9}$', message='手机号格式不正确')],
    )
    depart = models.ForeignKey(
        Department, on_delete=models.PROTECT,
        related_name='employees', verbose_name='所属部门',
    )
    avatar = models.ImageField(
        upload_to='avatar/%Y/%m/', null=True, blank=True, verbose_name='头像',
    )
    user = models.OneToOneField(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='employee_profile', verbose_name='关联账号',
        help_text='普通员工账号可关联到本人档案，用于只读查看',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '员工'
        verbose_name_plural = verbose_name
        ordering = ['-id']

    def __str__(self):
        return self.name


class Attendance(models.Model):

    STATUS_CHOICES = (
        ('normal', '按时'),
        ('late', '迟到'),
        ('early', '早退'),
        ('absent', '缺勤'),
    )
    WORK_START = time(9, 0)
    WORK_END = time(18, 0)

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE,
        related_name='attendances', verbose_name='员工',
    )
    date = models.DateField(default=timezone.localdate, verbose_name='考勤日期')
    clock_in = models.TimeField(null=True, blank=True, verbose_name='上班时间')
    clock_out = models.TimeField(null=True, blank=True, verbose_name='下班时间')
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='absent',
        editable=False, verbose_name='考勤状态',
    )
    remark = models.CharField(max_length=200, blank=True, verbose_name='备注')

    class Meta:
        verbose_name = '考勤记录'
        verbose_name_plural = verbose_name
        ordering = ['-date', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'date'], name='unique_employee_attendance_date',
            )
        ]

    def __str__(self):
        return f'{self.employee.name} - {self.date}'

    def compute_status(self):
        if self.clock_in is None or self.clock_out is None:
            return 'absent'
        if self.clock_in > self.WORK_START:
            return 'late'
        if self.clock_out < self.WORK_END:
            return 'early'
        return 'normal'

    def save(self, *args, **kwargs):
        self.status = self.compute_status()
        super().save(*args, **kwargs)


class Salary(models.Model):

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE,
        related_name='salaries', verbose_name='员工',
    )
    month = models.CharField(
        max_length=7, verbose_name='月份',
        validators=[RegexValidator(
            r'^\d{4}-(0[1-9]|1[0-2])$', message='月份格式应为 YYYY-MM，例如 2026-03',
        )],
    )
    base_salary = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name='基本工资',
    )
    bonus = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name='奖金',
    )
    deduction = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name='扣款',
    )
    total = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, editable=False, verbose_name='实发工资',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '薪资记录'
        verbose_name_plural = verbose_name
        ordering = ['-month', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'month'], name='unique_employee_salary_month',
            )
        ]

    def __str__(self):
        return f'{self.employee.name} - {self.month}'

    def compute_total(self):
        return (self.base_salary or 0) + (self.bonus or 0) - (self.deduction or 0)

    def save(self, *args, **kwargs):
        self.total = self.compute_total()
        super().save(*args, **kwargs)


class Announcement(models.Model):

    title = models.CharField(max_length=100, verbose_name='标题')
    content = models.TextField(verbose_name='内容')
    publisher = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='announcements', verbose_name='发布人',
    )
    publish_time = models.DateTimeField(auto_now_add=True, verbose_name='发布时间')
    is_top = models.BooleanField(default=False, verbose_name='是否置顶')

    class Meta:
        verbose_name = '公告'
        verbose_name_plural = verbose_name
        ordering = ['-is_top', '-publish_time']

    def __str__(self):
        return self.title


class Task(models.Model):

    LEVEL_CHOICES = (
        ('high', '高'),
        ('middle', '中'),
        ('low', '低'),
    )

    level = models.CharField(
        max_length=10, choices=LEVEL_CHOICES, default='middle', verbose_name='级别',
    )
    title = models.CharField(max_length=50, verbose_name='标题')
    detail = models.TextField(verbose_name='详情')
    owner = models.ForeignKey(
        Employee, on_delete=models.CASCADE,
        related_name='tasks', verbose_name='负责人',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '任务'
        verbose_name_plural = verbose_name
        ordering = ['-id']

    def __str__(self):
        return self.title


class Knowledge(models.Model):
    """AI 制度知识库条目：考勤/报销/请假等公司制度，用于 T3 制度问答。"""

    category = models.CharField(max_length=30, verbose_name='分类', default='制度')
    title = models.CharField(max_length=100, verbose_name='标题')
    content = models.TextField(verbose_name='内容')
    keywords = models.CharField(max_length=200, blank=True, verbose_name='关键词',
                                help_text='用逗号分隔，用于关键词检索匹配')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '制度知识'
        verbose_name_plural = verbose_name
        ordering = ['category', 'id']

    def __str__(self):
        return f'[{self.category}] {self.title}'
