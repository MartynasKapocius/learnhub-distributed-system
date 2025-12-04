# Python base image.
FROM python:3.10-slim

# Work directory.
WORKDIR /app

# Install dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY . .

# Environment defaults.
ENV MONGO_URI=mongodb://mongo:27017/learnhub_dev
ENV RABBITMQ_HOST=rabbitmq
ENV EVENT_EXCHANGE=learning_events

# Run the service.
CMD ["python", "app.py"]