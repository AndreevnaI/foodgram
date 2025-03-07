from rest_framework.pagination import PageNumberPagination

from .constants import LIMIT_PAGE_SIZE


class LimitPageNumberPaginator(PageNumberPagination):
    page_size_query_param = 'limit'
    page_size = LIMIT_PAGE_SIZE
