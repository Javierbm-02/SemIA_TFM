# Usa Python 3.11 slim para mantener la imagen ligera
FROM python:3.11-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar dependencias y ejecutarlas para aprovechar la caché de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el contenido de la web y modelo
COPY . .

# Variables de entorno
ENV PYTHONIOENCODING=utf-8
ENV FLASK_ENV=production

# Exponer el puerto
EXPOSE 5001

# Ejecutar con gunicorn (recibe el puerto de Cloud Run a través de $PORT)
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 120 app:app
