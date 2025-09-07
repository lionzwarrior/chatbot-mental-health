from prometheus_client import Histogram, start_http_server, REGISTRY
import os
import threading

try:
    CHATBOT_RESPONSE_TIME = REGISTRY._names_to_collectors[
        "chatbot_response_duration_seconds"
    ]
    print("Prometheus metric 'chatbot_response_duration_seconds' already initialized.")
except KeyError:
    CHATBOT_RESPONSE_TIME = Histogram(
        "chatbot_response_duration_seconds",
        "Duration of chatbot responses.",
        ["model_name"],
        buckets=[1.0, 5.0, 10.0, 20.0, 30.0, 60.0, 120.0, float("inf")],
    )
    print("Prometheus metric 'chatbot_response_duration_seconds' initialized.")

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


def observe_chatbot_response_time(duration, model_name="llama3.1:latest"):
    CHATBOT_RESPONSE_TIME.labels(model_name=model_name).observe(duration)
