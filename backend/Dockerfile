FROM python:3.9

WORKDIR /app

RUN pip install gunicorn==20.1.0

COPY requirements.txt .

RUN pip3 install -r requirements.txt --no-cache-dir

COPY . .

RUN python manage.py collectstatic

CMD ["gunicorn", "--bind", "0:8000", "foodgram.wsgi:application"]
