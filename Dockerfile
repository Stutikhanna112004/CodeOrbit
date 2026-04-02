# Use Python 3.11 slim — stable and well-supported
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Set environment variables
# PYTHONDONTWRITEBYTECODE — stops Python writing .pyc files
# PYTHONUNBUFFERED — logs appear instantly, not buffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies PostgreSQL needs
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first — Docker caches this layer
# so it only reinstalls packages if requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Collect static files for WhiteNoise to serve
RUN python manage.py collectstatic --noinput

# Expose port 8000
EXPOSE 8000

# Start with Daphne — supports HTTP + WebSockets
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "core.asgi:application"]