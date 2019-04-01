FROM python:3.7-stretch

RUN apt-get update && apt-get install -y --no-install-recommends \
		memcached nginx \
	&& rm -rf /var/lib/apt/lists/*

RUN mkdir /app
WORKDIR /app

ADD requirements.txt /app
RUN pip install -r requirements.txt

ADD . /app

EXPOSE 80
ENV DJANGO_PROD=1

RUN python manage.py test
RUN python manage.py collectstatic --noinput
RUN python manage.py migrate

RUN rm /etc/nginx/sites-enabled/*
RUN ln -s /app/nginx-site /etc/nginx/sites-enabled/

RUN chmod +x run.sh
CMD /bin/bash run.sh
