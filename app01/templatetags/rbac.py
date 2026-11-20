"""模板权限标签：前端按权限隐藏按钮。

职责（对应任务书 T5 权限控制，服务于 T2/T3/T6/T7 等页面的按钮显示）：
在模板里判断“当前用户有没有某个权限”，决定按钮/菜单要不要渲染。
模板用法：{% load rbac %} → {% has_perm_code request.user 'employee:add' as can_add %}
→ {% if can_add %} 显示按钮。
隐藏按钮只是“界面友好”，不是安全边界；真正拦截在视图装饰器 require_perm，
两层必须同时存在。

术语：simple_tag = 自定义模板标签，可接收参数并返回一个值，配合 “as 变量名”
存入模板上下文；filter = 模板过滤器，用 | 调用。
"""

# 讲解要点：
# 1. 页面现象：staff01 登录后员工列表右上角没有“新增员工”按钮，每行也没有
#    “编辑/删除”按钮；admin 登录则全部出现 —— 对应模板里 has_perm_code 判断。
# 2. 页面现象：部门管理员侧边栏少了“部门管理/系统管理” —— base.html 每个菜单项
#    外面都套了 has_perm_code 判断。
# 3. 页面现象：未登录访问登录页不会因标签报错 —— 本文件先判断 user 为空或未认证
#    时直接返回 False，避免对匿名用户调用 user.has_perm_code。
# 4. 页面现象：按钮隐藏后页面仍正常，说明数据范围由视图控制；模板标签只负责
#    “看不看得见”，两者配合才既安全又好用。

from django import template

register = template.Library()


@register.simple_tag
def has_perm_code(user, code):
    if not user or not user.is_authenticated:
        return False
    return user.has_perm_code(code)


@register.simple_tag
def has_any_perm(user, *codes):
    if not user or not user.is_authenticated:
        return False
    return user.has_any_perm(codes)


@register.filter
def get_item(mapping, key):
    if isinstance(mapping, dict):
        return mapping.get(key, '')
    return ''
