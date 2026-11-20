"""公告管理视图：发布、列表、置顶、搜索、分页。（对应任务书 T8 公告管理）

本文件包含公告模块的全部页面逻辑：
- 公告列表：置顶优先排序 + 标题/内容模糊搜索 + 分页；
- 发布公告：发布人自动取当前登录用户，发布时间由模型 auto_now_add 自动写入；
- 编辑、删除、置顶/取消置顶：删除和置顶只接受 POST 请求。
所有视图都用 @require_perm 装饰器做接口级权限校验，权限编码见函数上方的装饰器。
"""

# 讲解要点（结合浏览器里看到的页面效果）：
# 1. 打开「公告管理」页面，表格最上方是一条带「置顶」徽标的公告，其余公告按发布时间从新到旧排列——
#    这对应模型里的 ordering = ['-is_top', '-publish_time']，列表视图没有额外排序，直接沿用模型默认排序。
# 2. 在搜索框输入「绩效」点查询，页面只剩标题或正文含「绩效」的公告，地址栏出现 ?q=绩效——对应
#    keyword = request.GET.get('q') 和 Q(title__icontains=...) | Q(content__icontains=...)。
# 3. 翻到第 2 页时搜索关键字不会丢失——对应 paginate() 返回的 query_string 被模板拼进分页链接。
# 4. 发布后列表里能看到发布人和发布时间，之后再编辑公告，发布时间仍是最初的时间；点「置顶/取消置顶」
#    按钮回到列表后徽标出现或消失——对应 publisher = request.user、publish_time 的 auto_now_add=True
#    以及 toggle 视图把 is_top 取反后只保存这一列。

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from app01.forms import AnnouncementForm
from app01.middleware.permission import require_perm
from app01.models import Announcement
from app01.utils.pagination import paginate


@require_perm('announcement:view')
def announcement_list(request):
    keyword = request.GET.get('q', '').strip()
    queryset = Announcement.objects.select_related('publisher')
    if keyword:
        queryset = queryset.filter(
            Q(title__icontains=keyword) | Q(content__icontains=keyword)
        )
    page_obj, query_string = paginate(request, queryset, per_page=10)
    return render(
        request,
        'app01/announcement_list.html',
        {
            'page_obj': page_obj,
            'query_string': query_string,
            'keyword': keyword,
        },
    )


@require_perm('announcement:add')
def announcement_add(request):
    form = AnnouncementForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        announcement = form.save(commit=False)
        announcement.publisher = request.user
        announcement.save()
        messages.success(request, '公告发布成功')
        return redirect('announcement_list')
    return render(
        request,
        'app01/announcement_form.html',
        {'form': form, 'title': '发布公告'},
    )


@require_perm('announcement:edit')
def announcement_edit(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    form = AnnouncementForm(request.POST or None, instance=announcement)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '公告修改成功')
        return redirect('announcement_list')
    return render(
        request,
        'app01/announcement_form.html',
        {'form': form, 'title': '编辑公告', 'announcement': announcement},
    )


@require_perm('announcement:delete')
def announcement_delete(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method != 'POST':
        messages.error(request, '删除操作必须通过 POST 提交')
        return redirect('announcement_list')
    announcement.delete()
    messages.success(request, '公告删除成功')
    return redirect('announcement_list')


@require_perm('announcement:edit')
def announcement_toggle_top(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method != 'POST':
        messages.error(request, '置顶操作必须通过 POST 提交')
        return redirect('announcement_list')
    announcement.is_top = not announcement.is_top
    announcement.save(update_fields=['is_top'])
    messages.success(request, '已置顶' if announcement.is_top else '已取消置顶')
    return redirect('announcement_list')
