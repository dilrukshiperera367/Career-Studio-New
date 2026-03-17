"""Standard pagination for HRM API."""
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class LargeResultsSetPagination(PageNumberPagination):
    """For bulk data exports."""
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 500
