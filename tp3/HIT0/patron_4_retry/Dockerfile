FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir pika==1.3.2
COPY producer.py consumer_retry.py ./
