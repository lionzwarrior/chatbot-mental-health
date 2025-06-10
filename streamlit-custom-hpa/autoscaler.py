from kubernetes import client, config
from prometheus_api_client import PrometheusConnect
import time
import os

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus-operated.remmanuel.svc.cluster.pakcarik:9090")

prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)
config.load_incluster_config()

apps_v1 = client.AppsV1Api()

DEPLOYMENT_NAME = "mental-health-chatbot-deployment"
NAMESPACE = "remmanuel"
LOW_THRESHOLD = 30
HIGH_THRESHOLD = 80
MIN_REPLICAS = 1
MAX_REPLICAS = 3

def scale_to(n):
    print(f"Scaling {DEPLOYMENT_NAME} in namespace {NAMESPACE} to {n} replicas")
    body = {"spec": {"replicas": n}}
    try:
        apps_v1.patch_namespaced_deployment_scale(name=DEPLOYMENT_NAME, namespace=NAMESPACE, body=body)
        print(f"Successfully scaled to {n} replicas.")
    except client.ApiException as e:
        print(f"Error scaling deployment: {e}")

def get_current_replicas():
    try:
        deployment = apps_v1.read_namespaced_deployment(name=DEPLOYMENT_NAME, namespace=NAMESPACE)
        return deployment.spec.replicas
    except client.ApiException as e:
        print(f"Error reading deployment: {e}")
        return None

def get_cpu_utilization():
    query = f'avg(rate(container_cpu_usage_seconds_total{{namespace="{NAMESPACE}", pod=~"{DEPLOYMENT_NAME}.*", container!=""}}[5m])) * 100'
    try:
        result = prom.get_current_metric_value(query)
        if result and result[0]['value'][1]:
            cpu_util = float(result[0]['value'][1])
            return cpu_util
        return None
    except Exception as e:
        print(f"Error querying Prometheus for CPU utilization: {e}")
        return None

if __name__ == "__main__":
    print(f"Starting auto-scaler for deployment: {DEPLOYMENT_NAME} in namespace: {NAMESPACE}")
    while True:
        try:
            cpu_util = get_cpu_utilization()
            current_replicas = get_current_replicas()

            if cpu_util is not None and current_replicas is not None:
                print(f"CPU utilization: {cpu_util:.2f}%, current replicas: {current_replicas}")

                if cpu_util > HIGH_THRESHOLD and current_replicas < MAX_REPLICAS:
                    scale_to(current_replicas + 1)
                elif cpu_util < LOW_THRESHOLD and current_replicas > MIN_REPLICAS:
                    scale_to(current_replicas - 1)
                else:
                    print("No scaling action needed at this time.")
            else:
                print("Could not retrieve CPU utilization or current replica count. Retrying...")

        except Exception as e:
            print(f"Unhandled error in main loop: {e}")

        time.sleep(60)