# Проект фудграм
Сайт, на котором пользователи могут публиковать свои рецепты, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. Зарегистрированным пользователям доступен сервис «Список покупок». Он позволяет создавать список продуктов, которые нужно купить для приготовления выбранных блюд.

## Технологии

- Python
- Django REST Framework
- Gunicorn
- SQLite
- PostgreSQL
- Nginx
- Docker
- GitHub Actions

## Локальное развертывание

### 1. Клонировать репозиторий и перейти в него в командной строке:
```bash
git clone https://github.com/AndreevnaI/foodgram.git

cd foodgram
```

#### 2. Запустить фронтенд:
```bash
cd frontend
npm i
npm run start
```

#### 3. Запустить бэкенд. Cоздать и активировать виртуальное окружение:
##### Обязательно в новом терминале!
```bash
cd backend
```

```bash
python -m venv venv
```

- На Windows:
```bash
venv\Scripts\activate
```
- На macOS/Linux:
```bash
source venv/bin/activate
```

- Установить зависимости из файла requirements.txt и выполнить миграции:
```bash
python -m pip install --upgrade pip

pip install -r requirements.txt
```

```bash
python manage.py migrate
```

- Запустить проект:
```bash
python manage.py runserver
```

После запуска проекта будет доступна документация для API по адресу:

```url
http://localhost/api/docs
```


- [Ирина Ильина](https://github.com/AndreevnaI) (в роли Python-разработчика)