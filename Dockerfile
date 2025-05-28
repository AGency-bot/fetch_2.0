# Bazowy obraz z Pythonem + Playwright
FROM mcr.microsoft.com/playwright/python:v1.52.0-jammy

# Ustaw katalog roboczy
WORKDIR /app

# Skopiuj wymagane pliki
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Skopiuj całość projektu
COPY . .

# Ustaw domyślny port Render (dynamiczny przez ENV)
ENV PORT=8080

# Playwright: upewnij się, że zależności i przeglądarki są zainstalowane
RUN playwright install --with-deps

# Domyślny command (można nadpisać w render.yaml)
CMD ["python", "SERVER.py"]
