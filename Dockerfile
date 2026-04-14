# Verwende ein offizielles, leichtgewichtiges Python-Image
FROM python:3.13-slim

# Arbeitsverzeichnis im Container festlegen
WORKDIR /app

# Quellcode in den Container kopieren
COPY core/ /app/core/
COPY log/ /app/log/
COPY net/ /app/net/
COPY ux/ /app/ux/
COPY main.py /app/

# Benötigte Verzeichnisse erstellen
RUN mkdir -p /app/logs /app/config

# Umgebungsvariablen setzen (können in docker-compose überschrieben werden)
ENV TELCHAT_HOST=0.0.0.0
ENV TELCHAT_PORT=9999
ENV TELCHAT_CONFIG=/app/config/agents.json
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Port freigeben, auf dem der Server lauscht
EXPOSE 9999

# Startbefehl
CMD ["python", "main.py"]
