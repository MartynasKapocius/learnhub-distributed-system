# Python base image.
FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Work directory.
WORKDIR /app

# Install dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY . .

# Environment defaults.
ENV RABBITMQ_HOST=rabbitmq
ENV EVENT_EXCHANGE=learning_events

# Run the service.
CMD ["python", "app.py"]