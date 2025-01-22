import logging
import sys
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackQueryHandler,
    CallbackContext
)

from config import TELEGRAM_BOT_TOKEN
from handlers import (
    users,
    start_command, help_command,
    set_profile_command, ask_weight, ask_height, ask_age, ask_gender, ask_activity, ask_city, cancel,
    log_water_command, log_food_command, handle_food_grams,
    log_workout_command, check_progress_command,
    plot_progress_command, recommend_command, profile_command,
    menu_command, menu_callback,
    STATE_ASK_WEIGHT, STATE_ASK_HEIGHT, STATE_ASK_AGE,
    STATE_ASK_GENDER, STATE_ASK_ACTIVITY, STATE_ASK_CITY
)

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# Новая функция для логирования всех входящих сообщений
def log_all_messages(update: Update, context: CallbackContext):
    user = update.effective_user
    if update.message:
        text = update.message.text
    else:
        text = "<no text>"
    logger.info(
        "User %s (username=%s) sent: %s",
        user.id,
        user.username,
        text
    )

def main():
    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("set_profile", set_profile_command)],
        states={
            STATE_ASK_WEIGHT: [MessageHandler(Filters.text, ask_weight)],
            STATE_ASK_HEIGHT: [MessageHandler(Filters.text, ask_height)],
            STATE_ASK_AGE: [MessageHandler(Filters.text, ask_age)],
            STATE_ASK_GENDER: [MessageHandler(Filters.text, ask_gender)],
            STATE_ASK_ACTIVITY: [MessageHandler(Filters.text, ask_activity)],
            STATE_ASK_CITY: [MessageHandler(Filters.text, ask_city)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler("profile", profile_command))
    dp.add_handler(CommandHandler("log_water", log_water_command))
    dp.add_handler(CommandHandler("log_food", log_food_command))
    dp.add_handler(CommandHandler("log_workout", log_workout_command))
    dp.add_handler(CommandHandler("check_progress", check_progress_command))
    dp.add_handler(CommandHandler("plot_progress", plot_progress_command))
    dp.add_handler(CommandHandler("recommend", recommend_command))
    dp.add_handler(CommandHandler("menu", menu_command))
    dp.add_handler(CallbackQueryHandler(menu_callback, pattern="^MENU_"))

    # Сначала логируем все сообщения (group=0)
    dp.add_handler(MessageHandler(Filters.all, log_all_messages), group=0)
    # Потом обрабатываем ввод граммов (group=1)
    dp.add_handler(MessageHandler(Filters.text, handle_food_grams), group=1)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
