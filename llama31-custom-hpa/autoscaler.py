import os
import time
import logging
from kubernetes import client, config
from prometheus_api_client import PrometheusConnect, PrometheusApiClientException

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    config.load_incluster_config()
    logging.info("Loaded in-cluster Kubernetes config.")
except config.config_exception.ConfigException:
    try:
        config.load_kube_config()
        logging.info("Loaded kubeconfig from default path.")
    except config.config_exception.ConfigException as e:
        logging.error(f"Could not load Kubernetes config: {e}")
        exit(1)

apps_v1 = client.AppsV1Api()

DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME", "chatbot-mental-health")
NAMESPACE = os.getenv("NAMESPACE", "remmanuel")
PROMETHEUS_SERVICE_NAME = os.getenv("PROMETHEUS_SERVICE_NAME", "prometheus-operated")
PROMETHEUS_PORT = os.getenv("PROMETHEUS_PORT", "9090")
PROMETHEUS_URL = f"http://{PROMETHEUS_SERVICE_NAME}.{NAMESPACE}.svc.cluster.pakcarik:{PROMETHEUS_PORT}"

try:
    prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)
    prom.check_prometheus_connection()
    logging.info(f"Successfully connected to Prometheus at: {PROMETHEUS_URL}")
except PrometheusApiClientException as e:
    logging.error(f"Failed to connect to Prometheus at {PROMETHEUS_URL}: {e}")
    exit(1)

CPU_LOW_THRESHOLD = float(os.getenv("CPU_LOW_THRESHOLD", "30.0"))
CPU_HIGH_THRESHOLD = float(os.getenv("CPU_HIGH_THRESHOLD", "80.0"))

PAGE_VIEW_RATE_HIGH_THRESHOLD = float(os.getenv("PAGE_VIEW_RATE_HIGH_THRESHOLD", "0.5"))
PAGE_VIEW_RATE_LOW_THRESHOLD = float(os.getenv("PAGE_VIEW_RATE_LOW_THRESHOLD", "0.1"))

MIN_REPLICAS = int(os.getenv("MIN_REPLICAS", "1"))
MAX_REPLICAS = int(os.getenv("MAX_REPLICAS", "3"))
SCALE_COOLDOWN_SECONDS = int(os.getenv("SCALE_COOLDOWN_SECONDS", "300"))

last_scale_time = 0

def scale_deployment(n_replicas: int):
    global last_scale_time
    current_replicas = get_current_replicas()
    if current_replicas is None:
        return

    if not (MIN_REPLICAS <= n_replicas <= MAX_REPLICAS):
        logging.warning(f"Attempted to scale to {n_replicas} which is outside min/max replica bounds ({MIN_REPLICAS}-{MAX_REPLICAS}). Aborting.")
        return

    if n_replicas == current_replicas:
        logging.info(f"Deployment already at desired replica count: {n_replicas}. No scaling needed.")
        return

    if time.time() - last_scale_time < SCALE_COOLDOWN_SECONDS:
        logging.info(f"Cooldown period active. Last scale was {int(time.time() - last_scale_time)}s ago. Skipping scale.")
        return

    logging.info(f"Scaling {DEPLOYMENT_NAME} in namespace {NAMESPACE} from {current_replicas} to {n_replicas} replicas")
    body = {"spec": {"replicas": n_replicas}}
    try:
        apps_v1.patch_namespaced_deployment_scale(name=DEPLOYMENT_NAME, namespace=NAMESPACE, body=body)
        logging.info(f"Successfully initiated scale to {n_replicas} replicas.")
        last_scale_time = time.time()
    except client.ApiException as e:
        logging.error(f"Error scaling deployment: {e}")

def get_current_replicas() -> int | None:
    try:
        deployment = apps_v1.read_namespaced_deployment(name=DEPLOYMENT_NAME, namespace=NAMESPACE)
        return deployment.spec.replicas
    except client.ApiException as e:
        if e.status == 404:
            logging.error(f"Deployment '{DEPLOYMENT_NAME}' not found in namespace '{NAMESPACE}'. Check name and namespace.")
        else:
            logging.error(f"Error reading deployment '{DEPLOYMENT_NAME}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error when getting current replicas: {e}")
        return None

def query_prometheus(query: str, metric_name: str) -> float | None:
    try:
        result = prom.custom_query(query=query)
        if result and len(result) > 0 and 'value' in result[0] and len(result[0]['value']) > 1:
            value = float(result[0]['value'][1])
            logging.debug(f"Prometheus query for '{metric_name}' returned: {value}")
            return value
        logging.info(f"Prometheus query for '{metric_name}' returned no data or unexpected format.")
        return None
    except PrometheusApiClientException as e:
        logging.error(f"Prometheus API error for '{metric_name}': {e}")
        return None
    except Exception as e:
        logging.error(f"Error querying Prometheus for '{metric_name}': {e}")
        return None

def get_cpu_utilization() -> float | None:
    query = f'avg(rate(container_cpu_usage_seconds_total{{namespace="{NAMESPACE}", pod=~"{DEPLOYMENT_NAME}-.*", container!="", image!=""}}[5m])) * 100'
    return query_prometheus(query, "CPU Utilization")

def get_average_page_view_rate() -> float | None:
    query = f'sum(rate(streamlit_page_views_total{{namespace="{NAMESPACE}", pod=~"{DEPLOYMENT_NAME}-.*"}}[5m])) / count(kube_pod_info{{namespace="{NAMESPACE}", pod=~"{DEPLOYMENT_NAME}-.*"}})'
    return query_prometheus(query, "Average Page View Rate per Replica")

if __name__ == "__main__":
    logging.info(f"Starting auto-scaler for deployment: {DEPLOYMENT_NAME} in namespace: {NAMESPACE}")
    while True:
        try:
            current_replicas = get_current_replicas()
            if current_replicas is None:
                logging.warning("Could not determine current replicas. Retrying...")
                time.sleep(30)
                continue

            cpu_util = get_cpu_utilization()
            page_view_rate = get_average_page_view_rate()

            logging.info(f"Current state: Replicas={current_replicas}, CPU Util={cpu_util:.2f}% (if available), Page View Rate/Replica={page_view_rate:.2f} (if available)")
            desired_replicas = current_replicas

            scale_up_needed = False
            if cpu_util is not None and cpu_util > CPU_HIGH_THRESHOLD:
                logging.info(f"CPU utilization ({cpu_util:.2f}%) is above HIGH_THRESHOLD ({CPU_HIGH_THRESHOLD}%).")
                scale_up_needed = True
            
            if page_view_rate is not None and page_view_rate > PAGE_VIEW_RATE_HIGH_THRESHOLD:
                logging.info(f"Page view rate per replica ({page_view_rate:.2f}) is above HIGH_THRESHOLD ({PAGE_VIEW_RATE_HIGH_THRESHOLD}).")
                scale_up_needed = True

            if scale_up_needed:
                if current_replicas < MAX_REPLICAS:
                    desired_replicas = current_replicas + 1
                    logging.info(f"Scaling UP to {desired_replicas} replicas.")
                else:
                    logging.info(f"Already at MAX_REPLICAS ({MAX_REPLICAS}). Cannot scale up.")

            scale_down_needed = False
            if not scale_up_needed: 
                if cpu_util is not None and cpu_util < CPU_LOW_THRESHOLD:
                    logging.info(f"CPU utilization ({cpu_util:.2f}%) is below LOW_THRESHOLD ({CPU_LOW_THRESHOLD}%).")
                    scale_down_needed = True
                    
                if page_view_rate is not None and page_view_rate < PAGE_VIEW_RATE_LOW_THRESHOLD:
                    logging.info(f"Page view rate per replica ({page_view_rate:.2f}) is below LOW_THRESHOLD ({PAGE_VIEW_RATE_LOW_THRESHOLD}).")
                    scale_down_needed = True

                if scale_down_needed:
                    if current_replicas > MIN_REPLICAS:
                        desired_replicas = current_replicas - 1
                        logging.info(f"Scaling DOWN to {desired_replicas} replicas.")
                    else:
                        logging.info(f"Already at MIN_REPLICAS ({MIN_REPLICAS}). Cannot scale down.")

            if desired_replicas != current_replicas:
                scale_deployment(desired_replicas)
            else:
                logging.info("No scaling action needed at this time.")

        except Exception as e:
            logging.error(f"Unhandled error in main loop: {e}", exc_info=True)

        time.sleep(60) 