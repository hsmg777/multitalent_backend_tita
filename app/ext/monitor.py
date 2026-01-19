from prometheus_flask_exporter import PrometheusMetrics

metrics = PrometheusMetrics.for_app_factory()

def init_app(app):
    metrics.init_app(app)
    # Set static information as default labels
    metrics.info('app_info', 'Application info', version='1.0.0')
