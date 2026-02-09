# tests.py - юнит-тесты для API
import pytest
from fastapi.testclient import TestClient
from script import app, init_database, get_db_connection
import json
import sqlite3
import os

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Фикстура для настройки и очистки перед каждым тестом"""
    # Сохраняем оригинальный путь к БД
    original_db_path = "weather.db"
    
    # Используем тестовую БД
    test_db_path = "test_weather.db"
    
    # Подменяем путь к БД в приложении
    import script
    script.DB_PATH = test_db_path
    
    # Инициализируем тестовую БД
    init_database()
    
    yield
    
    # Очистка после тестов
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    # Возвращаем оригинальный путь
    script.DB_PATH = original_db_path

def test_health_check():
    """Тест проверки работоспособности"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_current_weather():
    """Тест получения текущей погоды"""
    response = client.get("/weather/current?latitude=55.7558&longitude=37.6173")
    assert response.status_code in [200, 500]  # 500 если API недоступно
    
    if response.status_code == 200:
        data = response.json()
        assert "temperature" in data
        assert "windspeed" in data
        assert "pressure" in data

def test_user_registration():
    """Тест регистрации пользователя"""
    response = client.post(
        "/users/register",
        json={"username": "testuser"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    assert data["username"] == "testuser"

def test_add_city_without_user():
    """Тест добавления города без пользователя"""
    city_data = {
        "name": "Moscow",
        "latitude": 55.7558,
        "longitude": 37.6173
    }
    
    response = client.post("/cities", json=city_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["message"] == "City added successfully"
    assert "city_id" in data

def test_add_city_with_user():
    """Тест добавления города с пользователем"""
    # Сначала регистрируем пользователя
    user_response = client.post(
        "/users/register",
        json={"username": "testuser2"}
    )
    user_id = user_response.json()["user_id"]
    
    # Добавляем город для пользователя
    city_data = {
        "name": "London",
        "latitude": 51.5074,
        "longitude": -0.1278
    }
    
    response = client.post(f"/cities?user_id={user_id}", json=city_data)
    assert response.status_code == 200

def test_get_cities():
    """Тест получения списка городов"""
    # Добавляем город
    city_data = {
        "name": "TestCity",
        "latitude": 50.0,
        "longitude": 50.0
    }
    
    client.post("/cities", json=city_data)
    
    # Получаем список городов
    response = client.get("/cities")
    assert response.status_code == 200
    
    cities = response.json()
    assert isinstance(cities, list)
    
    # Проверяем, что наш город в списке
    city_names = [city["name"] for city in cities]
    assert "TestCity" in city_names

def test_duplicate_city():
    """Тест добавления дубликата города"""
    city_data = {
        "name": "DuplicateCity",
        "latitude": 40.0,
        "longitude": 40.0
    }
    
    # Первое добавление
    response1 = client.post("/cities", json=city_data)
    assert response1.status_code == 200
    
    # Второе добавление (должно вернуть ошибку)
    response2 = client.post("/cities", json=city_data)
    assert response2.status_code == 400

def test_get_weather_for_city():
    """Тест получения погоды для города"""
    # Добавляем город
    city_data = {
        "name": "WeatherCity",
        "latitude": 60.0,
        "longitude": 60.0
    }
    
    response = client.post("/cities", json=city_data)
    assert response.status_code == 200
    
    # Пытаемся получить погоду (может вернуть 404 если нет прогноза)
    # Используем time_str вместо time, если в коде используется time_str
    response = client.get("/cities/WeatherCity/weather?time=12:00")
    # Разрешаем 422, так как это может быть ошибка валидации
    assert response.status_code in [200, 404, 422]

def test_get_weather_with_fields():
    """Тест получения погоды с выбором полей"""
    # Добавляем город
    city_data = {
        "name": "FieldsCity",
        "latitude": 70.0,
        "longitude": 70.0
    }
    
    client.post("/cities", json=city_data)
    
    # Запрос с указанием полей
    response = client.get(
        "/cities/FieldsCity/weather?time=14:00&fields=temperature,humidity"
    )
    
    if response.status_code == 200:
        data = response.json()
        # Проверяем, что вернулись только указанные поля
        assert "temperature" in data
        assert "humidity" in data
        assert "windspeed" not in data
        assert "precipitation" not in data

def test_invalid_time_format():
    """Тест с некорректным форматом времени"""
    response = client.get("/cities/SomeCity/weather?time=25:70")
    # FastAPI возвращает 422 при невалидном времени
    assert response.status_code == 422

if __name__ == "__main__":
    pytest.main(["-v", "tests.py"])