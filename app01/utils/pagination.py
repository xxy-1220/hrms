"""分页工具。

职责（对应任务书 T3/T6/T7 等列表页的通用能力）：
把任意 QuerySet 按每页固定条数切成一页，并把“当前页码”与“除页码外的其它筛选
参数”一起返回，供模板拼接翻页链接。

术语：Paginator = Django 自带分页器，负责切片并提供总页数/上一页/下一页；
QuerySet 切片 = 分页本质是惰性查询集做 [start:end]，只查当前页的数据。
"""

# 讲解要点：
# 1. 页面现象：各列表页底部显示“共 N 条，第 1 / M 页”，每页正好 10 行 ——
#    per_page 默认值 10 来自本文件，模板 includes/pagination.html 渲染页码。
# 2. 页面现象：搜索“张”后点“下一页”，地址是 /employees/?page=2&q=张，
#    筛选条件没有丢 —— 因为返回的 query_string 保留了 q 等参数。
# 3. 页面现象：手改地址成 ?page=abc 不会 500，而是回到第 1 页；改成 ?page=999
#    也不报错，而是显示最后一页 —— 对应 PageNotAnInteger 与 EmptyPage 分支。
# 4. 页面现象：筛选结果不足一页时底部不出现分页条 —— 模板用
#    {% if page_obj.has_other_pages %} 判断，page_obj 就是这里返回的。

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator


def paginate(request, queryset, per_page=10):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    query = request.GET.copy()
    query.pop('page', None)
    return page_obj, query.urlencode()
