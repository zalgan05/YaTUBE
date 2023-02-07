from django.core.paginator import Paginator


def paginate_post(request, posts, numbers):
    """Разбивает контент на отдельные страницы."""
    paginator = Paginator(posts, numbers)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
