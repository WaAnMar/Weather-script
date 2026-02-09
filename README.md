# Weather Service API

HTTP-сервер для предоставления информации о погоде с использованием Open-Meteo API.

## Установка и запуск

1. Установите зависимости:
```bash
pip install -r requirements.txt

# Weather Service API

HTTP-сервер для предоставления информации о погоде с использованием Open-Meteo API. Сервер реализован на FastAPI и предоставляет REST API для получения текущей погоды, отслеживания прогнозов для городов и многопользовательской работы.

## Содержание
1. [Функциональные возможности](#функциональные-возможности)
2. [Технологический стек](#технологический-стек)
3. [Установка и запуск](#установка-и-запуск)
4. [API Endpoints](#api-endpoints)
5. [Примеры использования](#примеры-использования)
6. [Структура базы данных](#структура-базы-данных)
7. [Архитектура и принцип работы](#архитектура-и-принцип-работы)
8. [Запуск тестов](#запуск-тестов)
9. [Решение проблем](#решение-проблем)

## Функциональные возможности

#Основные функции:
1. Получение текущей погоды - по координатам возвращает температуру, скорость ветра и атмосферное давление
2. Управление списком городов - добавление и просмотр городов для отслеживания погоды
3. Автоматическое обновление прогнозов - обновление данных каждые 15 минут
4. Получение прогноза по времени - погода для города в указанное время суток
5. Выбор параметров погоды - возможность запросить только нужные параметры (температура, влажность и т.д.)

#Дополнительные функции:
1. Многопользовательский режим - каждый пользователь имеет свой список городов
2. Поддержка SQLite - данные хранятся в файловой базе данных, не требующей дополнительной настройки
3. Автоматическая документация API - доступна через Swagger UI и ReDoc
4. Юнит-тесты - покрытие основных сценариев работы

## Технологический стек

- FastAPI - веб-фреймворк для создания API
- Uvicorn - ASGI-сервер для запуска приложения
- SQLite - база данных для хранения информации
- APScheduler - планировщик задач для обновления погоды
- HTTPX - асинхронный HTTP-клиент для запросов к Open-Meteo API
- Pydantic - валидация данных и работа с моделями
- Pytest - фреймворк для тестирования

#Установка

1. Клонируйте или создайте папку проекта:
```bash
mkdir weather-server
cd weather-server
```

2. Создайте файл requirements.txt:
```bash
echo "fastapi==0.104.1
uvicorn==0.24.0
httpx==0.25.1
pydantic==2.5.0
pytest==7.4.3
pytest-asyncio==0.21.1
apscheduler==3.10.4" > requirements.txt
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

#Запуск сервера

Способ 1: Прямой запуск
```bash
python3 script.py
```

Способ 2: Через Uvicorn
```bash
uvicorn script:app --host 127.0.0.1 --port 8000 --reload
```

После запуска сервер будет доступен по адресу: `http://127.0.0.1:8000`

#Документация API

После запуска сервера доступна автоматически сгенерированная документация:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## API Endpoints

#1. Проверка работоспособности
GET `/health`

Возвращает статус сервера и текущее время.

Пример ответа:
```json
{
  "status": "ok",
  "time_strstamp": "2024-01-15T14:30:45.123456"
}
```

#2. Получение текущей погоды по координатам
GET `/weather/current`

Параметры:
- `latitude` (обязательный) - широта в градусах
- `longitude` (обязательный) - долгота в градусах

Пример запроса:
```bash
GET /weather/current?latitude=55.7558&longitude=37.6173
```

Пример ответа:
```json
{
  "temperature": 5.2,
  "windspeed": 12.5,
  "pressure": 1013.25,
  "time_str": "2024-01-15T14:30:00"
}
```

#3. Регистрация пользователя
POST `/users/register`

Тело запроса (JSON):
```json
{
  "username": "имя_пользователя"
}
```

Пример ответа:
```json
{
  "user_id": 1,
  "username": "ivan_petrov"
}
```

#4. Добавление города для отслеживания
POST `/cities`

Query параметры:
- `user_id` (опциональный) - ID пользователя. Если не указан, город добавляется в общий список.

Тело запроса (JSON):
```json
{
  "name": "Москва",
  "latitude": 55.7558,
  "longitude": 37.6173
}
```

Пример ответа:
```json
{
  "message": "City added successfully",
  "city_id": 1,
  "user_id": 1
}
```

#5. Получение списка городов
GET `/cities`

Query параметры:
- `user_id` (опциональный) - ID пользователя. Если не указан, возвращает общие города.

Пример ответа:
```json
[
  {
    "id": 1,
    "name": "Москва",
    "latitude": 55.7558,
    "longitude": 37.6173
  },
  {
    "id": 2,
    "name": "Санкт-Петербург",
    "latitude": 59.9343,
    "longitude": 30.3351
  }
]
```

#6. Получение погоды для города
GET `/cities/{city_name}/weather`

Параметры:
- `city_name` (в пути) - название города
- `time_str` (обязательный) - время в формате "HH:MM" (например, "14:30")
- `fields` (опциональный) - список параметров через запятую (temperature, humidity, windspeed, precipitation, pressure)
- `user_id` (опциональный) - ID пользователя

Пример запроса:
```bash
GET /cities/Москва/weather?time_str=14:00&fields=temperature,humidity&user_id=1
```

Пример ответа:
```json
{
  "temperature": 5.5,
  "humidity": 65
}
```

## Примеры использования

#Пример 1: Полный рабочий процесс

```bash
# 1. Запускаем сервер (в первом окне терминала)
python3 script.py

# 2. Проверяем работоспособность (во втором окне терминала)
curl http://127.0.0.1:8000/health

# 3. Регистрируем пользователя
curl -X POST "http://127.0.0.1:8000/users/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "alex"}'

# 4. Добавляем город для пользователя
curl -X POST "http://127.0.0.1:8000/cities?user_id=1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Москва",
    "latitude": 55.7558,
    "longitude": 37.6173
  }'

# 5. Получаем список городов пользователя
curl "http://127.0.0.1:8000/cities?user_id=1"

# 6. Получаем погоду для Москвы в 14:00
curl "http://127.0.0.1:8000/cities/Москва/weather?time_str=14:00&user_id=1"

# 7. Получаем только температуру и влажность
curl "http://127.0.0.1:8000/cities/Москва/weather?time_str=14:00&fields=temperature,humidity&user_id=1"
```

#Пример 2: Работа без регистрации пользователя

```bash
# 1. Получаем текущую погоду по координатам
curl "http://127.0.0.1:8000/weather/current?latitude=55.7558&longitude=37.6173"

# 2. Добавляем город без указания пользователя
curl -X POST "http://127.0.0.1:8000/cities" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Лондон",
    "latitude": 51.5074,
    "longitude": -0.1278
  }'

# 3. Получаем общий список городов
curl "http://127.0.0.1:8000/cities"
```

#Пример 3: Использование Python для работы с API

```python
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# 1. Регистрация пользователя
response = requests.post(
    f"{BASE_URL}/users/register",
    json={"username": "python_user"}
)
user_data = response.json()
user_id = user_data["user_id"]

# 2. Добавление города
city_data = {
    "name": "Санкт-Петербург",
    "latitude": 59.9343,
    "longitude": 30.3351
}
requests.post(f"{BASE_URL}/cities?user_id={user_id}", json=city_data)

# 3. Получение погоды
weather_response = requests.get(
    f"{BASE_URL}/cities/Санкт-Петербург/weather",
    params={
        "time_str": "15:00",
        "fields": "temperature,windspeed",
        "user_id": user_id
    }
)

if weather_response.status_code == 200:
    print(json.dumps(weather_response.json(), indent=2, ensure_ascii=False))
```

## Структура базы данных

Сервер использует SQLite базу данных (`weather.db`) со следующими таблицами:

#Таблица `users`
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL
)
```


#Автоматическое обновление прогнозов:

1. При запуске сервера создается фоновое задание
2. Каждые 15 минут система:
   - Получает список всех городов из базы данных
   - Запрашивает актуальные прогнозы с Open-Meteo API
   - Сохраняет данные в таблицу `forecasts`
3. При добавлении нового города прогноз обновляется немедленно

#Особенности реализации:

1. Асинхронность - все операции ввода-вывода выполняются асинхронно
2. Валидация - все входные данные проходят строгую валидацию
3. Обработка ошибок - понятные сообщения об ошибках
4. Изоляция данных - каждый пользователь видит только свои города

## Запуск тестов

#Подготовка к тестированию

Убедитесь, что установлены все зависимости:

```bash
pip install -r requirements.txt
```

#Запуск тестов

Способ 1: Через pytest
```bash
python3 -m pytest tests.py -v
```

Способ 2: Прямой запуск
```bash
python3 tests.py
```


============================= test session starts ==============================
platform linux -- Python 3.8.10, pytest-7.4.3, pluggy-1.3.0
collected 10 items

tests.py::test_health_check PASSED
tests.py::test_current_weather PASSED
tests.py::test_user_registration PASSED
tests.py::test_add_city_without_user PASSED
tests.py::test_add_city_with_user PASSED
tests.py::test_get_cities PASSED
tests.py::test_duplicate_city PASSED
tests.py::test_get_weather_for_city PASSED
tests.py::test_get_weather_with_fields PASSED
tests.py::test_invalid_time_str_format PASSED

============================== 10 passed in 2.45s =============================
```

## Решение проблем

#Частые проблемы и решения

Проблема 1: ModuleNotFoundError при запуске
```
ModuleNotFoundError: No module named 'fastapi'
```
Решение: Установите зависимости:
```bash
pip install -r requirements.txt
```

Проблема 2: Порт 8000 уже занят
```
Address already in use
```
Решение: Измените порт в файле `script.py`:
```python
uvicorn.run(app, host="127.0.0.1", port=8001)  # измените 8000 на другой порт
```

Проблема 3: Ошибка 422 при запросе погоды
```
{"detail":[{"type":"missing","loc":["query","time_str"],"msg":"Field required"}]}
```
Решение: Убедитесь, что передаете обязательный параметр `time_str`:
```bash
# Правильно
curl "http://127.0.0.1:8000/cities/Москва/weather?time_str=14:00"

# Неправильно (нет параметра time_str)
curl "http://127.0.0.1:8000/cities/Москва/weather"
```

Проблема 4: Ошибка 404 при запросе прогноза
```
{"detail":"Weather forecast not found for specified time_str"}
```
Решение: Подождите 1-2 минуты после добавления города или попробуйте другое время.

#Просмотр логов

Логи сервера выводятся в консоль, где запущен `script.py`. Здесь можно увидеть:
- Входящие HTTP-запросы
- Ошибки при работе с API
- Информацию об обновлении прогнозов

# Просмотр содержимого базы
sqlite3 weather.db

# Внутри sqlite3:
.tables                    # Показать таблицы
SELECT  FROM users;       # Показать пользователей
SELECT  FROM cities;      # Показать города
SELECT COUNT() FROM forecasts;  # Количество прогнозов
.exit                     # Выйти
```

После этого перезапустите сервер - база данных создастся заново.

Для получения дополнительной помощи или сообщения о проблемах обратитесь к документации FastAPI или создайте issue в репозитории проекта.