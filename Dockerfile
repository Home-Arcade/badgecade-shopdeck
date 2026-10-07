# Aftendo/shopdeck (GPL-2.0, archived). Only the parts needed for buying
# Badge Arcade plays are copied in; ops/shopdeck_patches.py has our changes.
# Build from this folder: docker build -t badgecade-shopdeck .
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp
WORKDIR /app
RUN pip install --no-cache-dir \
    django==4.1.13 Flask==2.3.2 Werkzeug==2.3.8 django-extensions==3.2.1 \
    django-admin-interface==0.24.2 django-colorfield==0.8.0 xmltodict==0.13.0 \
    requests==2.31.0 psycopg2-binary==2.9.9 Pillow gunicorn

# eShop SOAP services (ecs, ias, cas) and the ticket templates
COPY main.py ecs.py ias.py cas.py basetik.bin basetik_licence.bin ./
COPY templates templates
# Django: admin page, database, ninja (purchases) and samurai (title lookup)
COPY manage.py ./
COPY shopdeck shopdeck
COPY shopdeckdb shopdeckdb
COPY api api
COPY metadata metadata

COPY shopdeck_patches.py /tmp/shopdeck_patches.py
RUN python /tmp/shopdeck_patches.py \
    && SHOPDECK_SECRET_KEY=build python manage.py makemigrations --noinput \
    && SHOPDECK_SECRET_KEY=build python manage.py collectstatic --noinput >/dev/null \
    && useradd --system --uid 10003 shopdeck && mkdir -p /data && chown shopdeck /data
USER 10003
EXPOSE 9000 9001
# 9000: Django (admin page, ninja, samurai)   9001: Flask SOAP (ecs, ias, cas)
CMD ["sh", "-c", "python manage.py migrate --noinput && (gunicorn -b 0.0.0.0:9001 -w 2 main:app &) && exec python manage.py runserver 0.0.0.0:9000 --insecure --noreload"]
