import os
from dotenv import load_dotenv
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import random
from collections import defaultdict
import json

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен нашего бота
try:
    load_dotenv()
    TOKEN = os.getenv("API_TOKEN")
except KeyError:
    print("API_TOKEN environment variable not set.")
    exit(1)

# Состояния для ConversationHandler
INPUT_CLASSES, INPUT_SUBJECTS, INPUT_DIFFICULT_SUBJECTS = range(3)

# Дни недели
DAYS_OF_WEEK = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
MAX_LESSONS_PER_DAY = 7  # Максимальное количество уроков в день

# Категории сложности
DIFFICULTY_LEVELS = {
    "очень сложный": 3,
    "сложный": 2,
    "средний": 1,
    "легкий": 0
}

# Глобальное хранилище данных (временно, без БД)
schedule_data = {}

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Привет! Я бот "Оптимальное расписание". Мои авторы Оводова Глафира и Гаджиева Мадина.\n\n'
        'Используй команды:\n'
        '/help - список команд\n'
        '/new_schedule - создать новое расписание\n'
        '/set_difficult - задать список сложных предметов\n'
        '/view_schedule - посмотреть текущее расписание\n'
        '/view_timetable - посмотреть расписание по дням недели\n'
        '/clear_schedule - очистить расписание\n'
        '/show_difficult - показать текущие настройки сложности'
    )

# Обработчик команды /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
📋 Доступные команды:

/start — начать работу
/help — показать эту справку
/new_schedule — создать новое расписание
/set_difficult — задать список сложных предметов
/show_difficult — показать текущие настройки сложности
/view_schedule — посмотреть список предметов по классам
/view_timetable — посмотреть расписание по дням недели
/clear_schedule — очистить расписание

⚙️ Сложность предметов:
• Сложные предметы (математика, физика) ставятся в начало дня
• Средние предметы (история, биология) ставятся в середину
• Легкие предметы (труд, музыка) ставятся в конец дня
"""
    await update.message.reply_text(help_text)

# Команда для задания сложных предметов
async def set_difficult(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "📊 Настройка сложности предметов\n\n"
        "Введите предметы с указанием уровня сложности в формате:\n"
        "предмет: уровень_сложности\n\n"
        "Доступные уровни сложности:\n"
        "• очень сложный (например: математика, физика)\n"
        "• сложный (химия, информатика)\n"
        "• средний (история, биология, география)\n"
        "• легкий (труд, музыка, ИЗО, физкультура)\n\n"
        "Пример:\n"
        "математика: очень сложный\n"
        "физика: очень сложный\n"
        "труд: легкий\n"
        "музыка: легкий\n"
        "история: средний\n\n"
        "Каждый предмет с новой строки.\n"
        "Для отмены введите /cancel"
    )
    return INPUT_DIFFICULT_SUBJECTS

# Обработка ввода сложных предметов
async def input_difficult_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_text = update.message.text.strip()
    
    difficulty_settings = {}
    
    for line in user_text.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        if ':' in line:
            subject, difficulty = line.split(':', 1)
            subject = subject.strip().lower()
            difficulty = difficulty.strip().lower()
            
            if difficulty in DIFFICULTY_LEVELS:
                difficulty_settings[subject] = DIFFICULTY_LEVELS[difficulty]
            else:
                await update.message.reply_text(
                    f"❌ Неверный уровень сложности для предмета '{subject}'. "
                    f"Используйте: очень сложный, сложный, средний, легкий"
                )
                return INPUT_DIFFICULT_SUBJECTS
    
    if not difficulty_settings:
        await update.message.reply_text("❌ Не указаны предметы. Попробуйте снова.")
        return INPUT_DIFFICULT_SUBJECTS
    
    # Сохраняем настройки сложности
    context.user_data['difficulty_settings'] = difficulty_settings
    
    # Создаем обратный словарь для удобства
    difficulty_to_subjects = defaultdict(list)
    for subject, level in difficulty_settings.items():
        difficulty_to_subjects[level].append(subject)
    
    response = "✅ Настройки сложности сохранены!\n\n"
    response += "📊 Текущие настройки:\n"
    
    for level_name, level_value in sorted(DIFFICULTY_LEVELS.items(), key=lambda x: x[1], reverse=True):
        subjects_in_level = difficulty_to_subjects.get(level_value, [])
        if subjects_in_level:
            response += f"\n{level_name.title()} ({level_value}):\n"
            for subj in subjects_in_level:
                response += f"  • {subj}\n"
    
    response += "\nТеперь вы можете создать расписание с учетом этих настроек."
    
    await update.message.reply_text(response)
    return ConversationHandler.END

# Команда для просмотра текущих настроек сложности
async def show_difficult(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'difficulty_settings' not in context.user_data or not context.user_data['difficulty_settings']:
        await update.message.reply_text(
            "📭 Настройки сложности не заданы.\n"
            "Используйте /set_difficult для настройки."
        )
        return
    
    difficulty_settings = context.user_data['difficulty_settings']
    difficulty_to_subjects = defaultdict(list)
    
    for subject, level in difficulty_settings.items():
        difficulty_to_subjects[level].append(subject)
    
    response = "📊 Текущие настройки сложности предметов:\n\n"
    
    for level_name, level_value in sorted(DIFFICULTY_LEVELS.items(), key=lambda x: x[1], reverse=True):
        subjects_in_level = difficulty_to_subjects.get(level_value, [])
        if subjects_in_level:
            response += f"🎯 {level_name.title()} ({level_value} балл):\n"
            for subj in subjects_in_level:
                response += f"  • {subj}\n"
            response += "\n"
    
    response += "📝 Правила распределения:\n"
    response += "• Очень сложные предметы\n"
    response += "• Сложные предметы\n"
    response += "• Средние предметы\n"
    response += "• Легкие предметы\n"
    
    await update.message.reply_text(response)

# Начало создания расписания
async def new_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Проверяем, заданы ли настройки сложности
    if 'difficulty_settings' not in context.user_data:
        await update.message.reply_text(
            "⚠️ Сначала задайте настройки сложности предметов!\n"
            "Используйте /set_difficult\n\n"
            "Хотите продолжить без настроек сложности? (да/нет)"
        )
        context.user_data['waiting_for_difficulty_confirmation'] = True
        return INPUT_CLASSES
    
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

# Обработка ввода классов (обновленная для проверки сложности)
async def input_classes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_text = update.message.text.strip()
    
    # Проверка ответа на вопрос о сложности
    if context.user_data.get('waiting_for_difficulty_confirmation'):
        if user_text.lower() in ['нет', 'no', 'н', 'n']:
            await update.message.reply_text(
                "Сначала используйте /set_difficult для настройки сложности предметов."
            )
            del context.user_data['waiting_for_difficulty_confirmation']
            return ConversationHandler.END
        elif user_text.lower() in ['да', 'yes', 'д', 'y']:
            del context.user_data['waiting_for_difficulty_confirmation']
            # Продолжаем без настроек сложности
            pass
        else:
            await update.message.reply_text("Пожалуйста, ответьте 'да' или 'нет'.")
            return INPUT_CLASSES
    
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
        "История (2)\n"
        "Труд (1)\n"
        "Музыка (1)\n\n"
        "Для отмены введите /cancel"
    )
    
    return INPUT_SUBJECTS

# Обработка ввода предметов (обновленная для учета сложности)
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
                
                if subject_name:
                    # Определяем сложность предмета
                    difficulty = 0  # По умолчанию легкий
                    if 'difficulty_settings' in context.user_data:
                        difficulty_settings = context.user_data['difficulty_settings']
                        # Ищем предмет в настройках сложности (регистронезависимо)
                        for key in difficulty_settings:
                            if key.lower() in subject_name.lower():
                                difficulty = difficulty_settings[key]
                                break
                    
                    subjects_data.append({
                        'name': subject_name,
                        'hours_per_week': hours,
                        'difficulty': difficulty
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
    if total_hours > MAX_LESSONS_PER_DAY * 5:
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

# Улучшенная функция генерации расписания с учетом сложности
def generate_daily_timetable_with_difficulty(subjects, class_name):
    """
    Генерирует расписание с учетом сложности предметов
    """
    # Создаем список уроков с информацией о сложности
    lessons_list = []
    for subject in subjects:
        for i in range(subject['hours_per_week']):
            lessons_list.append({
                'name': subject['name'],
                'difficulty': subject['difficulty'],
                'original_order': i  # для разнесения одинаковых предметов
            })
    
    # Сортируем по сложности (сложные сначала)
    lessons_list.sort(key=lambda x: (-x['difficulty'], x['original_order']))
    
    # Создаем расписание по дням
    daily_timetable = {day: [] for day in DAYS_OF_WEEK}
    
    # Алгоритм распределения с учетом сложности:
    # 1. Сложные предметы ставим в начало дня (1-2 уроки)
    # 2. Средние предметы ставим в середину дня (2-4 уроки)
    # 3. Легкие предметы ставим в конец дня (4-7 уроки)
    
    # Создаем матрицу дней с учетом оптимальных позиций
    day_positions = {}
    for day in DAYS_OF_WEEK:
        # Определяем оптимальные позиции для разных уровней сложности
        day_positions[day] = {
            3: [1, 2],    # Очень сложные: 1-2 уроки
            2: [2, 3],    # Сложные: 2-3 уроки
            1: [3, 4],    # Средние: 3-4 уроки
            0: [4, 5, 6, 7]  # Легкие: 4-7 уроки
        }
    
    # Распределяем уроки по дням
    day_index = 0
    lesson_positions = {}
    
    for lesson in lessons_list:
        difficulty = lesson['difficulty']
        day = DAYS_OF_WEEK[day_index]
        
        # Получаем доступные позиции для этого уровня сложности в этот день
        available_positions = day_positions[day].get(difficulty, [])
        
        if available_positions:
            # Выбираем первую доступную позицию
            position = available_positions[0]
            # Удаляем эту позицию из доступных
            available_positions.remove(position)
            
            # Сохраняем урок в расписании
            daily_timetable[day].append({
                'name': lesson['name'],
                'position': position,
                'difficulty': difficulty
            })
            
            # Обновляем day_positions
            day_positions[day][difficulty] = available_positions
        else:
            # Если нет доступных позиций для этой сложности, ставим в любую свободную
            all_positions = list(range(1, MAX_LESSONS_PER_DAY + 1))
            occupied_positions = [l['position'] for l in daily_timetable[day]]
            free_positions = [p for p in all_positions if p not in occupied_positions]
            
            if free_positions:
                position = free_positions[0]
                daily_timetable[day].append({
                    'name': lesson['name'],
                    'position': position,
                    'difficulty': difficulty
                })
            else:
                # Если все позиции заняты, переходим к следующему дню
                day_index = (day_index + 1) % len(DAYS_OF_WEEK)
                day = DAYS_OF_WEEK[day_index]
                position = 1
                daily_timetable[day].append({
                    'name': lesson['name'],
                    'position': position,
                    'difficulty': difficulty
                })
        
        # Переходим к следующему дню для следующего урока
        day_index = (day_index + 1) % len(DAYS_OF_WEEK)
    
    # Сортируем уроки в каждом дне по позиции
    for day in DAYS_OF_WEEK:
        daily_timetable[day].sort(key=lambda x: x['position'])
    
    # Форматируем результат
    result = f"📅 Расписание для класса {class_name}:\n\n"
    
    for day in DAYS_OF_WEEK:
        lessons = daily_timetable[day]
        if lessons:
            result += f"<b>{day}:</b>\n"
            
            # Сортируем уроки по позиции
            lessons.sort(key=lambda x: x['position'])
            
            for lesson in lessons:
                # Добавляем эмодзи сложности
                difficulty_emoji = ""
                if lesson['difficulty'] >= 3:
                    difficulty_emoji = "🔴"  # Очень сложный
                elif lesson['difficulty'] == 2:
                    difficulty_emoji = "🟠"  # Сложный
                elif lesson['difficulty'] == 1:
                    difficulty_emoji = "🟡"  # Средний
                else:
                    difficulty_emoji = "🟢"  # Легкий
                
                result += f"  {lesson['position']}. {difficulty_emoji} {lesson['name']}\n"
            
            # Статистика сложности за день
            difficult_count = sum(1 for l in lessons if l['difficulty'] >= 2)
            easy_count = sum(1 for l in lessons if l['difficulty'] == 0)
            
            result += f"  📊 Сложных: {difficult_count}, Легких: {easy_count}\n"
        else:
            result += f"<b>{day}:</b> Нет уроков\n"
        result += "\n"
    
    # Общая статистика
    total_difficult = sum(1 for subj in subjects for _ in range(subj['hours_per_week']) if subj['difficulty'] >= 2)
    total_easy = sum(1 for subj in subjects for _ in range(subj['hours_per_week']) if subj['difficulty'] == 0)
    
    result += f"📈 Статистика сложности:\n"
    result += f"• Сложных уроков в неделю: {total_difficult}\n"
    result += f"• Легких уроков в неделю: {total_easy}\n"
    result += f"• Баланс сложности: {'⚖️ Хороший' if total_difficult <= total_easy else '⚠️ Много сложных'}\n"
    
    return result

# Обновленная функция просмотра расписания
async def view_timetable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'schedule' not in context.user_data or not context.user_data['schedule']:
        await update.message.reply_text("📭 У вас нет сохраненного расписания.\nИспользуйте /new_schedule для создания.")
        return
    
    schedule = context.user_data['schedule']
    classes = context.user_data.get('classes', list(schedule.keys()))
    
    # Проверяем, есть ли настройки сложности
    has_difficulty = 'difficulty_settings' in context.user_data
    
    if has_difficulty:
        info_text = "📊 Расписание с учетом сложности предметов:\n"
        info_text += "🔴 - очень сложный\n"
        info_text += "🟠 - сложный\n"
        info_text += "🟡 - средний\n"
        info_text += "🟢 - легкий\n"
        await update.message.reply_text(info_text)
    
    # Отправляем расписание для каждого класса
    for cls in classes:
        if cls in schedule:
            subjects = schedule[cls]
            
            if has_difficulty:
                timetable_text = generate_daily_timetable_with_difficulty(subjects, cls)
            else:
                # Без учета сложности используем старый алгоритм
                lessons_list = []
                for subject in subjects:
                    for _ in range(subject['hours_per_week']):
                        lessons_list.append(subject['name'])
                
                random.shuffle(lessons_list)
                daily_timetable = {day: [] for day in DAYS_OF_WEEK}
                day_index = 0
                for lesson in lessons_list:
                    current_day = DAYS_OF_WEEK[day_index]
                    daily_timetable[current_day].append(lesson)
                    day_index = (day_index + 1) % len(DAYS_OF_WEEK)
                
                timetable_text = f"📅 Расписание для класса {cls} (без учета сложности):\n\n"
                for day in DAYS_OF_WEEK:
                    lessons = daily_timetable[day]
                    if lessons:
                        timetable_text += f"<b>{day}:</b>\n"
                        for i, lesson in enumerate(lessons, 1):
                            timetable_text += f"  {i}. {lesson}\n"
                        timetable_text += f"  Всего уроков: {len(lessons)}\n"
                    else:
                        timetable_text += f"<b>{day}:</b> Нет уроков\n"
                    timetable_text += "\n"
            
            # Отправляем сообщение с разбивкой если нужно
            if len(timetable_text) > 4000:
                parts = [timetable_text[i:i+4000] for i in range(0, len(timetable_text), 4000)]
                for part in parts:
                    await update.message.reply_text(part, parse_mode='HTML')
            else:
                await update.message.reply_text(timetable_text, parse_mode='HTML')
    
    # Финальное сообщение
    total_classes = len(classes)
    if has_difficulty:
        await update.message.reply_text(
            f"✅ Расписание для {total_classes} классов с учетом сложности сгенерировано!\n"
            f"Для изменения настроек сложности используйте /set_difficult"
        )
    else:
        await update.message.reply_text(
            f"📊 Расписание для {total_classes} классов\n"
            f"⚠️ Для учета сложности предметов используйте /set_difficult"
        )

# Обновленная функция summary
async def generate_timetable_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    classes = context.user_data['classes']
    schedule = context.user_data['schedule']
    
    total_classes = len(classes)
    total_subjects = sum(len(schedule[cls]) for cls in classes)
    
    summary_text = f"✅ Расписание успешно создано!\n\n"
    
    # Проверяем использование сложности
    if 'difficulty_settings' in context.user_data:
        summary_text += "⚙️ Используются настройки сложности предметов\n\n"
    
    summary_text += f"📊 Статистика:\n"
    summary_text += f"• Классов: {total_classes}\n"
    summary_text += f"• Всего предметов: {total_subjects}\n\n"
    
    summary_text += "📋 Детали по классам:\n"
    for cls in classes:
        subjects = schedule[cls]
        total_hours = sum(subj['hours_per_week'] for subj in subjects)
        
        # Подсчитываем сложность
        difficult_hours = sum(subj['hours_per_week'] for subj in subjects if subj.get('difficulty', 0) >= 2)
        easy_hours = sum(subj['hours_per_week'] for subj in subjects if subj.get('difficulty', 0) == 0)
        
        summary_text += f"\n🎓 {cls}:\n"
        for subj in subjects:
            difficulty_info = ""
            if 'difficulty' in subj:
                diff = subj['difficulty']
                if diff >= 3:
                    difficulty_info = " 🔴"
                elif diff == 2:
                    difficulty_info = " 🟠"
                elif diff == 1:
                    difficulty_info = " 🟡"
                else:
                    difficulty_info = " 🟢"
            
            summary_text += f"  • {subj['name']}: {subj['hours_per_week']} ч/нед{difficulty_info}\n"
        
        summary_text += f"  📊 Всего часов: {total_hours}\n"
        if 'difficulty_settings' in context.user_data:
            summary_text += f"  🔴 Сложных часов: {difficult_hours}\n"
            summary_text += f"  🟢 Легких часов: {easy_hours}\n"
    
    summary_text += "\nИспользуйте:\n"
    summary_text += "/view_schedule - для просмотра предметов\n"
    summary_text += "/view_timetable - для просмотра расписания\n"
    
    if 'difficulty_settings' not in context.user_data:
        summary_text += "\n⚠️ Для учета сложности предметов используйте /set_difficult"
    
    await update.message.reply_text(summary_text)

# Остальные функции остаются без изменений (start, help_command, cancel, view_schedule, clear_schedule, handle_message, error)
# ... (копируем остальные функции без изменений)

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

# Очистка расписания
async def clear_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'schedule' in context.user_data:
        del context.user_data['schedule']
    if 'classes' in context.user_data:
        del context.user_data['classes']
    
    await update.message.reply_text("✅ Расписание очищено.")

def main() -> None:
    """Запуск бота."""
    application = Application.builder().token(TOKEN).build()

    # ConversationHandler для создания расписания
    conv_handler_new = ConversationHandler(
        entry_points=[CommandHandler('new_schedule', new_schedule)],
        states={
            INPUT_CLASSES: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_classes)],
            INPUT_SUBJECTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_subjects)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # ConversationHandler для настройки сложности
    conv_handler_difficult = ConversationHandler(
        entry_points=[CommandHandler('set_difficult', set_difficult)],
        states={
            INPUT_DIFFICULT_SUBJECTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_difficult_subjects)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Запуск бота
    print("🤖 Бот запущен...")
    application.run_polling()

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END

# Обработчик текстовых сообщений (не команд)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text
    await update.message.reply_text(f'Вы сказали: {user_text}')

# Обработчик ошибок
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f'Update {update} caused error {context.error}')

    # Регистрация обработчиков
    application.add_handler(conv_handler_new)
    application.add_handler(conv_handler_difficult)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("show_difficult", show_difficult))
    application.add_handler(CommandHandler("view_schedule", view_schedule))
    application.add_handler(CommandHandler("view_timetable", view_timetable))
    application.add_handler(CommandHandler("clear_schedule", clear_schedule))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error)

    # Запуск бота
    print("🤖 Бот запущен...")
    print("⚙️ Режим сложности предметов активирован!")
    application.run_polling()

if __name__ == '__main__':
    main()

