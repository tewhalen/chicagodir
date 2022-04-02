release: flask db upgrade
web: gunicorn chicagodir.app:create_app\(\) -b 0.0.0.0:$PORT -w 3
worker: flask run_worker