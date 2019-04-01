# Book Search Engine

Simple web application aggregating results from book stores with public API. Currently supporting:
- Allegro
- Google Books

## Run with Docker

Build:
```bash
docker build -t book_search_engine .
```

Run:
```bash
docker run -it -p 8080:80 -e ALLEGRO_CLIENT_ID=<CLIENT_ID> -e ALLEGRO_CLIENT_SECRET=<CLIENT_SECRET> book_search_engine
```

Obtaining Allegro API keys: https://developer.allegro.pl/auth/

## Run locally

Prerequisites:
- python 3.6+
- memcached server

Installing requirements:
```bash
pip install -r requirements.txt
```

Running tests:
```bash
python manage.py test
```

Running developer server:
```bash
export ALLEGRO_CLIENT_ID=<CLIENT_ID>
export ALLEGRO_CLIENT_SECRET=<CLIENT_SECRET>
python manage.py runserver localhost:8080
```
