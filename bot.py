import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import random

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен вашего бота

try:
    # Access the value using the key (variable name)
    TOKEN = os.environ['API_TOKEN']
except KeyError:
    print("API_TOKEN environment variable not set.")

# Состояния для ConversationHandler
INPUT_CLASSES, INPUT_SUBJECTS = range(2)

# Дни недели
DAYS_OF_WEEK = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
MAX_LESSONS_PER_DAY = 7  # Максимальное количество уроков в день

# Глобальное хранилище данных (временно, без БД)
schedule_data = {}

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Привет! Я бот "Оптимальное расписание". Мои авторы Оводова Глафира и Гаджиева Мадина.\n\n'
        'Используй команды:\n'
        '/help - список команд\n'
        '/new_schedule - создать новое расписание\n'
        '/view_schedule - посмотреть текущее расписание\n'
        '/view_timetable - посмотреть расписание по дням недели\n'
        '/clear_schedule - очистить расписание'
    )

# Обработчик команды /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
📋 Доступные команды:

/start — начать работу
/help — показать эту справку
/new_schedule — создать новое расписание
/view_schedule — посмотреть список предметов по классам
/view_timetable — посмотреть расписание по дням недели
/clear_schedule — очистить расписание
/echo <текст> — повторить ваш текст
    """
    await update.message.reply_text(help_text)

# Начало создания расписания
async def new_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "📝 Создание нового расписания\n\n"
        "Введите список классов через запятую или с новой строки.\n"
        "Например:\n"
        "5А, 5Б, 6А, 6Б\n\n"
        "Или каждый класс с новой строки:\n"
        "5А\n"
        "5Б\n"
        "6А\n"
        "6Б\n\n"
        "Для отмены введите /cancel"
    )
    return INPUT_CLASSES

# Обработка ввода классов
async def input_classes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_text = update.message.text.strip()
    
    # Очищаем предыдущие данные
    context.user_data['schedule'] = {}
    context.user_data['classes'] = []
    
    # Разбираем ввод классов
    if ',' in user_text:
        classes = [cls.strip() for cls in user_text.split(',') if cls.strip()]
    else:
        classes = [cls.strip() for cls in user_text.split('\n') if cls.strip()]
    
    if not classes:
        await update.message.reply_text("❌ Не указаны классы. Попробуйте снова.")
        return INPUT_CLASSES
    
    # Сохраняем классы
    context.user_data['classes'] = classes
    context.user_data['current_class_index'] = 0
    
    # Начинаем ввод предметов для первого класса
    current_class = classes[0]
    await update.message.reply_text(
        f"🎓 Введите предметы для класса {current_class}\n\n"
        "Формат: предмет (количество часов в неделю)\n"
        "Каждый предмет с новой строки:\n\n"
        "Например:\n"
        "Математика (5)\n"
        "Русский язык (4)\n"
        "Литература (3)\n"
        "История (2)\n\n"
        "Для отмены введите /cancel"
    )
    
    return INPUT_SUBJECTS

# Обработка ввода предметов
async def input_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_text = update.message.text.strip()
    classes = context.user_data['classes']
    current_index = context.user_data['current_class_index']
    current_class = classes[current_index]
    
    # Разбираем предметы
    subjects_input = [line.strip() for line in user_text.split('\n') if line.strip()]
    subjects_data = []
    
    for subject_line in subjects_input:
        if '(' in subject_line and ')' in subject_line:
            try:
                subject_name = subject_line.split('(')[0].strip()
                hours_str = subject_line.split('(')[1].split(')')[0].strip()
                hours = int(hours_str)
                
                if subject_name and hours > 0:
                    subjects_data.append({
                        'name': subject_name,
                        'hours_per_week': hours
                    })
            except (ValueError, IndexError):
                await update.message.reply_text(
                    f"❌ Ошибка в формате: {subject_line}\n"
                    f"Используйте формат: 'Математика (5)'"
                )
                return INPUT_SUBJECTS
    
    if not subjects_data:
        await update.message.reply_text("❌ Не указаны предметы или неправильный формат. Попробуйте снова.")
        return INPUT_SUBJECTS
    
    # Проверяем, не слишком ли много часов
    total_hours = sum(subj['hours_per_week'] for subj in subjects_data)
    if total_hours > MAX_LESSONS_PER_DAY * 5:  # 5 дней недели
        await update.message.reply_text(
            f"⚠️ Внимание! Слишком много часов в неделю для класса {current_class}.\n"
            f"Всего: {total_hours} часов при максимуме {MAX_LESSONS_PER_DAY * 5}\n"
            f"Продолжить? (да/нет)"
        )
        context.user_data['pending_subjects'] = subjects_data
        context.user_data['pending_class'] = current_class
        return INPUT_SUBJECTS
    
    # Сохраняем предметы для текущего класса
    if 'schedule' not in context.user_data:
        context.user_data['schedule'] = {}
    
    context.user_data['schedule'][current_class] = subjects_data
    
    # Переходим к следующему классу или завершаем
    next_index = current_index + 1
    
    if next_index < len(classes):
        context.user_data['current_class_index'] = next_index
        next_class = classes[next_index]
        
        await update.message.reply_text(
            f"✅ Предметы для класса {current_class} сохранены!\n"
            f"Всего предметов: {len(subjects_data)}\n"
            f"Сумма часов: {total_hours}\n\n"
            f"🎓 Теперь введите предметы для класса {next_class}:"
        )
        return INPUT_SUBJECTS
    else:
        # Все классы обработаны
        await generate_timetable_summary(update, context)
        return ConversationHandler.END

async def generate_timetable_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    classes = context.user_data['classes']
    schedule = context.user_data['schedule']
    
    total_classes = len(classes)
    total_subjects = sum(len(schedule[cls]) for cls in classes)
    
    summary_text = f"✅ Расписание успешно создано!\n\n"
    summary_text += f"📊 Статистика:\n"
    summary_text += f"• Классов: {total_classes}\n"
    summary_text += f"• Всего предметов: {total_subjects}\n\n"
    
    summary_text += "📋 Детали по классам:\n"
    for cls in classes:
        subjects = schedule[cls]
        total_hours = sum(subj['hours_per_week'] for subj in subjects)
        summary_text += f"\n🎓 {cls}:\n"
        for subj in subjects:
            summary_text += f"  • {subj['name']}: {subj['hours_per_week']} ч/нед\n"
        summary_text += f"  Всего часов: {total_hours}\n"
    
    summary_text += "\nИспользуйте:\n"
    summary_text += "/view_schedule - для просмотра предметов\n"
    summary_text += "/view_timetable - для просмотра расписания по дням"
    
    await update.message.reply_text(summary_text)

# Отмена создания расписания
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Создание расписания отменено.")
    return ConversationHandler.END

# Просмотр текущего расписания (список предметов)
async def view_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'schedule' not in context.user_data or not context.user_data['schedule']:
        await update.message.reply_text("📭 У вас нет сохраненного расписания.\nИспользуйте /new_schedule для создания.")
        return
    
    schedule = context.user_data['schedule']
    classes = context.user_data.get('classes', list(schedule.keys()))
    
    response = "📋 Текущее расписание (предметы по классам):\n\n"
    
    for cls in classes:
        if cls in schedule:
            subjects = schedule[cls]
            total_hours = sum(subj['hours_per_week'] for subj in subjects)
            
            response += f"🎓 Класс {cls}:\n"
            for i, subj in enumerate(subjects, 1):
                response += f"  {i}. {subj['name']}: {subj['hours_per_week']} ч/нед\n"
            response += f"  📊 Всего часов в неделю: {total_hours}\n\n"
    
    response += f"Всего классов: {len(classes)}\n"
    response += "Используйте /view_timetable для просмотра расписания по дням"
    
    await update.message.reply_text(response)

# Функция для создания расписания по дням недели
def generate_daily_timetable(subjects, class_name):
    """
    Генерирует расписание по дням недели для одного класса
    """
    # Создаем список предметов с повторениями по количеству часов
    lessons_list = []
    for subject in subjects:
        for _ in range(subject['hours_per_week']):
            lessons_list.append(subject['name'])
    
    # Перемешиваем уроки
    random.shuffle(lessons_list)
    
    # Распределяем по дням недели
    daily_timetable = {day: [] for day in DAYS_OF_WEEK}
    
    # Простое распределение: равномерно по дням
    day_index = 0
    for lesson in lessons_list:
        current_day = DAYS_OF_WEEK[day_index]
        daily_timetable[current_day].append(lesson)
        day_index = (day_index + 1) % len(DAYS_OF_WEEK)
    
    # Форматируем результат
    result = f"📅 Расписание для класса {class_name}:\n\n"
    
    for day in DAYS_OF_WEEK:
        lessons = daily_timetable[day]
        if lessons:
            result += f"<b>{day}:</b>\n"
            for i, lesson in enumerate(lessons, 1):
                result += f"  {i}. {lesson}\n"
            result += f"  Всего уроков: {len(lessons)}\n"
        else:
            result += f"<b>{day}:</b> Нет уроков\n"
        result += "\n"
    
    return result

# Просмотр расписания по дням недели
async def view_timetable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'schedule' not in context.user_data or not context.user_data['schedule']:
        await update.message.reply_text("📭 У вас нет сохраненного расписания.\nИспользуйте /new_schedule для создания.")
        return
    
    schedule = context.user_data['schedule']
    classes = context.user_data.get('classes', list(schedule.keys()))
    
    # Отправляем расписание для каждого класса отдельным сообщением
    for cls in classes:
        if cls in schedule:
            subjects = schedule[cls]
            timetable_text = generate_daily_timetable(subjects, cls)
            
            # Проверяем, не слишком ли длинное сообщение
            if len(timetable_text) > 4000:
                parts = [timetable_text[i:i+4000] for i in range(0, len(timetable_text), 4000)]
                for part in parts:
                    await update.message.reply_text(part, parse_mode='HTML')
            else:
                await update.message.reply_text(timetable_text, parse_mode='HTML')
    
    # Добавляем общую информацию
    total_classes = len(classes)
    await update.message.reply_text(
        f"📊 Итого: расписание для {total_classes} классов\n"
        f"Используйте /view_schedule для просмотра списка предметов"
    )

# Очистка расписания
async def clear_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'schedule' in context.user_data:
        del context.user_data['schedule']
    if 'classes' in context.user_data:
        del context.user_data['classes']
    
    await update.message.reply_text("✅ Расписание очищено.")

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

    # ConversationHandler для создания расписания
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('new_schedule', new_schedule)],
        states={
            INPUT_CLASSES: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_classes)],
            INPUT_SUBJECTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_subjects)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Регистрация обработчиков
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("view_schedule", view_schedule))
    application.add_handler(CommandHandler("view_timetable", view_timetable))
    application.add_handler(CommandHandler("clear_schedule", clear_schedule))
    application.add_handler(CommandHandler("echo", echo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error)

    # Запуск бота
    print("🤖 Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()
