import os, time, logging
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
DEPLOYMENT_NAME, NAMESPACE = os.getenv(
    "DEPLOYMENT_NAME", "ollama-model-deployment"
), os.getenv("NAMESPACE", "remmanuel")
PROMETHEUS_URL = f"http://{os.getenv('PROMETHEUS_SERVICE_NAME', 'prometheus-operated')}.{NAMESPACE}.svc.cluster.pakcarik:{os.getenv('PROMETHEUS_PORT', '9090')}"

try:
    prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)
    prom.check_prometheus_connection()
    logging.info(f"Connected to Prometheus at: {PROMETHEUS_URL}")
except PrometheusApiClientException as e:
    logging.error(f"Failed to connect to Prometheus: {e}")
    exit(1)

GPU_UTIL_HIGH, GPU_UTIL_LOW = float(os.getenv("GPU_UTIL_HIGH_THRESHOLD", "70")), float(
    os.getenv("GPU_UTIL_LOW_THRESHOLD", "40")
)
GPU_MEM_HIGH, GPU_MEM_LOW = float(os.getenv("GPU_MEM_HIGH_THRESHOLD", "85")), float(
    os.getenv("GPU_MEM_LOW_THRESHOLD", "50")
)
MIN_REPLICAS, MAX_REPLICAS, SCALE_COOLDOWN = (
    int(os.getenv("MIN_REPLICAS", "1")),
    int(os.getenv("MAX_REPLICAS", "3")),
    int(os.getenv("SCALE_COOLDOWN_SECONDS", "60")),
)


def query(q, name):
    try:
        r = prom.custom_query(q)
        if not r or "value" not in r[0]:
            return None
        return float(r[0]["value"][1])
    except Exception as e:
        logging.error(f"Prometheus query error for {name}: {e}")
        return None


def gpu_util():
    return query(
        f'avg(DCGM_FI_DEV_GPU_UTIL{{exported_namespace="{NAMESPACE}",exported_pod=~"{DEPLOYMENT_NAME}-.*"}})',
        "GPU Util",
    )


def gpu_mem():
    return query(
        f'(avg(DCGM_FI_DEV_FB_USED{{exported_namespace="{NAMESPACE}",exported_pod=~"{DEPLOYMENT_NAME}-.*"}}) / '
        f'(avg(DCGM_FI_DEV_FB_USED{{exported_namespace="{NAMESPACE}",exported_pod=~"{DEPLOYMENT_NAME}-.*"}}) + '
        f'avg(DCGM_FI_DEV_FB_FREE{{exported_namespace="{NAMESPACE}",exported_pod=~"{DEPLOYMENT_NAME}-.*"}}))) * 100',
        "GPU Mem",
    )


def replicas():
    try:
        return apps_v1.read_namespaced_deployment(
            DEPLOYMENT_NAME, NAMESPACE
        ).spec.replicas
    except:
        return None


last_scale_up, last_scale_down = 0, 0


def scale(n, direction):
    global last_scale_up, last_scale_down
    now = time.time()
    if direction == "up" and now - last_scale_up < SCALE_COOLDOWN:
        return
    if direction == "down" and now - last_scale_down < SCALE_COOLDOWN:
        return
    apps_v1.patch_namespaced_deployment_scale(
        DEPLOYMENT_NAME, NAMESPACE, {"spec": {"replicas": n}}
    )
    logging.info(f"Scaled {DEPLOYMENT_NAME} to {n}")
    if direction == "up":
        last_scale_up = now
    else:
        last_scale_down = now


logging.info(f"Starting GPU autoscaler for {DEPLOYMENT_NAME} in {NAMESPACE}")
while True:
    cur = replicas()
    if cur is None:
        time.sleep(30)
        continue
    util, mem = gpu_util(), gpu_mem()
    util_str = f"{util:.2f}%" if util is not None else "N/A"
    mem_str = f"{mem:.2f}%" if mem is not None else "N/A"
    logging.info(f"Replicas={cur}, GPU Util={util_str}, VRAM={mem_str}")

    up = util and util > GPU_UTIL_HIGH or mem and mem > GPU_MEM_HIGH
    down = util and util < GPU_UTIL_LOW and mem and mem < GPU_MEM_LOW
    if up and cur < MAX_REPLICAS:
        scale(cur + 1)
    elif down and cur > MIN_REPLICAS:
        scale(cur - 1)
    else:
        logging.info("No scaling action.")
    time.sleep(60)
