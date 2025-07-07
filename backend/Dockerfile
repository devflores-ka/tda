# Usa una imagen base de Python
FROM python:3.9-slim

# Establece variables de entorno
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instala las dependencias del sistema operativo, incluyendo pkg-config
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Crea y establece el directorio de trabajo
WORKDIR /app

# Instala las dependencias de Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código del proyecto al contenedor
COPY . /app/