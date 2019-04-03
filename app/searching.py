import logging
import base64
import os
from operator import itemgetter
import datetime
import requests
from pymemcache.client.base import Client
from pymemcache import serde


log = logging.getLogger(__name__)


def memcache_client():
    cache_client = Client(('localhost', 11211),
                          serializer=serde.python_memcache_serializer,
                          deserializer=serde.python_memcache_deserializer)
    return cache_client


def get_or_create_allegro_token():
    cache_client = memcache_client()

    if cache_client:
        try:
            allegro_token = cache_client.get('allegro_token')
            if allegro_token:
                if datetime.datetime.utcnow() < allegro_token['expires']:
                    return allegro_token['token']
        except ConnectionRefusedError:
            log.error('Cache client unavailable')

    client_id = os.environ.get('ALLEGRO_CLIENT_ID', None)
    client_secret = os.environ.get('ALLEGRO_CLIENT_SECRET', None)
    if not client_id or not client_secret:
        return None

    client_auth = base64.b64encode(f'{client_id}:{client_secret}'.encode('utf-8')).decode('utf-8')
    resp = requests.post('https://allegro.pl/auth/oauth/token?grant_type=client_credentials', headers={
        'Authorization': f'Basic {client_auth}'
    })
    auth_data = resp.json()

    if resp.status_code != 200:
        log.error(f'Allegro auth failed: {resp.status_code}')
        log.error(f'{auth_data}')

    if cache_client:
        try:
            expires = datetime.datetime.utcnow() + datetime.timedelta(seconds=auth_data['expires_in'])
            cache_client.set('allegro_token', {
                'token': auth_data['access_token'],
                'expires': expires
            })
        except ConnectionRefusedError:
            log.error('Cache client unavailable')

    if 'access_token' not in auth_data:
        log.error('`access_token` missing in the response')
        return None

    return auth_data['access_token']


def search_allegro(phrase):
    token = get_or_create_allegro_token()
    if not token:
        log.debug('Allegro token is missing. Skipping the search')
        return []
    phrase = phrase.replace(' ', '+')
    resp = requests.get(f'https://api.allegro.pl/offers/listing?category.id=7&phrase={phrase}', headers={
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.allegro.public.v1+json',
    })
    data = resp.json()
    if resp.status_code != 200:
        log.error(f'Allegro search failed: {resp.status_code}')
        log.error(f'{data}')

    if 'items' not in data:
        log.error(f'`items` missing in the Allegro response')
        return []

    try:
        items = data['items']['promoted'] + data['items']['regular']
        items = [{
            'name': item['name'],
            'link': f'https://allegro.pl/oferta/{item["id"]}',
            'price': float(item['sellingMode']['price']['amount']),
            'currency': item['sellingMode']['price']['currency'],
            'isbn': None,
            'source': 'Allegro'
        } for item in items]
        return items
    except KeyError as e:
        log.error(f'Allegro result conversion error: {e}')
        return []


def search_google(phrase):
    phrase = phrase.replace(' ', '+')
    resp = requests.get(f'https://www.googleapis.com/books/v1/volumes?q={phrase}&country=pl')
    data = resp.json()
    if resp.status_code != 200:
        log.error(f'Google search failed: {resp.status_code}')
        log.error(f'{data}')

    def extract_isbn(item):
        try:
            for identifier in item['volumeInfo']['industryIdentifiers']:
                if identifier['type'] == 'ISBN_13':
                    return identifier['identifier']
        except KeyError:
            pass
        return None

    if 'items' not in data:
        log.error(f'`items` missing in the Google response')
        return []

    try:
        items = [{
            'name': item['volumeInfo']['title'],
            'link': item['saleInfo'].get('buyLink', None),
            'price': float(item['saleInfo']['listPrice']['amount']) if 'listPrice' in item['saleInfo'] else 0,
            'currency': item['saleInfo']['listPrice']['currencyCode'] if 'listPrice' in item['saleInfo'] else None,
            'isbn': extract_isbn(item),
            'source': 'Google Books'
        } for item in data['items']]
        return items
    except KeyError as e:
        log.error(f'Google result conversion error: {e}')
        return []


def search_all(phrase):
    methods = [
        search_allegro,
        search_google
    ]
    output = {
        'items': []
    }
    for method in methods:
        output['items'] += method(phrase)
    output['items'].sort(key=itemgetter('price'))
    return output


def group_by_isbn(items):
    items_by_isbn = {}
    items_without_isbn = []
    for item in items:
        isbn = item.get('isbn', None)
        if isbn:
            items_by_isbn.setdefault(isbn, []).append(item)
        else:
            items_without_isbn.append(item)
    for items_col in items_by_isbn.values():
        items_col.sort(key=itemgetter('price'))
    result = [{
        'isbn': isbn,
        'items': items_col,
    } for isbn, items_col in sorted(items_by_isbn.items(), key=lambda x: x[0])]
    items_without_isbn.sort(key=itemgetter('price'))
    result.append({
        'isbn': None,
        'items': items_without_isbn,
    })
    return result
