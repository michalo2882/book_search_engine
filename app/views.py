import logging

from django.http import HttpResponseNotAllowed, JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.cache import cache_page

from app.searching import search_all, group_by_isbn


log = logging.getLogger(__name__)


@cache_page(60 * 15)
def start(request):
    return render(request, 'app/index.html')


@cache_page(60 * 15)
def search(request):
    if request.method == 'GET':
        query = request.GET.get('query', None)
        if not query:
            return HttpResponseBadRequest()
        try:
            result = search_all(query)
            result['items'] = group_by_isbn(result['items'])
        except Exception as e:
            log.error(f'Exception: {e}')
            return JsonResponse({'error': 'application error'}, status=500)
        return JsonResponse(result)
    else:
        return HttpResponseNotAllowed(permitted_methods=['GET'])
