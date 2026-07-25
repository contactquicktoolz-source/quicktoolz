FROM python:3.11-slim

# System dependencies: LibreOffice (word to pdf) + ffmpeg (audio converter)
RUN apt-get update && apt-get install -y \
    libreoffice \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--timeout", "120", "app:app"]