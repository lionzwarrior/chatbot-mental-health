# Chatbot-mental-health


## DNS Testing
kubectl run testdns --rm -it --image=busybox --restart=Never -- sh

nslookup kubernetes.default.svc.cluster.pakcarik


## Curl test
kubectl apply -f curl-pod.yaml

kubectl get pods curl-pod

kubectl exec -it curl-pod -- curl -X POST http://haproxy-service:8080/api/generate -d '{ "model": "llama3:8b", "prompt": "Say hi." }'

kubectl exec -it curl-pod -- curl -X POST http://ollama-model-headless-service:11434/api/generate -d '{ "model": "llama3:8b", "prompt": "Say hi." }' 

kubectl exec -it curl-pod -- curl -X POST -g 'http://prometheus-kube-prometheus-prometheus.remmanuel.svc.cluster.pakcarik:9090/api/v1/admin/tsdb/delete_series?match[]={__name__="chatbot_requests_total"}'


kubectl delete -f curl-pod.yaml


## Force delete namespace
kubectl get namespace gpu-operator -o json | jq '.spec.finalizers = []' | kubectl replace --raw "/api/v1/namespaces/gpu-operator/finalize" -f -


## Force delete a pod
kubectl delete pod haproxy-65774767b6-4snfq --force --grace-period=0


## PV + PVC & Mongodb + Qdrant
kubectl apply -f qdrant-nas-pv-remmanuel.yaml

kubectl apply -f qdrant-nas-pvc-remmanuel.yaml

kubectl apply -f mongodb-nas-pv-remmanuel.yaml

kubectl apply -f mongodb-nas-pvc-remmanuel.yaml

kubectl create secret generic mongodb-credentials -n remmanuel --from-literal=MONGO_USERNAME='admin' --from-literal=MONGO_PASSWORD='admin' --from-literal=MONGO_HOST='mongodb-service' --from-literal=MONGO_PORT='27017'


## Deployment Mongodb + Qdrant
kubectl apply -f mongodb-deployment-remmanuel.yaml

kubectl apply -f mongodb-service-remmanuel.yaml

kubectl apply -f qdrant-deployment-remmanuel.yaml

kubectl apply -f qdrant-service-remmanuel.yaml

kubectl exec -it mongodb-6b69b7d595-prql5 -n remmanuel -- mongosh


## Install Prometheus
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts

helm repo update

helm show values prometheus-community/kube-prometheus-stack > values.yaml

nano values.yaml

enableAdminAPI = false -> true

serviceMonitorSelectorNilUsesHelmValues = true -> false

helm install prometheus prometheus-community/kube-prometheus-stack --namespace remmanuel -f values.yaml


## Nvidia container toolkit
https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html

kubectl label node cn1 nvidia.com/gpu.deploy.driver=true

kubectl label node cn2 nvidia.com/gpu.deploy.driver=true

kubectl label node cn3 nvidia.com/gpu.deploy.driver=true

kubectl label node cn1 nvidia.com/gpu.deploy.container-toolkit=true

kubectl label node cn2 nvidia.com/gpu.deploy.container-toolkit=true

kubectl label node cn3 nvidia.com/gpu.deploy.container-toolkit=true


## GPU Operator + DCGM
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia && helm repo update

helm install --wait gpu-operator -n gpu-operator --create-namespace nvidia/gpu-operator

kubectl label node cn1 nvidia.com/gpu.deploy.dcgm-exporter=true --overwrite

kubectl label node cn2 nvidia.com/gpu.deploy.dcgm-exporter=true --overwrite

kubectl label node cn3 nvidia.com/gpu.deploy.dcgm-exporter=true --overwrite

kubectl get pods -n gpu-operator -o wide | grep device-plugin

kubectl -n gpu-operator rollout restart ds/nvidia-device-plugin-daemonset


## if GPU Operator need to be uninstalled
helm uninstall --wait gpu-operator -n gpu-operator

helm upgrade --install gpu-operator nvidia/gpu-operator -n gpu-operator --set driver.enabled=false --wait --timeout 10m


## Check GPU Count
kubectl get nodes -o=custom-columns=NAME:.metadata.name,GPU:.status.allocatable."nvidia\.com/gpu"


## Ollama model deployment
kubectl apply -f ollama-model-pv.yaml

kubectl apply -f ollama-model-pvc.yaml

kubectl apply -f ollama-nodel-prepull.yaml

kubectl apply -f ollama-model-deployment.yaml

kubectl apply -f ollama-model-service.yaml

kubectl port-forward svc/ollama-model-service 11434:11434 -n remmanuel

kubectl exec -it ollama-model-deployment-77c4894bc7-gwvrq -- /bin/bash


## Access grafana
kubectl get svc prometheus-grafana -o wide

kubectl get nodes -o wide

kubectl port-forward svc/prometheus-grafana 3000:80

kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090

ssh -L 3000:localhost:3000 -L 9090:localhost:9090 raphael@pakcarik.petra.ac.id

kubectl get secret prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 --decode; echo

password: prom-operator


## Prepare docker
docker login


## Setup Cookie
kubectl create secret generic cookie-secret --from-literal=encryption-password='r3mm4nu312025!'


## Docker build Chatbot Mental Heatlh Old
docker build -t lionzwarrior10/chatbot-mental-health-old:latest .

docker push lionzwarrior10/chatbot-mental-health-old:latest


## Docker build Chatbot Mental Heatlh
docker build -t lionzwarrior10/chatbot-mental-health:latest .

docker push lionzwarrior10/chatbot-mental-health:latest


## Docker build ollama-model-custom-hpa
docker build -t lionzwarrior10/ollama-model-custom-hpa .

docker push lionzwarrior10/ollama-model-custom-hpa


## Docker build custom-ollama
docker build -t lionzwarrior10/custom-ollama .

docker push lionzwarrior10/custom-ollama


## Deploy ollama-model-custom-hpa
kubectl apply -f ollama-model-custom-hpa-rbac.yaml

kubectl apply -f ollama-model-custom-hpa-deployment.yaml


## Deploy Chatbot custom-ollama
kubectl apply -f ollama-model-deployment-custom.yaml

kubectl apply -f ollama-model-service.yaml

kubectl apply -f ollama-model-headless-service.yaml


## Deploy Chatbot Mental Heatlh
kubectl apply -f chatbot-mental-health-haproxy-deployment.yaml

kubectl apply -f chatbot-mental-health-service.yaml


## Kubectl port forwarding
kubectl port-forward svc/prometheus-grafana 3000:80

kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090

kubectl port-forward svc/ollama-model-service 11434:11434

kubectl port-forward svc/mongodb-service 27017:27017

kubectl port-forward svc/qdrant-headless-service 6333:6333

kubectl port-forward svc/chatbot-mental-health-service 8501:80

ssh -L 3000:127.0.0.1:3000 raphael@pakcarik.petra.ac.id

ssh -L 6333:127.0.0.1:6333 raphael@pakcarik.petra.ac.id

ssh -L 9090:127.0.0.1:9090 raphael@pakcarik.petra.ac.id

ssh -L 3000:127.0.0.1:3000 -L 9090:127.0.0.1:9090 raphael@pakcarik.petra.ac.id

# Delete process after stopping port forwarding
ps aux | grep "kubectl port-forward" | grep -v grep

kill 887043

# Copy a file from a pod
kubectl cp chatbot-mental-health-789d6db6-n5xdm:/app/time_to_first_token_response_time.log ./time_to_first_token_response_time.log
kubectl cp chatbot-mental-health-789d6db6-n5xdm:/app/total_response_time.log ./total_response_time.log

## Reset counter
curl -X POST -g 'http://prometheus-kube-prometheus-prometheus.remmanuel.svc.cluster.pakcarik:9090/api/v1/admin/tsdb/delete_series?match[]={__name__="chatbot_requests_total"}'
