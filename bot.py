import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен вашего бота (получите у @BotFather)
TOKEN = '8345579740:AAG2ksPseh6P1PeDjF__YsmmY0XE7628gfI'

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Привет! Я бот Оптимальное расписание. Мои авторы Оводова Глафира и Гаджиева Мадина. Используй /help для списка команд.'
    )

# Обработчик команды /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
Доступные команды:
/start — начать работу
/help — показать эту справку
/echo <текст> — повторить ваш текст
/schedule - добавление параметров расписания 
    """
    await update.message.reply_text(help_text)

# Обработчик команды /help
async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_text = """
В процессе разработки
    """
    await update.message.reply_text(reply_text)

# Обработчик команды /echo
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args:
        text_to_echo = ' '.join(context.args)
        await update.message.reply_text(f'Эхо: {text_to_echo}')
    else:
        await update.message.reply_text('Используйте: /echo <ваш текст>')

# Обработчик текстовых сообщений (не команд)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text
    await update.message.reply_text(f'Вы сказали: {user_text}')

# Обработчик ошибок
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f'Update {update} caused error {context.error}')

def main() -> None:
    """Запуск бота."""
    application = Application.builder().token(TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("schedule", schedule_command))
    application.add_handler(CommandHandler("echo", echo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error)

    # Запуск бота
    print("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()

