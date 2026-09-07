import string
import random
from fastapi import FastAPI, Response
from starlette_exporter import PrometheusMiddleware, handle_metrics

def setup_metrics(app: FastAPI, app_name: str):
    app.add_middleware(
        PrometheusMiddleware,
        app_name=app_name,
        prefix='http',
        group_paths=True
    )

    # random_route = '/' + ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    app.add_route('/metrics', handle_metrics)
