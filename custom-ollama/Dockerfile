FROM ollama/ollama:latest

RUN ollama serve & \
    sleep 8 && \
    ollama pull openchat:7b && \
    ollama pull llama3:8b && \
    pkill ollama
