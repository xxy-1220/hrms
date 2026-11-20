"""WSGI 入口（同步 Web 服务网关）。

文件职责：
    定义 WSGI 应用对象 application，供 gunicorn、uWSGI、mod_wsgi 等服务器调用。
    Django 本身不直接监听端口，真正“接待”浏览器请求的是 Web 服务器，
    服务器通过 WSGI 协议把请求交给这里，Django 处理完再把响应交回去。
    另外，manage.py runserver 默认也是通过这条 WSGI 链路启动的。

项目位置：
    d:\\ems\\program\\hrms\\wsgi.py，与 settings.py 同目录；settings.py 里
    WSGI_APPLICATION='hrms.wsgi.application' 指向本文件中的 application 变量。

对应任务书：
    T1 环境与初始化（项目骨架与部署入口）；
    与 T4~T10 的所有页面都相关——浏览器看到的每个页面都经这里进入 Django。

# 讲解要点：
# 1. 答辩演示时终端出现 “Starting development server at http://127.0.0.1:8000/”，
#    背后就是 runserver 加载了本文件的 application，登录页、首页、列表页的请求都从这里进 Django。
# 2. 浏览器访问任意页面能看到内容，说明 WSGI 这条“服务器 → Django → 视图 → 模板”的链路是通的。
# 3. 代码里的 DJANGO_SETTINGS_MODULE 指向 hrms.settings，保证部署服务器知道读哪份配置
#   （页面的中文、数据库连接、静态文件路径都依赖它）。
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms.settings')

application = get_wsgi_application()
