"""视图公共逻辑：数据范围控制与权限辅助。

职责（对应任务书 T3 员工管理、T5 权限控制、T11 ORM 性能优化）：
所有“列表/详情”类视图都从这里拿查询集，保证三种角色的数据边界一致：
  - 超级管理员：全部员工；
  - 部门管理员：仅本部门员工；
  - 普通员工：仅本人档案。
把“数据范围”收敛到一处，避免每个视图各写一套过滤条件导致越权漏洞。

术语：ORM = 用 Python 对象操作数据库；QuerySet = 惰性查询集；N+1 = 循环里逐行
查外键；select_related = 用 JOIN 一次性取回外键，专治 N+1；RBAC = 基于角色的
访问控制（用户 → 角色 → 权限）。
"""

# 讲解要点：
# 1. 页面现象：admin 登录员工列表能看到全公司；manager01 登录后只剩本部门员工，
#    部门下拉框也只有一个选项；staff01 登录后列表里只有自己一行 —— 三种结果
#    都出自本文件 scoped_employees 的三个 return 分支。
# 2. 页面现象：员工列表每行都显示部门名称，但页面并不卡 —— 因为
#    select_related('depart') 让员工和部门在一条 JOIN 查询里一起取回，消除了 N+1。
# 3. 页面现象：普通员工打开考勤、薪资页面同样“只看自己” —— 靠的是
#    scope_related_queryset 用本人档案的 id 去过滤关联表。
# 4. 页面现象：部门管理员若没绑定部门，员工列表是空表而不是全部数据 ——
#    对应 queryset.none() 这个“安全失败”分支。

from app01.models import Employee


def scoped_employees(user):
    queryset = Employee.objects.select_related('depart')
    if user.is_super_admin or user.is_superuser:
        return queryset
    if user.has_perm_code('employee:edit'):
        if not user.depart_id:
            return queryset.none()
        return queryset.filter(depart_id=user.depart_id)
    return queryset.filter(user=user)


def is_department_scoped(user):
    return not (user.is_super_admin or user.is_superuser) and user.has_perm_code(
        'employee:edit'
    )


def scope_related_queryset(user, queryset, employee_field='employee'):
    if user.is_super_admin or user.is_superuser:
        return queryset
    employee_ids = scoped_employees(user).values_list('id', flat=True)
    return queryset.filter(**{f'{employee_field}_id__in': employee_ids})
