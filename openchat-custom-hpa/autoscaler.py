from kubernetes import client, config
from prometheus_api_client import PrometheusConnect
import time

# Prometheus connection
prom = PrometheusConnect(url="http://prometheus-operated.remmanuel.svc.cluster.pakcarik:9090", disable_ssl=True)

# Kubernetes API client
config.load_incluster_config()
apps_v1 = client.AppsV1Api()

# Configuration constants
DEPLOYMENT_NAME = "ollama-openchat-deployment"
NAMESPACE = "remmanuel"

# Thresholds for scaling
# For CPU and GPU, you might want distinct thresholds or use the same for simplicity.
CPU_LOW_THRESHOLD = 20
CPU_HIGH_THRESHOLD = 70
GPU_LOW_THRESHOLD = 20
GPU_HIGH_THRESHOLD = 70

# Replica limits
MIN_REPLICAS = 1
MAX_REPLICAS = 6

def scale_to(n):
    """Scales the deployment to the specified number of replicas."""
    print(f"Scaling {DEPLOYMENT_NAME} in namespace {NAMESPACE} to {n} replicas")
    body = {"spec": {"replicas": n}}
    try:
        apps_v1.patch_namespaced_deployment_scale(name=DEPLOYMENT_NAME, namespace=NAMESPACE, body=body)
        print(f"Successfully scaled to {n} replicas.")
    except client.ApiException as e:
        print(f"Error scaling deployment: {e}")

def get_current_replicas():
    """Retrieves the current number of replicas for the deployment."""
    try:
        deployment = apps_v1.read_namespaced_deployment(name=DEPLOYMENT_NAME, namespace=NAMESPACE)
        return deployment.spec.replicas
    except client.ApiException as e:
        print(f"Error getting current replicas: {e}")
        return None

def get_cpu_utilization():
    """Fetches the average CPU utilization for the deployment's pods."""
    # This query assumes you have cAdvisor metrics or similar for CPU usage.
    # You might need to adjust the metric name and labels based on your Prometheus setup.
    # A common metric for pod CPU usage is 'pod_cpu_usage_seconds_total' or 'node_cpu_seconds_total'
    # aggregated by pod/container. For simplicity, let's use a common one.
    # We are looking for CPU usage as a percentage, so a rate is needed.
    # Let's assume a metric that gives CPU usage in cores, and we convert to percentage
    # based on the CPU limits or requests if available, or just as a raw utilization.
    # For a percentage, you typically divide by the number of CPU cores requested/limited.
    # A simpler approach for percentage could be using 'kube_pod_container_resource_requests_cpu_cores'
    # and 'sum(rate(container_cpu_usage_seconds_total...))'
    # For a simple utilization percentage from Prometheus:
    try:
        # Example query: Average CPU utilization across all containers in the deployment
        # You might need to adjust this query based on how your CPU metrics are exposed.
        # This query gets the average CPU utilization of pods belonging to the deployment.
        # It aggregates 'container_cpu_usage_seconds_total' and divides by the number of CPU cores.
        # This is a more robust way to get a percentage if you have resource requests set.
        # If you don't have resource requests/limits, you might have to adapt.
        # For a more direct percentage if available, you might use 'container_cpu_usage_percentage'
        # or similar from your monitoring setup.
        # Here's a common way to calculate CPU utilization percentage from `container_cpu_usage_seconds_total`
        # and `kube_pod_container_resource_requests_cpu_cores`:
        cpu_query = (
            f'sum(rate(container_cpu_usage_seconds_total{{namespace="{NAMESPACE}", '
            f'pod=~"{DEPLOYMENT_NAME}.*"}}[5m])) by (pod) / '
            f'kube_pod_container_resource_requests_cpu_cores{{namespace="{NAMESPACE}", '
            f'pod=~"{DEPLOYMENT_NAME}.*"}} * 100'
        )
        result = prom.get_current_metric_value(cpu_query)
        if result:
            # We want an average across all pods for the deployment, so average the results
            total_cpu_util = 0
            count = 0
            for item in result:
                if item['value'][1]:
                    total_cpu_util += float(item['value'][1])
                    count += 1
            if count > 0:
                return total_cpu_util / count
    except Exception as e:
        print(f"Error fetching CPU utilization: {e}")
    return None

def get_gpu_utilization():
    """Fetches the average GPU utilization for the deployment's pods."""
    try:
        # Your existing GPU query
        gpu_query = f'avg(DCGM_FI_DEV_GPU_UTIL{{namespace="{NAMESPACE}",pod=~"{DEPLOYMENT_NAME}.* বিস্ফোরণ"}})'
        result = prom.get_current_metric_value(gpu_query)
        if result and result[0]['value'][1]:
            return float(result[0]['value'][1])
    except Exception as e:
        print(f"Error fetching GPU utilization: {e}")
    return None

while True:
    try:
        current_replicas = get_current_replicas()
        if current_replicas is None:
            print("Could not retrieve current replica count. Skipping scaling iteration.")
            time.sleep(60)
            continue

        cpu_util = get_cpu_utilization()
        gpu_util = get_gpu_utilization()

        print(f"Current Replicas: {current_replicas}")
        print(f"CPU Utilization: {cpu_util if cpu_util is not None else 'N/A'}%")
        print(f"GPU Utilization: {gpu_util if gpu_util is not None else 'N/A'}%")

        should_scale_up = False
        should_scale_down = False

        # Scaling logic based on CPU
        if cpu_util is not None:
            if cpu_util > CPU_HIGH_THRESHOLD and current_replicas < MAX_REPLICAS:
                should_scale_up = True
                print(f"CPU utilization ({cpu_util:.2f}%) is high. Considering scale up.")
            elif cpu_util < CPU_LOW_THRESHOLD and current_replicas > MIN_REPLICAS:
                should_scale_down = True
                print(f"CPU utilization ({cpu_util:.2f}%) is low. Considering scale down.")

        # Scaling logic based on GPU
        if gpu_util is not None:
            if gpu_util > GPU_HIGH_THRESHOLD and current_replicas < MAX_REPLICAS:
                should_scale_up = True
                print(f"GPU utilization ({gpu_util:.2f}%) is high. Considering scale up.")
            elif gpu_util < GPU_LOW_THRESHOLD and current_replicas > MIN_REPLICAS:
                should_scale_down = True
                print(f"GPU utilization ({gpu_util:.2f}%) is low. Considering scale down.")

        # Combine scaling decisions
        # If either CPU or GPU is high, scale up.
        # If BOTH CPU and GPU are low, scale down. (This prevents flapping if one is low and other is medium)
        if should_scale_up:
            print("Scaling up due to high CPU or GPU utilization.")
            scale_to(current_replicas + 1)
        elif should_scale_down and (cpu_util is None or cpu_util < CPU_LOW_THRESHOLD) and \
                             (gpu_util is None or gpu_util < GPU_LOW_THRESHOLD):
            # Only scale down if both metrics are low or one is low and the other is not available.
            # This avoids scaling down if one metric is low but the other is still high.
            print("Scaling down due to low CPU and GPU utilization.")
            scale_to(current_replicas - 1)
        else:
            print("No scaling action needed at this time.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    time.sleep(60)