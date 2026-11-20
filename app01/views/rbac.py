"""系统管理视图：超级管理员的用户授权、角色与权限分配。（对应任务书 T5 RBAC 权限管理）

RBAC = Role-Based Access Control（基于角色的访问控制）：用户不直接拥有权限，
而是先绑定「角色」，角色再绑定「权限」。本文件负责这套关系的后台维护：
- 用户授权：给某个账号分配角色、所属部门和启用状态；
- 角色管理：新增/编辑角色，并为角色勾选权限；
- 删除保护：内置角色、以及已分配给用户的角色都不允许删除。
"""

# 讲解要点（结合浏览器里看到的页面效果）：
# 1. 进入「系统管理 → 用户授权」，列表每行显示账号、部门、角色标签；在搜索框输入姓名或手机号，
#    列表即时过滤——对应 rbac_user_list 里的 Q(username__icontains=...) 多字段「或」查询与 paginate。
# 2. 点某行「分配角色」进入表单，勾选「部门管理员」保存后回到列表，该用户角色标签立刻变化——
#    对应 rbac_user_edit 里 UserRoleForm(instance=target).save()，ModelForm 会自动保存多对多角色。
# 3. 打开「角色管理」，每行显示「权限数量」和「使用人数」；点编辑后权限复选框按「部门/员工/考勤…」
#    分块排列，角色已有权限默认勾上——对应 annotate(user_count=Count('users', distinct=True))、
#    _permission_groups() 分组和 selected_ids 回填。
# 4. 删除「普通员工」这种内置角色时页面提示「系统内置角色不允许删除」；删除已有人使用的角色时提示
#    「请先解除分配」——对应 rbac_role_delete 里的 BUILTIN_ROLE_CODES 和 role.users.exists() 判断。

import logging

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from app01.forms import RoleForm, UserRoleForm
from app01.middleware.permission import require_perm
from app01.models import Permission, Role, User
from app01.utils.pagination import paginate

logger = logging.getLogger('app01')

# 系统内置角色编码，禁止删除，避免破坏权限体系
BUILTIN_ROLE_CODES = ('super_admin', 'dept_admin', 'employee')

MODULE_ORDER = ['部门', '员工', '考勤', '薪资', '公告', '任务', '统计', '系统']


def _permission_groups():
    permissions = list(Permission.objects.all())

    def sort_key(item):
        index = MODULE_ORDER.index(item.module) if item.module in MODULE_ORDER else len(MODULE_ORDER)
        return index, item.code

    permissions.sort(key=sort_key)
    groups = []
    for permission in permissions:
        if not groups or groups[-1]['module'] != permission.module:
            groups.append({'module': permission.module, 'permissions': []})
        groups[-1]['permissions'].append(permission)
    return groups


@require_perm('rbac:view')
def rbac_user_list(request):
    keyword = request.GET.get('q', '').strip()
    queryset = (
        User.objects.select_related('depart')
        .prefetch_related('roles')
        .order_by('id')
    )
    if keyword:
        queryset = queryset.filter(
            Q(username__icontains=keyword)
            | Q(last_name__icontains=keyword)
            | Q(first_name__icontains=keyword)
            | Q(phone__icontains=keyword)
        )

    page_obj, query_string = paginate(request, queryset, per_page=10)
    return render(
        request,
        'app01/rbac_user_list.html',
        {
            'page_obj': page_obj,
            'query_string': query_string,
            'keyword': keyword,
        },
    )


@require_perm('rbac:manage')
def rbac_user_edit(request, pk):
    target = get_object_or_404(
        User.objects.select_related('depart').prefetch_related('roles'), pk=pk
    )
    form = UserRoleForm(request.POST or None, instance=target)
    if request.method == 'POST' and form.is_valid():
        form.save()
        logger.info('用户授权更新：%s', target.username)
        messages.success(request, f'用户「{target.username}」角色分配已更新')
        return redirect('rbac_user_list')
    return render(
        request,
        'app01/rbac_user_form.html',
        {'form': form, 'target': target, 'title': '分配角色'},
    )


@require_perm('rbac:view')
def rbac_role_list(request):
    roles = (
        Role.objects.prefetch_related('permissions')
        .annotate(user_count=Count('users', distinct=True))
        .order_by('id')
    )
    return render(
        request,
        'app01/rbac_role_list.html',
        {'roles': roles},
    )


def _save_role_with_permissions(request, role=None):
    form = RoleForm(request.POST or None, instance=role)
    selected_ids = set()
    if role:
        selected_ids = set(role.permissions.values_list('id', flat=True))

    if request.method == 'POST':
        selected_ids = {
            int(value) for value in request.POST.getlist('permissions') if value.isdigit()
        }
        if form.is_valid():
            saved_role = form.save()
            saved_role.permissions.set(Permission.objects.filter(id__in=selected_ids))
            logger.info(
                '角色权限更新：%s（%s 项权限）', saved_role.name, len(selected_ids)
            )
            messages.success(request, f'角色「{saved_role.name}」保存成功')
            return redirect('rbac_role_list')

    return render(
        request,
        'app01/rbac_role_form.html',
        {
            'form': form,
            'role': role,
            'permission_groups': _permission_groups(),
            'selected_ids': selected_ids,
            'title': '编辑角色' if role else '新增角色',
        },
    )


@require_perm('rbac:manage')
def rbac_role_add(request):
    return _save_role_with_permissions(request)


@require_perm('rbac:manage')
def rbac_role_edit(request, pk):
    role = get_object_or_404(
        Role.objects.prefetch_related('permissions'), pk=pk
    )
    return _save_role_with_permissions(request, role)


@require_perm('rbac:manage')
def rbac_role_delete(request, pk):
    role = get_object_or_404(Role, pk=pk)
    if request.method != 'POST':
        messages.error(request, '删除操作必须通过 POST 提交')
        return redirect('rbac_role_list')

    if role.code in BUILTIN_ROLE_CODES:
        messages.error(request, '系统内置角色不允许删除')
    elif role.users.exists():
        messages.error(request, '该角色已分配给用户，请先解除分配再删除')
    else:
        role.delete()
        messages.success(request, '角色删除成功')
    return redirect('rbac_role_list')
