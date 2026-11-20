"""ASGI 入口（异步 Web 服务网关）。

文件职责：
    定义 ASGI 应用对象 application，供 Daphne、Uvicorn 等异步服务器调用。
    ASGI 是 WSGI 的“升级版协议”，除了普通 HTTP 请求，还能处理 WebSocket（实时推送）
    和长连接。本项目目前只用普通 HTTP，所以它和 wsgi.py 效果一样，只是预留了异步能力。

项目位置：
    d:\\ems\\program\\hrms\\asgi.py，与 settings.py 同目录；settings.py 里
    ASGI_APPLICATION='hrms.asgi.application' 指向本文件中的 application 变量。

对应任务书：
    T1 环境与初始化（项目骨架与部署入口）；
    T9 AJAX 任务（当前 AJAX 仍是普通 HTTP 请求，走 ASGI 也能正常工作）。

# 讲解要点：
# 1. 答辩时浏览器能打开登录页、任务管理页，说明 HTTP 链路正常；此时用 WSGI 还是 ASGI
#    对页面效果没有区别，学生可以讲“ASGI 是为将来做 WebSocket 实时消息预留的入口”。
# 2. 任务管理页用 AJAX 提交任务、不刷新页面就能看到新任务，这类请求同样可以由本文件接入，
#    但当前课程设计使用同步视图，所以 ASGI 主要作为部署备选。
# 3. 代码里指定 DJANGO_SETTINGS_MODULE，保证异步服务器启动时也能读到同一份配置
#   （页面中文、时区、数据库都从这里来）。
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms.settings')

application = get_asgi_application()
