FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    git \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade-strategy eager -r requirements.txt \
    && pip cache purge

RUN pip install --no-cache-dir --upgrade tqdm huggingface_hub

COPY src ./src
COPY docs ./docs
COPY asset ./asset
COPY .streamlit/secrets.toml.template ./.streamlit/secrets.toml.template
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8501
EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.baseUrlPath=/chatbot-mental-health"]