# Bruk slank Python-base
FROM python:3.11-slim
 
# Unngå .pyc-filer og bufret output i Docker-logger
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
 
# Sett arbeidsmappe inne i containeren
WORKDIR /app
 
# Kopier og installer avhengigheter først
# (Docker cacher dette laget hvis requirements.txt ikke endres)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
# Kopier resten av koden
COPY . .
 
# Start servicen
CMD ["python", "main.py"]