FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY copilot/ copilot/
COPY .env* .

EXPOSE 8000

CMD ["uvicorn", "copilot.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
