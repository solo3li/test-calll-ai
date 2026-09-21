FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir --default-timeout=120 -r requirements.txt

COPY . /app/

EXPOSE 8000 8002

CMD ["sh", "-c", "python manage.py migrate && python manage.py seed_data && python mcp_server.py & python manage.py runserver 0.0.0.0:8000"]
