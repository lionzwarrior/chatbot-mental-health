import os
import threading

from prometheus_client import Gauge, Counter, start_http_server, REGISTRY

POD_NAME = os.getenv('POD_NAME', 'unknown-pod')

try:
    CONCURRENT_REQUESTS = REGISTRY._names_to_collectors[
        "chatbot_concurrent_requests"
    ]
    print("Prometheus metric 'chatbot_concurrent_requests' already initialized.")
except KeyError:
    CONCURRENT_REQUESTS = Gauge(
        "chatbot_concurrent_requests",
        "Number of concurrent chatbot requests.",
        ["pod"]
    )
    print("Prometheus metric 'chatbot_concurrent_requests' initialized.")
    

try:
    REQUESTS_COUNTER = REGISTRY._names_to_collectors[
        "chatbot_requests_total"
    ]
    print("Prometheus metric 'chatbot_requests_total' already initialized.")
except KeyError:
    REQUESTS_COUNTER = Counter(
        "chatbot_requests_total",
        "Total number of chatbot requests.",
        ["pod"]
    )
    print("Prometheus metric 'chatbot_requests_total' initialized.")


metrics_server_lock = threading.Lock()

def start_metrics_server(port=8000):
    """Starts a simple HTTP server to expose Prometheus metrics."""
    with metrics_server_lock:
        if "metrics_server_started" not in os.environ:
            try:
                start_http_server(port)
                print(f"Prometheus metrics server started on port {port}")
                os.environ["metrics_server_started"] = "true"
            except Exception as e:
                if "Address already in use" in str(e):
                    print(f"Prometheus metrics server already running on port {port}.")
                    os.environ["metrics_server_started"] = "true"
                else:
                    print(f"Error starting metrics server: {e}")


def inc_concurrent_requests():
    """Increment the concurrent request gauge for this pod."""
    CONCURRENT_REQUESTS.labels(POD_NAME).inc()


def dec_concurrent_requests():
    """Decrement the concurrent request gauge for this pod."""
    CONCURRENT_REQUESTS.labels(POD_NAME).dec()


def count_request():
    """Increment the total request counter for this pod and user."""
    REQUESTS_COUNTER.labels(POD_NAME).inc()
