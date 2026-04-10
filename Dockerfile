FROM python:3.10-slim-bullseye

# Install Chrome and dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    gnupg \
    xvfb \
    ca-certificates \
    --no-install-recommends \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install ChromeDriver - FIXED VERSION
RUN apt-get update && apt-get install -y chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV CHROME_BIN=/usr/bin/google-chrome-stable \
    CHROME_PATH=/usr/bin/google-chrome-stable \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:99 \
    RENDER=true

# Create non-root user for security
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app && \
    mkdir -p /home/botuser/.cache && \
    chown -R botuser:botuser /home/botuser

# Switch to non-root user
USER botuser

# Expose port
EXPOSE 8000

# Run with gunicorn
CMD ["gunicorn", "app:app", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "1", \
     "--threads", "2", \
     "--timeout", "120"]
