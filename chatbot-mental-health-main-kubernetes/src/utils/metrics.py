import threading
from prometheus_client import start_http_server, Counter, Histogram, Gauge
import time
import os

STREAMLIT_PAGE_VIEWS = Counter(
    'streamlit_page_views_total',
    'Total number of Streamlit page views or interactions.'
)

BUTTON_CLICKS = Counter(
    'streamlit_button_clicks_total',
    'Total number of button clicks.',
    ['button_name']
)

CHATBOT_RESPONSE_TIME = Histogram(
    'chatbot_response_duration_seconds',
    'Duration of chatbot responses.',
    ['model_name']
)

def start_metrics_server(port=8000):
    """Starts a simple HTTP server to expose Prometheus metrics."""
    if 'metrics_server_started' not in os.environ:
        try:
            start_http_server(port)
            print(f"Prometheus metrics server started on port {port}")
            os.environ['metrics_server_started'] = 'true'
        except Exception as e:
            print(f"Error starting metrics server: {e}")

def increment_page_view():
    STREAMLIT_PAGE_VIEWS.inc()

def increment_button_click(button_name):
    BUTTON_CLICKS.labels(button_name=button_name).inc()

def observe_chatbot_response_time(duration, model_name="default"):
    CHATBOT_RESPONSE_TIME.labels(model_name=model_name).observe(duration)