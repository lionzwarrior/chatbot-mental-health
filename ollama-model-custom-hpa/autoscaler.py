import os
import time
import logging
from kubernetes import client, config
from prometheus_api_client import PrometheusConnect, PrometheusApiClientException

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

try:
    config.load_incluster_config()
    logging.info("Loaded in-cluster Kubernetes config.")
except config.config_exception.ConfigException:
    config.load_kube_config()
    logging.info("Loaded kubeconfig from default path.")

apps_v1 = client.AppsV1Api()

STATEFULSET_NAME = os.getenv("STATEFULSET_NAME", "ollama-model")
NAMESPACE = os.getenv("NAMESPACE", "remmanuel")
PROMETHEUS_URL = f"http://{os.getenv('PROMETHEUS_SERVICE_NAME', 'prometheus-operated')}.{NAMESPACE}.svc.cluster.pakcarik:{os.getenv('PROMETHEUS_PORT', '9090')}"
GPU_UTIL_HIGH = float(os.getenv("GPU_UTIL_HIGH_THRESHOLD", "70"))
GPU_UTIL_LOW = float(os.getenv("GPU_UTIL_LOW_THRESHOLD", "40"))
GPU_MEM_HIGH = float(os.getenv("GPU_MEM_HIGH_THRESHOLD", "85"))
GPU_MEM_LOW = float(os.getenv("GPU_MEM_LOW_THRESHOLD", "50"))
MIN_REPLICAS = int(os.getenv("MIN_REPLICAS", "3"))
MAX_REPLICAS = int(os.getenv("MAX_REPLICAS", "6"))
SCALE_COOLDOWN = int(os.getenv("SCALE_COOLDOWN_SECONDS", "60"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))

try:
    prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)
    prom.check_prometheus_connection()
    logging.info(f"Connected to Prometheus at: {PROMETHEUS_URL}")
except PrometheusApiClientException as e:
    logging.error(f"Failed to connect to Prometheus: {e}")
    exit(1)

last_scale_up_time = 0
last_scale_down_time = 0

def query_prometheus(query_string, metric_name):
    """Executes a query in Prometheus and returns a single float value."""
    try:
        result = prom.custom_query(query=query_string)
        if not result or "value" not in result[0]:
            logging.warning(f"Prometheus query for {metric_name} returned no data.")
            return None
        return float(result[0]["value"][1])
    except Exception as e:
        logging.error(f"Prometheus query error for {metric_name}: {e}")
        return None

def get_gpu_utilization():
    """Gets the average GPU utilization across all target pods."""
    query = f'avg(DCGM_FI_DEV_GPU_UTIL{{exported_namespace="{NAMESPACE}",exported_pod=~"{STATEFULSET_NAME}-.*"}})'
    return query_prometheus(query, "GPU Utilization")

def get_gpu_memory_usage():
    """Gets the average GPU memory usage (as a percentage) across all target pods."""
    query = (
        f'(avg(DCGM_FI_DEV_FB_USED{{exported_namespace="{NAMESPACE}",exported_pod=~"{STATEFULSET_NAME}-.*"}}) / '
        f'(avg(DCGM_FI_DEV_FB_USED{{exported_namespace="{NAMESPACE}",exported_pod=~"{STATEFULSET_NAME}-.*"}}) + '
        f'avg(DCGM_FI_DEV_FB_FREE{{exported_namespace="{NAMESPACE}",exported_pod=~"{STATEFULSET_NAME}-.*"}}))) * 100'
    )
    return query_prometheus(query, "GPU Memory Usage")

def get_current_replicas():
    """Gets the number of currently READY replicas for the statefulset."""
    try:
        statefulset = apps_v1.read_namespaced_stateful_set(STATEFULSET_NAME, NAMESPACE)
        if statefulset.status and statefulset.status.ready_replicas is not None:
            return statefulset.status.ready_replicas
        return statefulset.spec.replicas if statefulset.spec.replicas is not None else 0
    except client.ApiException as e:
        logging.error(f"Could not read replicas for {STATEFULSET_NAME}: {e}")
        return None

def scale_statefulset(new_replica_count, direction):
    """Patches the statefulset to the new replica count and handles cooldown."""
    global last_scale_up_time, last_scale_down_time
    now = time.time()

    if direction == "up" and now - last_scale_up_time < SCALE_COOLDOWN:
        logging.info(f"Scale up is in cooldown. Waiting...")
        return
    if direction == "down" and now - last_scale_down_time < SCALE_COOLDOWN:
        logging.info(f"Scale down is in cooldown. Waiting...")
        return

    logging.info(f"Attempting to scale {STATEFULSET_NAME} to {new_replica_count} replicas...")
    try:
        apps_v1.patch_namespaced_stateful_set_scale(
            STATEFULSET_NAME, NAMESPACE, {"spec": {"replicas": new_replica_count}}
        )
        logging.info(f"Successfully scaled {STATEFULSET_NAME} to {new_replica_count} replicas.")
        if direction == "up":
            last_scale_up_time = now
        else:
            last_scale_down_time = now
    except client.ApiException as e:
        logging.error(f"Failed to scale statefulset {STATEFULSET_NAME}: {e.body}")

logging.info(f"Starting GPU autoscaler for {STATEFULSET_NAME} in {NAMESPACE}")
while True:
    current_replicas = get_current_replicas()
    if current_replicas is None:
        logging.warning("Could not determine current replica count. Retrying in 30 seconds.")
        time.sleep(30)
        continue

    util = get_gpu_utilization()
    mem = get_gpu_memory_usage()

    util_str = f"{util:.2f}%" if util is not None else "N/A"
    mem_str = f"{mem:.2f}%" if mem is not None else "N/A"
    logging.info(f"State: Replicas={current_replicas}, GPU Util={util_str}, VRAM Usage={mem_str}")

    should_scale_up = util is not None and util > GPU_UTIL_HIGH or mem is not None and mem > GPU_MEM_HIGH
    should_scale_down = util is not None and util < GPU_UTIL_LOW and mem is not None and mem < GPU_MEM_LOW

    if should_scale_up and current_replicas < MAX_REPLICAS:
        logging.info("High load detected. Scaling UP.")
        scale_statefulset(current_replicas + 1, "up")
    elif should_scale_down and current_replicas > MIN_REPLICAS:
        logging.info("Low load detected. Scaling DOWN.")
        scale_statefulset(current_replicas - 1, "down")
    else:
        logging.info("No scaling action required.")

    time.sleep(CHECK_INTERVAL)