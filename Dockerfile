FROM python:3.9-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Archivos Python
COPY app.py /app/
COPY mongo_utils.py /app/
COPY cassandra_utils.py /app/
COPY requirements.txt /app/

# Archivos WEB
COPY static /app/static
COPY templates /app/templates

# Cassandra
COPY cassandra /app/cassandra

# Instalar las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto 5000
EXPOSE 5000

# Comando para ejecutar la aplicación
CMD ["python", "app.py"]