"""表单定义：统一使用 ModelForm 完成数据校验与渲染。

文件职责：
    表单层负责“接收用户输入 → 清洗/校验 → 报错或返回干净数据”。
    ModelForm 是 Django 的“模型表单”：它以某个 Model 为蓝本，自动生成对应字段的输入控件，
    并自动复用模型字段上的校验规则（如 max_length、unique、正则），不用手写一堆 input。
    页面上的新增/编辑表单、登录表单、用户授权表单都来自本文件。

项目位置：
    d:\\ems\\program\\app01\\forms.py，属于业务应用 app01；
    views/ 下的视图在处理 POST 请求时实例化这些表单，templates/ 下的模板用 {{ form }} 渲染控件。

对应任务书：
    T2 部门（DepartmentForm）；T3 员工（EmployeeForm 的姓名/年龄/手机号校验）；
    T4 登录（LoginForm 与验证码收尾）；T5 RBAC（UserRoleForm、RoleForm）；
    T6 考勤（AttendanceForm，禁止手填状态）；T7 薪资（SalaryForm，配合 commit=False 自动算 total）；
    T8 公告（AnnouncementForm）；T9 AJAX 任务（TaskForm，错误以 JSON 回显）；
    T13 安全（所有 POST 表单都依赖 CSRF 中间件校验 token）。

# 讲解要点：
# 1. 打开登录页 /login/，三个输入框（用户名、密码、验证码）都带 Bootstrap 的圆角样式和占位提示，
#    验证码图片点一下会刷新——控件样式来自 LoginForm 里 widget attrs 的 'class': 'form-control'，
#    验证码统一转大写再比较来自 clean_captcha()。
# 2. 打开“部门管理 → 新增部门”或“员工管理 → 新增员工”，所有输入框/下拉框/文件框都长得一样整齐，
#    这就是 BootstrapFormMixin._apply_bootstrap() 遍历字段统一加 form-control 的效果；
#    留空或格式错误时输入框变红、下方出现红字，是 ModelForm 校验 + 模板里的 errors 显示。
# 3. 员工表单页里，姓名要求 2~20 字、年龄 18~65、手机号 11 位、部门下拉默认显示“请选择部门”、
#    日期用日历控件、上班/下班用时间控件——分别对应 EmployeeForm 的 clean_name / clean_age /
#    clean_phone、__init__ 里设置的 empty_label 和 input_formats。
# 4. 薪资表单页看不到“实发工资”输入框，因为模型里 total 是 editable=False；
#    保存时视图用 commit=False 先不写库、算完 total 再保存。系统管理“用户授权”页的角色是一排复选框，
#    对应 UserRoleForm 的 ModelMultipleChoiceField + CheckboxSelectMultiple。
"""
from django import forms

from .models import (
    Announcement,
    Attendance,
    Department,
    Employee,
    Role,
    Salary,
    Task,
    User,
)


class BootstrapFormMixin:

    def _apply_bootstrap(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect)):
                continue
            if isinstance(widget, forms.FileInput):
                widget.attrs.setdefault('class', 'form-control')
                continue
            css = widget.attrs.get('class', '')
            widget.attrs['class'] = f'form-control {css}'.strip()


class LoginForm(forms.Form):

    username = forms.CharField(
        max_length=150, label='用户名',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': '请输入用户名', 'autofocus': True,
        }),
    )
    password = forms.CharField(
        label='密码',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 'placeholder': '请输入密码',
        }),
    )
    captcha = forms.CharField(
        max_length=4, label='验证码',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': '请输入图片验证码',
            'autocomplete': 'off',
        }),
    )

    def clean_captcha(self):
        return self.cleaned_data['captcha'].strip().upper()


class DepartmentForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:
        model = Department
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': '请输入部门名称'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': '部门职责简述'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()


class EmployeeForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:
        model = Employee
        fields = [
            'name', 'age', 'gender', 'balance', 'hire_date',
            'phone', 'depart', 'avatar',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': '2~20 个字符'}),
            'age': forms.NumberInput(attrs={'min': 18, 'max': 65}),
            'gender': forms.Select(),
            'balance': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'hire_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'phone': forms.TextInput(attrs={'placeholder': '11 位手机号', 'maxlength': 11}),
            'depart': forms.Select(),
            'avatar': forms.FileInput(attrs={'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hire_date'].input_formats = ['%Y-%m-%d']
        self.fields['depart'].empty_label = '请选择部门'
        self._apply_bootstrap()

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if not 2 <= len(name) <= 20:
            raise forms.ValidationError('姓名长度需在 2~20 个字符之间')
        return name

    def clean_age(self):
        age = self.cleaned_data['age']
        if not 18 <= age <= 65:
            raise forms.ValidationError('年龄必须在 18~65 岁之间')
        return age

    def clean_phone(self):
        import re

        phone = self.cleaned_data['phone'].strip()
        if not re.match(r'^1[3-9]\d{9}$', phone):
            raise forms.ValidationError('手机号格式不正确')
        return phone


class AttendanceForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:
        model = Attendance
        fields = ['employee', 'date', 'clock_in', 'clock_out', 'remark']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'clock_in': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
            'clock_out': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
            'remark': forms.TextInput(attrs={'placeholder': '可选'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].input_formats = ['%Y-%m-%d']
        for name in ('clock_in', 'clock_out'):
            self.fields[name].input_formats = ['%H:%M', '%H:%M:%S']
            self.fields[name].required = True
            self.fields[name].help_text = '上班时间 09:00，下班时间 18:00'
        self.fields['employee'].empty_label = '请选择员工'
        self._apply_bootstrap()

    def clean(self):
        cleaned = super().clean()
        clock_in = cleaned.get('clock_in')
        clock_out = cleaned.get('clock_out')
        if clock_in and clock_out and clock_out <= clock_in:
            raise forms.ValidationError('下班时间必须晚于上班时间')
        return cleaned


class SalaryForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:
        model = Salary
        fields = ['employee', 'month', 'base_salary', 'bonus', 'deduction']
        widgets = {
            'month': forms.TextInput(attrs={'type': 'month', 'placeholder': '2026-03'}),
            'base_salary': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'bonus': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'deduction': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].empty_label = '请选择员工'
        self._apply_bootstrap()


class AnnouncementForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:
        model = Announcement
        fields = ['title', 'content', 'is_top']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': '公告标题'}),
            'content': forms.Textarea(attrs={'rows': 6, 'placeholder': '公告正文'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()


class TaskForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:
        model = Task
        fields = ['level', 'title', 'detail', 'owner']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': '任务标题'}),
            'detail': forms.Textarea(attrs={'rows': 3, 'placeholder': '任务详情'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['owner'].empty_label = '请选择负责人'
        self._apply_bootstrap()


class UserRoleForm(BootstrapFormMixin, forms.ModelForm):

    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='角色',
    )

    class Meta:
        model = User
        fields = [
            'last_name', 'first_name', 'phone', 'depart',
            'is_active', 'is_super_admin', 'roles',
        ]
        labels = {
            'last_name': '姓',
            'first_name': '名',
            'is_active': '账号启用',
            'is_super_admin': '超级管理员标识',
        }
        widgets = {
            'phone': forms.TextInput(attrs={'placeholder': '11 位手机号'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['depart'].empty_label = '未分配部门'
        self._apply_bootstrap()


class RoleForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:
        model = Role
        fields = ['name', 'code', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': '角色名称，例如：人事专员'}),
            'code': forms.TextInput(attrs={'placeholder': '角色编码，例如：hr_staff'}),
            'description': forms.TextInput(attrs={'placeholder': '角色职责简述'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()
