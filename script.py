# script.py - основной файл сервера
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import uvicorn
import sqlite3
import json
from datetime import datetime, time
from typing import Optional, List
from pydantic import BaseModel
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Создадим базу данных SQLite в памяти
DB_PATH = "weather.db"

# Модели данных
class Coordinates(BaseModel):
    latitude: float
    longitude: float

class CityRequest(BaseModel):
    name: str
    latitude: float
    longitude: float

class WeatherRequest(BaseModel):
    time: str  # Формат: "HH:MM"
    fields: Optional[List[str]] = None

class UserRegistration(BaseModel):
    username: str

# Инициализация базы данных
def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL
        )
    ''')
    
    # Таблица городов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, name)
        )
    ''')
    
    # Таблица прогнозов погоды
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            temperature REAL,
            humidity REAL,
            windspeed REAL,
            precipitation REAL,
            pressure REAL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (city_id) REFERENCES cities(id),
            UNIQUE(city_id, timestamp)
        )
    ''')
    
    conn.commit()
    conn.close()

init_database()

# Глобальные переменные
app = FastAPI(title="Weather Service API")
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запуск планировщика при старте
    scheduler.start()
    
    # Запускаем задачу обновления погоды каждые 15 минут
    scheduler.add_job(
        update_all_weather_forecasts,
        trigger=IntervalTrigger(minutes=15),
        id="update_weather",
        replace_existing=True
    )
    
    yield
    
    # Остановка планировщика при завершении
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

# Функции для работы с базой данных
def get_db_connection():
    return sqlite3.connect(DB_PATH)

async def make_openmeteo_request(latitude: float, longitude: float):
    """Запрос к Open-Meteo API"""
    base_url = "https://api.open-meteo.com/v1/forecast"
    
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current_weather": "true",
        "hourly": "temperature_2m,relativehumidity_2m,windspeed_10m,precipitation,pressure_msl",
        "timezone": "auto"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(base_url, params=params, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Open-Meteo API error: {str(e)}")

async def update_weather_forecast(city_id: int, latitude: float, longitude: float):
    """Обновление прогноза погоды для конкретного города"""
    try:
        data = await make_openmeteo_request(latitude, longitude)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем текущее время
        now = datetime.now().isoformat()
        
        # Обрабатываем текущую погоду
        current = data.get("current_weather", {})
        current_time = current.get("time", datetime.now().isoformat())
        
        cursor.execute('''
            INSERT OR REPLACE INTO forecasts 
            (city_id, timestamp, temperature, windspeed, pressure, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            city_id,
            current_time,
            current.get("temperature"),
            current.get("windspeed"),
            current.get("pressure", 1013.25),  # Значение по умолчанию
            now
        ))
        
        # Обрабатываем почасовой прогноз
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        temperatures = hourly.get("temperature_2m", [])
        humidities = hourly.get("relativehumidity_2m", [])
        windspeeds = hourly.get("windspeed_10m", [])
        precipitations = hourly.get("precipitation", [])
        pressures = hourly.get("pressure_msl", [])
        
        for i in range(min(len(times), 24)):  # Только на сегодня
            cursor.execute('''
                INSERT OR REPLACE INTO forecasts 
                (city_id, timestamp, temperature, humidity, windspeed, precipitation, pressure, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                city_id,
                times[i],
                temperatures[i] if i < len(temperatures) else None,
                humidities[i] if i < len(humidities) else None,
                windspeeds[i] if i < len(windspeeds) else None,
                precipitations[i] if i < len(precipitations) else None,
                pressures[i] if i < len(pressures) else None,
                now
            ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error updating forecast for city {city_id}: {str(e)}")

async def update_all_weather_forecasts():
    """Обновление прогнозов для всех городов"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, latitude, longitude FROM cities")
    cities = cursor.fetchall()
    
    conn.close()
    
    for city in cities:
        city_id, lat, lon = city
        await update_weather_forecast(city_id, lat, lon)

# Основные маршруты API
@app.get("/weather/current")
async def get_current_weather(latitude: float, longitude: float):
    """
    Метод 1: Получение текущей погоды по координатам
    Возвращает температуру, скорость ветра и атмосферное давление
    """
    try:
        data = await make_openmeteo_request(latitude, longitude)
        current = data.get("current_weather", {})
        
        return {
            "temperature": current.get("temperature"),
            "windspeed": current.get("windspeed"),
            "pressure": current.get("pressure", 1013.25),
            "time": current.get("time")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users/register")
async def register_user(user_data: UserRegistration):
    """
    Дополнительный метод: Регистрация пользователя
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO users (username) VALUES (?)",
            (user_data.username,)
        )
        user_id = cursor.lastrowid
        conn.commit()
        
        return {"user_id": user_id, "username": user_data.username}
    
    except sqlite3.IntegrityError:
        # Пользователь уже существует
        cursor.execute(
            "SELECT id FROM users WHERE username = ?",
            (user_data.username,)
        )
        result = cursor.fetchone()
        if result:
            return {"user_id": result[0], "username": user_data.username}
        else:
            raise HTTPException(status_code=400, detail="User registration failed")
    
    finally:
        conn.close()

@app.post("/cities")
async def add_city(city_data: CityRequest, user_id: Optional[int] = None):
    """
    Метод 2: Добавление города для отслеживания погоды
    Если user_id не указан, город добавляется в общий список
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Проверяем существование пользователя, если указан user_id
        if user_id:
            cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="User not found")
        
        # Проверяем, не добавлен ли уже город
        cursor.execute('''
            SELECT id FROM cities 
            WHERE (user_id = ? OR (? IS NULL AND user_id IS NULL)) 
            AND name = ?
        ''', (user_id, user_id, city_data.name))
        
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="City already exists for this user")
        
        # Добавляем город
        cursor.execute('''
            INSERT INTO cities (user_id, name, latitude, longitude)
            VALUES (?, ?, ?, ?)
        ''', (user_id, city_data.name, city_data.latitude, city_data.longitude))
        
        city_id = cursor.lastrowid
        conn.commit()
        
        # Немедленно обновляем прогноз для нового города
        await update_weather_forecast(city_id, city_data.latitude, city_data.longitude)
        
        return {
            "message": "City added successfully",
            "city_id": city_id,
            "user_id": user_id
        }
    
    finally:
        conn.close()

@app.get("/cities")
async def get_cities(user_id: Optional[int] = None):
    """
    Метод 3: Получение списка городов
    Если user_id указан, возвращает города пользователя
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if user_id:
        cursor.execute(
            "SELECT id, name, latitude, longitude FROM cities WHERE user_id = ?",
            (user_id,)
        )
    else:
        cursor.execute(
            "SELECT id, name, latitude, longitude FROM cities WHERE user_id IS NULL"
        )
    
    cities = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": city[0],
            "name": city[1],
            "latitude": city[2],
            "longitude": city[3]
        }
        for city in cities
    ]

@app.get("/cities/{city_name}/weather")
async def get_city_weather(
    city_name: str,
    time_str: str,
    fields: Optional[str] = None,
    user_id: Optional[int] = None
):
    """
    Метод 4: Получение погоды для города в указанное время
    Параметр fields: список параметров через запятую (temperature,humidity,windspeed,precipitation)
    """
    # Парсим время
    try:
        target_time = datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM")
    
    # Определяем сегодняшнюю дату
    today = datetime.now().date()
    target_datetime = datetime.combine(today, target_time).isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Находим город
    if user_id:
        cursor.execute('''
            SELECT id FROM cities 
            WHERE name = ? AND user_id = ?
        ''', (city_name, user_id))
    else:
        cursor.execute('''
            SELECT id FROM cities 
            WHERE name = ? AND user_id IS NULL
        ''', (city_name,))
    
    city_result = cursor.fetchone()
    
    if not city_result:
        raise HTTPException(status_code=404, detail="City not found")
    
    city_id = city_result[0]
    
    # Получаем прогноз погоды
    cursor.execute('''
        SELECT temperature, humidity, windspeed, precipitation, pressure
        FROM forecasts 
        WHERE city_id = ? AND timestamp LIKE ?
        ORDER BY timestamp DESC
        LIMIT 1
    ''', (city_id, f"%{target_datetime.split('T')[0]}T{time_str}%"))
    
    forecast = cursor.fetchone()
    conn.close()
    
    if not forecast:
        raise HTTPException(status_code=404, detail="Weather forecast not found for specified time")
    
    # Определяем, какие поля возвращать
    available_fields = {
        "temperature": forecast[0],
        "humidity": forecast[1],
        "windspeed": forecast[2],
        "precipitation": forecast[3],
        "pressure": forecast[4]
    }
    
    if fields:
        requested_fields = [f.strip() for f in fields.split(",")]
        result = {}
        for field in requested_fields:
            if field in available_fields:
                result[field] = available_fields[field]
        return result
    else:
        # По умолчанию возвращаем все поля
        return {
            "temperature": forecast[0],
            "humidity": forecast[1],
            "windspeed": forecast[2],
            "precipitation": forecast[3],
            "pressure": forecast[4],
            "time": time_str
        }

@app.get("/health")
async def health_check():
    """Проверка работоспособности сервера"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    # Запускаем сервер
    uvicorn.run(
        "script:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )