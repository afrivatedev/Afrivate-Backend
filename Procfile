web: gunicorn Afrivate.wsgi
worker: celery -A Afrivate worker --loglevel=info
beat: celery -A Afrivate beat --loglevel=info
