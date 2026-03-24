FROM python:3.10

WORKDIR /app

COPY . .

RUN pip install Flask flask-socketio eventlet

EXPOSE 5000

CMD ["python", "app.py"]