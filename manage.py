#!/usr/bin/env python
"""Django 命令行管理入口。

文件职责：
    这是整个项目的“总开关”脚本。无论是 `python manage.py runserver` 启动开发服务器，
    还是 `python manage.py migrate` 建表、`python manage.py createsuperuser` 创建管理员、
    `python manage.py test` 跑测试，最终都会进入本文件的 main() 函数，
    再由 Django 的 execute_from_command_line 按命令名分发执行。

项目位置：
    位于项目根目录 d:\\ems\\program\\manage.py，与配置包 hrms/、业务应用 app01/ 平级。
    它是唯一一个“放在根目录、名字固定”的 Django 脚本，Django 靠它找到整个项目。

对应任务书：
    T1 环境与初始化（项目骨架、manage.py、settings 配置）；
    T12 测试（`python manage.py test` 也是从这里进入的）。

# 讲解要点：
# 1. 答辩时先在终端输入 `python manage.py runserver`，告诉大家“这个 manage.py 就是项目的
#    总入口”，随后浏览器访问 127.0.0.1:8000，看到的第一个中文登录页就是它启动的服务。
# 2. 页面上所有数据（部门、员工、考勤、薪资……）都存在 MySQL 里，建表命令
#    `python manage.py migrate` 同样是从这个文件进入的，所以它是“启动 + 建表 + 测试”的统一入口。
# 3. 代码里的 DJANGO_SETTINGS_MODULE 指向 'hrms.settings'，等于告诉 Django
#    “去读 hrms/settings.py 这份配置”，页面为什么是中文、连的是哪个数据库，都由此决定。
# 4. 页面右上角“Django 后台”能打开 /admin/，也是因为 manage.py 注册了 Django 自带的管理站点。
"""
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            '无法导入 Django，请确认已安装依赖并激活虚拟环境。'
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
