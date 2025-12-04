FROM python:3.11-slim

WORKDIR /app

# pre-install build dependencies and system libraries needed for running chromium
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    fonts-noto-color-emoji \
    libatk-bridge2.0-0 libatk1.0-0 \
    libcups2 libdrm2 libdbus-1-3 \
    libgbm1 libgtk-3-0 libnss3 \
    libxcomposite1 libxdamage1 libxfixes3 \
    libxkbcommon0 libxrandr2 libxshmfence1 \
    libasound2 libpango-1.0-0 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

# install chromium with playwright
RUN playwright install --with-deps chromium

COPY ./app ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]