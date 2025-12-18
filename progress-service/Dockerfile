FROM python:3.11-slim

WORKDIR /app

RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install --no-cache-dir \
    --timeout=100 \
    -r requirements.txt
    
COPY . .

CMD ["python", "progress_worker.py"]
