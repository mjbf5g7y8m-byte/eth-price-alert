FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY eth_price_alert.py .

CMD ["python", "eth_price_alert.py"]

