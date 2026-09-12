# 1. Imagen base: Python ya instalado, versión slim (más ligera)
FROM python:3.12-slim

# 2. Variables de entorno recomendadas para Python en contenedores
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Carpeta de trabajo dentro del contenedor
WORKDIR /app

# 4. Copiamos primero solo requirements.txt (aprovecha el cache de Docker)
COPY requirements.txt .

# 5. Instalamos las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copiamos el resto del código del proyecto
COPY . .

# 7. Puerto que Django usará dentro del contenedor
EXPOSE 8000

# 8. Comando por defecto al iniciar el contenedor
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]