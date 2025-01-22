import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler

from utils import (
    get_weather,
    get_food_info,
    calculate_water_goal_advanced,
    calculate_calorie_goal_advanced,
    check_and_reset_day,
    generate_progress_plot
)

logger = logging.getLogger(__name__)
users = {}

STATE_ASK_WEIGHT, STATE_ASK_HEIGHT, STATE_ASK_AGE, STATE_ASK_GENDER, STATE_ASK_ACTIVITY, STATE_ASK_CITY = range(6)

def start_command(update: Update, context: CallbackContext):
    update.message.reply_text("Привет! Наберите /help, чтобы узнать, что я умею.")

def help_command(update: Update, context: CallbackContext):
    text = (
        "/menu — Меню с кнопками.\n"
        "/set_profile — Настройка профиля.\n"
        "/log_water <мл> — Записать воду.\n"
        "/log_food <продукт> — Записать продукт.\n"
        "/log_workout <тип> <мин> — Записать тренировку.\n"
        "/check_progress — Прогресс.\n"
        "/plot_progress — Графики.\n"
        "/recommend — Рекомендации.\n"
        "/profile — Текущий профиль.\n"
        "/cancel — Прервать настройку.\n"
    )
    update.message.reply_text(text)
    menu_command(update, context)

def set_profile_command(update: Update, context: CallbackContext):
    update.message.reply_text("Введите вес (кг):")
    return STATE_ASK_WEIGHT

def ask_weight(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    try:
        w = float(update.message.text.strip())
    except:
        update.message.reply_text("Нужно число. Повторите ввод веса (кг):")
        return STATE_ASK_WEIGHT
    users[user_id] = users.get(user_id, {})
    users[user_id]["weight"] = w
    update.message.reply_text("Введите рост (см):")
    return STATE_ASK_HEIGHT

def ask_height(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    try:
        h = float(update.message.text.strip())
    except:
        update.message.reply_text("Нужно число. Повторите ввод роста (см):")
        return STATE_ASK_HEIGHT
    users[user_id]["height"] = h
    update.message.reply_text("Введите возраст (лет):")
    return STATE_ASK_AGE

def ask_age(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    try:
        a = float(update.message.text.strip())
    except:
        update.message.reply_text("Нужно число. Повторите ввод возраста (лет):")
        return STATE_ASK_AGE
    users[user_id]["age"] = a
    update.message.reply_text("Укажите пол (male/female):")
    return STATE_ASK_GENDER

def ask_gender(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    g = update.message.text.strip().lower()
    if g not in ["male","female"]:
        update.message.reply_text("Введите 'male' или 'female'.")
        return STATE_ASK_GENDER
    users[user_id]["gender"] = g
    update.message.reply_text("Сколько минут активности в день?")
    return STATE_ASK_ACTIVITY

def ask_activity(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    try:
        act = float(update.message.text.strip())
    except:
        update.message.reply_text("Нужно число. Повторите ввод активности (мин):")
        return STATE_ASK_ACTIVITY
    users[user_id]["activity"] = act
    update.message.reply_text("В каком городе вы находитесь?")
    return STATE_ASK_CITY

def ask_city(update: Update, context: CallbackContext):
    from datetime import datetime
    user_id = update.effective_user.id
    c = update.message.text.strip()
    users[user_id]["city"] = c
    users[user_id]["current_date"] = datetime.now().strftime("%Y-%m-%d")
    users[user_id]["logged_water"] = 0
    users[user_id]["logged_calories"] = 0
    users[user_id]["burned_calories"] = 0
    t = get_weather(c)
    w_kg = users[user_id]["weight"]
    a_min = users[user_id]["activity"]
    h_cm = users[user_id]["height"]
    a = users[user_id]["age"]
    g = users[user_id]["gender"]
    wg = calculate_water_goal_advanced(w_kg, a_min, t)
    cg = calculate_calorie_goal_advanced(w_kg, h_cm, a, a_min, g)
    users[user_id]["water_goal"] = wg
    users[user_id]["calorie_goal"] = cg
    update.message.reply_text(
        f"Профиль сохранён!\n"
        f"Вес: {w_kg} кг, Рост: {h_cm} см, Возраст: {a}, Пол: {g}\n"
        f"Активность: {a_min} мин/день\n"
        f"Город: {c}, Температура: ~{t} °C\n"
        f"Вода: ~{int(wg)} мл, Калории: ~{int(cg)} ккал"
    )
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

def log_water_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in users:
        update.message.reply_text("Сначала /set_profile.")
        return
    check_and_reset_day(users[user_id])
    args = context.args
    if not args:
        update.message.reply_text("Использование: /log_water <мл>")
        return
    try:
        amt = float(args[0])
    except:
        update.message.reply_text("Нужно число (мл).")
        return
    users[user_id]["logged_water"] += amt
    wg = users[user_id]["water_goal"]
    cur = users[user_id]["logged_water"]
    left = max(wg - cur, 0)
    update.message.reply_text(f"Добавлено: {amt} мл. Всего: {cur:.1f}/{wg:.1f}. Осталось: {left:.1f} мл.")

def log_food_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in users:
        update.message.reply_text("Сначала /set_profile.")
        return
    check_and_reset_day(users[user_id])
    product_name = " ".join(context.args).strip()
    if not product_name:
        update.message.reply_text("Использование: /log_food <продукт>")
        return
    info = get_food_info(product_name)
    if not info:
        update.message.reply_text("Не найдена калорийность.")
        return
    context.user_data["food_info"] = info
    context.user_data["waiting_for_grams"] = True
    update.message.reply_text(
        f"Найдено: {info['name']}, {info['calories']} ккал/100г. Сколько грамм съели?"
    )

def handle_food_grams(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in users:
        return
    if context.user_data.get("waiting_for_grams"):
        check_and_reset_day(users[user_id])
        try:
            grams = float(update.message.text.strip())
        except:
            update.message.reply_text("Введите число (граммы).")
            return
        info = context.user_data.get("food_info")
        if not info:
            update.message.reply_text("Ошибка, /log_food снова.")
            context.user_data["waiting_for_grams"] = False
            return
        total_cals = (info["calories"] / 100.0) * grams
        users[user_id]["logged_calories"] += total_cals
        update.message.reply_text(
            f"Записано: {round(total_cals,1)} ккал.\n"
            f"Всего: {round(users[user_id]['logged_calories'],1)} ккал."
        )
        context.user_data["waiting_for_grams"] = False
        context.user_data["food_info"] = None

MET_VALUES = {
    "бег":9.8, "running":9.8, "ходьба":3.5, "walking":3.5,
    "плавание":7.0, "swimming":7.0, "велосипед":6.0, "cycling":6.0,
    "йога":3.0, "yoga":3.0
}

def log_workout_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in users:
        update.message.reply_text("Сначала /set_profile.")
        return
    check_and_reset_day(users[user_id])
    args = context.args
    if len(args) < 2:
        update.message.reply_text("Использование: /log_workout <тип> <мин>")
        return
    wtype = args[0].lower()
    try:
        minutes = float(args[1])
    except:
        update.message.reply_text("Минуты должны быть числом.")
        return
    met = MET_VALUES.get(wtype, 5.0)
    weight_kg = users[user_id]["weight"]
    cals_burned = met * weight_kg * (minutes / 60)
    users[user_id]["burned_calories"] += cals_burned
    add_water = (minutes // 30)*200
    msg = f"{wtype.capitalize()} {minutes} мин. Сожжено ~{int(cals_burned)} ккал."
    if add_water > 0:
        msg += f" Дополнительно выпейте ~{int(add_water)} мл воды."
    update.message.reply_text(msg)

def check_progress_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in users:
        update.message.reply_text("Сначала /set_profile.")
        return
    check_and_reset_day(users[user_id])
    ud = users[user_id]
    w_goal = ud["water_goal"]
    w_logged = ud["logged_water"]
    c_goal = ud["calorie_goal"]
    c_logged = ud["logged_calories"]
    c_burned = ud["burned_calories"]
    left = max(w_goal - w_logged, 0)
    bal = c_goal - c_logged + c_burned
    text = (
        f"Вода: {w_logged:.1f}/{w_goal:.1f} мл, осталось {left:.1f}\n"
        f"Калории: съедено {round(c_logged,1)}/{round(c_goal,1)}, "
        f"сожжено {round(c_burned,1)}, баланс {round(bal,1)}"
    )
    update.message.reply_text(text)

def plot_progress_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in users:
        update.message.reply_text("Сначала /set_profile.")
        return
    check_and_reset_day(users[user_id])
    ud = users[user_id]
    buf = generate_progress_plot(
        w_logged=ud["logged_water"],
        w_goal=ud["water_goal"],
        c_logged=ud["logged_calories"],
        c_goal=ud["calorie_goal"],
        c_burned=ud["burned_calories"]
    )
    update.message.reply_photo(photo=buf, caption="Графики воды и калорий.")

def recommend_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in users:
        update.message.reply_text("Сначала /set_profile.")
        return
    check_and_reset_day(users[user_id])
    ud = users[user_id]
    bal = ud["calorie_goal"] - ud["logged_calories"] + ud["burned_calories"]
    low = ["Огурцы","Яблоки","Салат","Творог 0%"]
    high = ["Орехи","Сыры","Авокадо","Шоколад"]
    work = ["Ходьба 30 мин","Бег 20 мин","Плавание 15 мин","Йога 40 мин"]
    if bal < 0:
        msg_food = f"Добавьте больше низкокалорийных продуктов: {low}"
        msg_work = f"Доп активность: {work[0]}"
    else:
        msg_food = f"Прибавьте что-то калорийное: {high}"
        msg_work = f"Для формы: {work[1]}"
    text = f"Баланс: {round(bal,1)} ккал\n{msg_food}\n{msg_work}"
    update.message.reply_text(text)

def profile_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in users:
        update.message.reply_text("Нет профиля. /set_profile.")
        return
    ud = users[user_id]
    text = (
        f"Вес: {ud.get('weight')} кг, Рост: {ud.get('height')} см, "
        f"Возраст: {ud.get('age')}, Пол: {ud.get('gender')}\n"
        f"Активность: {ud.get('activity')} мин/д\n"
        f"Город: {ud.get('city')}, Дата: {ud.get('current_date')}\n"
        f"Вода: {ud.get('water_goal')} мл, Калории: {ud.get('calorie_goal')} ккал"
    )
    update.message.reply_text(text)

def menu_command(update: Update, context: CallbackContext):
    kbd = [
        [
            InlineKeyboardButton("Профиль", callback_data="MENU_PROFILE"),
            InlineKeyboardButton("Прогресс", callback_data="MENU_PROGRESS"),
        ],
        [
            InlineKeyboardButton("Рекомендации", callback_data="MENU_RECOMMEND"),
        ]
    ]
    rm = InlineKeyboardMarkup(kbd)
    update.message.reply_text("Выберите действие:", reply_markup=rm)

def menu_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    query.answer()
    if user_id not in users:
        query.edit_message_text("Нет профиля. /set_profile")
        return
    check_and_reset_day(users[user_id])
    if data == "MENU_PROFILE":
        ud = users[user_id]
        text = (
            f"Вес: {ud.get('weight')} кг, Рост: {ud.get('height')} см, "
            f"Возраст: {ud.get('age')}, Пол: {ud.get('gender')}\n"
            f"Активность: {ud.get('activity')} мин\n"
            f"Город: {ud.get('city')}, Дата: {ud.get('current_date')}\n"
            f"Вода: {ud.get('water_goal')} мл, Калории: {ud.get('calorie_goal')} ккал"
        )
        query.edit_message_text(text)
    elif data == "MENU_PROGRESS":
        ud = users[user_id]
        w_goal = ud["water_goal"]
        w_logged = ud["logged_water"]
        c_goal = ud["calorie_goal"]
        c_logged = ud["logged_calories"]
        c_burned = ud["burned_calories"]
        left = max(w_goal - w_logged, 0)
        bal = c_goal - c_logged + c_burned
        msg = (
            f"Вода: {w_logged:.1f}/{w_goal:.1f} мл, осталось {left:.1f}\n"
            f"Калории: съедено {round(c_logged,1)}/{round(c_goal,1)}, "
            f"сожжено {round(c_burned,1)}, баланс {round(bal,1)}"
        )
        query.edit_message_text(msg)
    elif data == "MENU_RECOMMEND":
        ud = users[user_id]
        bal = ud["calorie_goal"] - ud["logged_calories"] + ud["burned_calories"]
        low = ["Огурцы","Яблоки","Салат","Творог 0%"]
        high = ["Орехи","Сыры","Авокадо","Шоколад"]
        wrk = ["Ходьба 30 мин","Бег 20 мин","Плавание 15 мин","Йога 40 мин"]
        if bal < 0:
            mf = f"Добавьте низкокалорийное: {low}"
            mw = f"Доп активность: {wrk[0]}"
        else:
            mf = f"Прибавьте калорийное: {high}"
            mw = f"Для формы: {wrk[1]}"
        query.edit_message_text(f"Баланс: {round(bal,1)}\n{mf}\n{mw}")
    else:
        query.edit_message_text("Неизвестная команда.")
