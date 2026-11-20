"""应用配置（app01 的“身份证”）。

文件职责：
    Django 里每个应用都可以有一个 AppConfig 子类，用来声明应用名称、默认主键类型、
    后台显示名等元信息。Django 启动时会自动读取它，用来识别 app01 这个应用。
    本文件不做业务逻辑，只负责“自我介绍”。

项目位置：
    d:\\ems\\program\\app01\\apps.py，属于业务应用 app01；
    settings.py 的 INSTALLED_APPS 里只写了 'app01'，Django 会自动找到本文件的 App01Config。

对应任务书：
    T1 环境与初始化（应用注册与项目骨架）；
    T5 RBAC（应用内的用户/角色/权限模型依赖该应用被正确加载）。

# 讲解要点：
# 1. 登录后打开右上角菜单的“Django 后台”（/admin/），首页会按应用分组列出数据表，
#    其中一组显示中文名“企业员工管理”，而不是英文 app01——这就是 verbose_name 的效果。
# 2. 应用能被正常加载，页面上的部门、员工、考勤等模型和路由才存在；
#    如果 INSTALLED_APPS 里漏写 'app01'，打开首页会直接报错、侧边栏也没有这些菜单。
# 3. default_auto_field 指定主键类型为 BigAutoField（64 位自增），
#    列表页每条记录的隐藏主键就是它，避免数据量大时整型溢出。
"""
from django.apps import AppConfig


class App01Config(AppConfig):

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app01'
    verbose_name = '企业员工管理'
