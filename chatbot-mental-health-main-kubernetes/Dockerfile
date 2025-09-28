FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libmagic-dev \
    poppler-utils \
    tesseract-ocr \
    libreoffice \
    libgl1-mesa-glx \
    libglib2.0-0 \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY docs ./docs
COPY asset ./asset
COPY .streamlit/secrets.toml.template ./.streamlit/secrets.toml.template
COPY .streamlit/config.toml ./.streamlit/config.toml

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8080
EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

CMD ["streamlit", "run", "src/app.py"]