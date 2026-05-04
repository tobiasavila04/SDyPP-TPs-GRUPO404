FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY master.py .
# La imagen de prueba debe copiarse antes del build:
# cp ../imagen_prueba.jpg .
COPY imagen_prueba.jpg .
CMD ["python", "master.py"]
