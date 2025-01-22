import logging
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io
from datetime import datetime
import requests

from config import OPENWEATHER_API_KEY

logger = logging.getLogger(__name__)

def get_weather(city: str) -> float:
    try:
        url = (
            "http://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
        )
        response = requests.get(url)
        data = response.json()
        if data.get("cod") != 200:
            return 0.0
        return float(data["main"]["temp"])
    except:
        return 0.0

def get_food_info(product_name: str) -> dict:
    try:
        url = (
            "https://world.openfoodfacts.org/cgi/search.pl"
            f"?action=process&search_terms={product_name}&json=true"
        )
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            products = data.get('products', [])
            for p in products[:5]:
                cals = p.get('nutriments', {}).get('energy-kcal_100g', 0)
                if cals and cals > 0:
                    name_found = p.get('product_name', 'Неизвестно')
                    return {'name': name_found, 'calories': cals}
        return None
    except:
        return None

def calculate_water_goal_advanced(weight_kg: float, activity_min: float, temperature: float) -> float:
    base = weight_kg * 30.0
    extra_activity = (activity_min // 30) * 500
    extra_temp = 0
    if 25 < temperature < 30:
        extra_temp = 500
    elif temperature >= 30:
        extra_temp = 1000
    total = base + extra_activity + extra_temp
    if total > 2500:
        total = 2500
    return total

def calculate_calorie_goal_advanced(weight_kg: float, height_cm: float, age: float,
                                    activity_min: float, gender: str="male") -> float:
    if gender.lower() == 'male':
        base_bmr = 10*weight_kg + 6.25*height_cm - 5*age + 5
    else:
        base_bmr = 10*weight_kg + 6.25*height_cm - 5*age - 161
    add = 0
    if 30 <= activity_min < 90:
        add = 200
    elif activity_min >= 90:
        add = 400
    return base_bmr + add

def check_and_reset_day(user_data: dict):
    today_str = datetime.now().strftime("%Y-%m-%d")
    if user_data.get("current_date") != today_str:
        user_data["current_date"] = today_str
        user_data["logged_water"] = 0
        user_data["logged_calories"] = 0
        user_data["burned_calories"] = 0

def generate_progress_plot(w_logged, w_goal, c_logged, c_goal, c_burned) -> io.BytesIO:
    fig, axes = plt.subplots(1, 2, figsize=(8, 4))
    axes[0].bar(["Выпито"], [w_logged], color="blue", label="Выпито")
    if w_goal > w_logged:
        axes[0].bar(["Выпито"], [w_goal - w_logged], bottom=[w_logged], color="lightblue", label="Осталось")
    axes[0].set_ylim([0, max(w_goal, w_logged)*1.1])
    axes[0].set_title("Вода (мл)")
    axes[0].legend()
    axes[1].bar(["Калории"], [c_logged], color="red", label="Съедено")
    axes[1].bar(["Калории"], [c_burned], bottom=[c_logged], color="green", label="Сожжено")
    axes[1].axhline(y=c_goal, color="black", linestyle="--", label="Цель")
    m = max(c_goal, c_logged + c_burned)
    axes[1].set_ylim([0, m*1.1])
    axes[1].set_title("Калории (ккал)")
    axes[1].legend()
    fig.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)
    return buf
