# chatbot-mental-health

curl -v http://localhost:11434/api/generate -H "Content-Type: application/json" -d "{\"model\":\"llama3.1\", \"prompt\":\"Why is the sky blue?\", \"options\": {\"num_ctx\": 2048}, \"stream\": false}"

# DNS Testing
kubectl run testdns --rm -it --image=busybox --restart=Never -- sh
nslookup kubernetes.default.svc.cluster.pakcarik

# Curl test
kubectl apply -f curl-pod.yaml
kubectl get pods curl-pod
kubectl exec -it curl-pod -- curl -X POST http://ollama-model-service.remmanuel.svc.cluster.pakcarik:11434/api/generate -d '{ "model": "llama3.1:latest", "prompt": "Say hi." }'  
kubectl delete -f curl-pod.yaml

# force delete namespace
kubectl get namespace gpu-operator -o json \
  | jq '.spec.finalizers = []' \
  | kubectl replace --raw "/api/v1/namespaces/gpu-operator/finalize" -f -

# force delete a pod
kubectl delete pod ollama-model-deployment-94d78f948-2g469 --force --grace-period=0

# PV + PVC & mongodb + qdrant
kubectl apply -f qdrant-nas-pv-remmanuel.yaml
kubectl apply -f qdrant-nas-pvc-remmanuel.yaml
kubectl apply -f mongodb-nas-pv-remmanuel.yaml
kubectl apply -f mongodb-nas-pvc-remmanuel.yaml
kubectl create secret generic mongodb-credentials -n remmanuel \
  --from-literal=MONGO_USERNAME='admin' \
  --from-literal=MONGO_PASSWORD='admin' \
  --from-literal=MONGO_HOST='mongodb-service' \
  --from-literal=MONGO_PORT='27017'

# Deployment mongodb + qdrant
kubectl apply -f mongodb-deployment-remmanuel.yaml
kubectl apply -f mongodb-service-remmanuel.yaml
kubectl apply -f qdrant-deployment-remmanuel.yaml
kubectl apply -f qdrant-service-remmanuel.yaml
kubectl exec -it mongodb-6b69b7d595-prql5 -n remmanuel -- mongosh

# Check
kubectl get pods -n remmanuel
kubectl get pvc -n remmanuel
kubectl get deployment -n remmanuel
kubectl get service -n remmanuel

# Install Prometheus
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace remmanuel \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
  --set grafana.enabled=true
NAME: prometheus
LAST DEPLOYED: Tue Jun  3 16:14:23 2025
NAMESPACE: remmanuel
STATUS: deployed
REVISION: 1
NOTES:
kube-prometheus-stack has been installed. Check its status by running:
  kubectl --namespace remmanuel get pods -l "release=prometheus"

Get Grafana 'admin' user password by running:

  kubectl --namespace remmanuel get secrets prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d ; echo

Access Grafana local instance:

  export POD_NAME=$(kubectl --namespace remmanuel get pod -l "app.kubernetes.io/name=grafana,app.kubernetes.io/instance=prometheus" -oname)
  kubectl --namespace remmanuel port-forward $POD_NAME 3000

Visit https://github.com/prometheus-operator/kube-prometheus for instructions on how to create & configure Alertmanager and Prometheus instances using the Operator.

# Install Prometheus Adapter
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus-adapter prometheus-community/prometheus-adapter \
  --namespace remmanuel \
  --values ./prometheus-adapter-values.yaml

# Nvidia container toolkit
https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
kubectl label node cn1 nvidia.com/gpu.deploy.driver=true
kubectl label node cn2 nvidia.com/gpu.deploy.driver=true
kubectl label node cn3 nvidia.com/gpu.deploy.driver=true
kubectl label node cn1 nvidia.com/gpu.deploy.container-toolkit=true
kubectl label node cn2 nvidia.com/gpu.deploy.container-toolkit=true
kubectl label node cn3 nvidia.com/gpu.deploy.container-toolkit=true

# GPU Operator + DCGM
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia && helm repo update
helm install --wait gpu-operator -n gpu-operator --create-namespace nvidia/gpu-operator
kubectl label node cn1 nvidia.com/gpu.deploy.dcgm-exporter=true --overwrite
kubectl label node cn2 nvidia.com/gpu.deploy.dcgm-exporter=true --overwrite
kubectl label node cn3 nvidia.com/gpu.deploy.dcgm-exporter=true --overwrite
kubectl get pods -n gpu-operator -o wide | grep device-plugin
kubectl -n gpu-operator rollout restart ds/nvidia-device-plugin-daemonset

helm uninstall --wait gpu-operator -n gpu-operator

helm upgrade --install gpu-operator \
  nvidia/gpu-operator \
  -n gpu-operator \
  --set driver.enabled=false \
  --wait \
  --timeout 10m

# Check GPU
kubectl get nodes -o=custom-columns=NAME:.metadata.name,GPU:.status.allocatable."nvidia\.com/gpu"

# Ollama model deployment
kubectl apply -f ollama-model-pv.yaml
kubectl apply -f ollama-model-pvc.yaml
kubectl apply -f ollama-nodel-prepull.yaml
kubectl apply -f ollama-model-deployment.yaml
kubectl apply -f ollama-model-service.yaml
kubectl port-forward svc/ollama-model-service 11434:11434 -n remmanuel
curl http://localhost:11434/api/tags
kubectl exec -it ollama-model-deployment-77c4894bc7-gwvrq -- /bin/bash


# Access grafana
kubectl edit svc prometheus-grafana
type: ClusterIP -> LoadBalancer
kubectl get svc prometheus-grafana -o wide
kubectl get nodes -o wide
kubectl port-forward svc/prometheus-grafana 3000:80
kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090
ssh -L 3000:localhost:3000 -L 9090:localhost:9090 raphael@pakcarik.petra.ac.id
kubectl get secret prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 --decode; echo
password: prom-operator

# Prepare docker
docker login

# Docker build Ollama Autotune
docker build -t lionzwarrior10/ollama-autotune:latest .
docker push lionzwarrior10/ollama-autotune:latest

# Docker build Chatbot Mental Heatlh
docker build -t lionzwarrior10/chatbot-mental-health:latest .
docker push lionzwarrior10/chatbot-mental-health:latest

# Docker build ollama-model-custom-hpa
docker build -t lionzwarrior10/ollama-model-custom-hpa .
docker push lionzwarrior10/ollama-model-custom-hpa

# Deploy ollama-model-custom-hpa
kubectl apply -f ollama-model-custom-hpa-rbac.yaml
kubectl apply -f ollama-model-custom-hpa-deployment.yaml

# Kubectl port forwarding
kubectl port-forward svc/prometheus-grafana 3000:80
kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090
kubectl port-forward svc/ollama-model-service 11434:11434
kubectl port-forward svc/ollama-openchat-service 11435:11434
kubectl port-forward svc/mongodb-service 27017:27017
kubectl port-forward svc/qdrant-service 6333:6333
kubectl port-forward svc/chatbot-mental-health-service 8501:80

kubectl port-forward svc/prometheus-grafana 3000:80 & \
kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090 & \
kubectl port-forward svc/ollama-model-service 11434:11434 & \
kubectl port-forward svc/mongodb-service 27017:27017 & \
kubectl port-forward svc/qdrant-service 6333:6333 & \
kubectl port-forward svc/chatbot-mental-health-service 8501:80

ssh -L 27017:127.0.0.1:27017 -L 6333:127.0.0.1:6333 -L 11434:127.0.0.1:11434 -L 27017:127.0.0.1:27017 -L 6333:127.0.0.1:6333 -L 8501:127.0.0.1:8501 -L 3000:127.0.0.1:3000 -L 9090:127.0.0.1:9090  raphael@pakcarik.petra.ac.id

ssh -L 27017:127.0.0.1:27017 raphael@pakcarik.petra.ac.id
ssh -L 6333:127.0.0.1:6333 raphael@pakcarik.petra.ac.id

# Delete process after stopping port forwarding
ps aux | grep "kubectl port-forward" | grep -v grep
kill 887043
