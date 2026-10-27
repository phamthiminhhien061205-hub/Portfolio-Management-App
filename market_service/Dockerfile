FROM python:3.12-slim

WORKDIR /app

COPY market_service/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY market_service /app/market_service

EXPOSE 8001

CMD ["uvicorn", "market_service.main:app", "--host", "0.0.0.0", "--port", "8001"]