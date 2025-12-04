FROM python:3.10-slim
WORKDIR /app
COPY user-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY user-service/ .
CMD ["python", "app.py"]
