from django.test import TestCase, Client
from unittest import mock

from app import searching


class ViewTest(TestCase):

    def test_start_view(self):
        client = Client()
        resp = client.get('/')
        self.assertEqual(resp.status_code, 200)

    @mock.patch('app.searching.search_all')
    def test_search_view(self, search_all_mock):
        search_all_mock.return_value = {
            'items': []
        }
        client = Client()
        resp = client.get('/api/v1/search?query=clean code')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('items' in resp.json())

    def test_search_view_post_should_return_not_allowed(self):
        client = Client()
        resp = client.post('/api/v1/search?query=clean code')
        self.assertEqual(resp.status_code, 405)

    def test_search_view_missing_query_param_should_return_bad_request(self):
        client = Client()
        resp = client.get('/api/v1/search')
        self.assertEqual(resp.status_code, 400)


class SearchingTest(TestCase):

    @mock.patch('app.searching.search_allegro', lambda x: [{'name': 'a', 'price': 10}])
    @mock.patch('app.searching.search_google', lambda x: [{'name': 'b', 'price': 5}])
    def test_search_all_should_sort_results(self):
        result = searching.search_all('xyz')
        self.assertTrue('items' in result)
        self.assertEqual(len(result['items']), 2)
        self.assertEqual(result['items'][0]['price'], 5)
        self.assertEqual(result['items'][1]['price'], 10)
        
    @mock.patch('app.searching.memcache_client', lambda: None)
    @mock.patch('os.environ.get', {}.get)
    @mock.patch('requests.post')
    def test_get_or_create_allegro_token_with_missing_ids_should_return_none(self, post_mock):
        result = searching.get_or_create_allegro_token()
        self.assertIsNone(result)

    @mock.patch('app.searching.memcache_client', lambda: None)
    @mock.patch('os.environ.get', {
        'ALLEGRO_CLIENT_ID': 'abc',
        'ALLEGRO_CLIENT_SECRET': 'abc',
    }.get)
    @mock.patch('requests.post')
    def test_get_or_create_allegro_token_with_ids_should_return_valid_token(self, post_mock):
        post_mock.return_value.json.return_value = {
            'access_token': 'xyz'
        }
        result = searching.get_or_create_allegro_token()
        self.assertEqual(result, 'xyz')

    @mock.patch('requests.get')
    @mock.patch('app.searching.get_or_create_allegro_token')
    def test_search_allegro_missing_token_should_return_empty_list(self, get_token_mock, get_mock):
        get_mock.return_value.json.return_value = {'items': {}}
        get_token_mock.return_value = None
        result = searching.search_allegro('xyz')
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @mock.patch('requests.get')
    @mock.patch('app.searching.get_or_create_allegro_token')
    def test_search_allegro_invalid_data_should_return_empty_list(self, get_token_mock, get_mock):
        get_mock.return_value.json.return_value = {'invalid': {}}
        get_token_mock.return_value = 'token123'
        result = searching.search_allegro('xyz')
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @mock.patch('requests.get')
    @mock.patch('app.searching.get_or_create_allegro_token')
    def test_search_allegro_empty_result_should_return_empty_list(self, get_token_mock, get_mock):
        get_mock.return_value.json.return_value = {'items': {'promoted': [], 'regular': []}}
        get_token_mock.return_value = 'token123'
        result = searching.search_allegro('xyz')
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @mock.patch('requests.get')
    @mock.patch('app.searching.get_or_create_allegro_token')
    def test_search_allegro_valid_result_should_return_valid_list(self, get_token_mock, get_mock):
        get_mock.return_value.json.return_value = {'items': {'promoted': [{
            'name': 'xyz',
            'id': 123,
            'sellingMode': {
                'price': {
                    'amount': 10,
                    'currency': 'pln'
                }
            }
        }], 'regular': []}}
        get_token_mock.return_value = 'token123'
        result = searching.search_allegro('xyz')
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], {
            'name': 'xyz',
            'link': 'https://allegro.pl/oferta/123',
            'price': 10,
            'currency': 'pln',
            'isbn': None,
            'source': 'Allegro'
        })

    @mock.patch('requests.get')
    def test_search_google_invalid_data_should_return_empty_list(self, get_mock):
        get_mock.return_value.json.return_value = {'invalid': []}
        result = searching.search_google('xyz')
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @mock.patch('requests.get')
    def test_search_google_empty_result_should_return_empty_list(self, get_mock):
        get_mock.return_value.json.return_value = {'items': []}
        result = searching.search_google('xyz')
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @mock.patch('requests.get')
    def test_search_google_valid_result_should_return_valid_list(self, get_mock):
        get_mock.return_value.json.return_value = {'items': [{
            'volumeInfo': {
                'title': 'xyz'
            },
            'saleInfo': {
                'buyLink': 'somelink',
                'listPrice': {
                    'amount': 10,
                    'currencyCode': 'pln'
                },
            }
        }]}
        result = searching.search_google('xyz')
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], {
            'name': 'xyz',
            'link': 'somelink',
            'price': 10,
            'currency': 'pln',
            'isbn': None,
            'source': 'Google Books'
        })

    @mock.patch('requests.get')
    def test_search_google_valid_result_with_isbn_should_return_valid_list(self, get_mock):
        get_mock.return_value.json.return_value = {'items': [{
            'volumeInfo': {
                'title': 'xyz',
                'industryIdentifiers': [{
                    'type': 'ISBN_13',
                    'identifier': '123'
                }]
            },
            'saleInfo': {
                'buyLink': 'somelink',
                'listPrice': {
                    'amount': 10,
                    'currencyCode': 'pln'
                },
            }
        }]}
        result = searching.search_google('xyz')
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], {
            'name': 'xyz',
            'link': 'somelink',
            'price': 10,
            'currency': 'pln',
            'isbn': '123',
            'source': 'Google Books'
        })