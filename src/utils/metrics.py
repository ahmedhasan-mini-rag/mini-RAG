from fastapi import FastAPI
from starlette_exporter import PrometheusMiddleware, handle_metrics

def setup_metrics(app: FastAPI, app_name: str):
    app.add_middleware(
        PrometheusMiddleware,
        app_name=app_name,
        prefix='http',
        group_paths=True
    )

    app.add_route('/metrics', handle_metrics, include_in_schema=False)
