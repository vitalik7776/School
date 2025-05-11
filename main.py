import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

# Загрузка переменных окружения из .env файла
load_dotenv()

# Конфигурация логгера
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Конфигурация бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN provided in environment variables")

# Информация об администраторе
ADMIN_ID = int(os.getenv("ADMIN_ID", "456319202"))  # ID администратора

# Ссылка на канал для подходящих пользователей
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/+ph_7tRCN12EwNDM0")

# Пороговые значения результатов теста
HIGH_READINESS_THRESHOLD = 7  # Количество ответов 'c' для высокой готовности
MEDIUM_READINESS_THRESHOLD = 5  # Количество ответов 'b' для средней готовности

# Список вопросов и вариантов ответов для теста
questions = [
    {
        "q": "1. Что ты чаще всего чувствуешь в последнее время?",
        "a": ["Стабильность и спокойствие", "Лёгкую тревогу, неудовлетворённость", "Боль, растерянность, пустоту"]
    },
    {
        "q": "2. Как ты обычно справляешься с переживаниями?",
        "a": ["Просто отдыхаю", "Алкоголь, наркотики, другие зависимости", "Мне важно говорить и чувствовать поддержку"]
    },
    {
        "q": "3. Насколько тебе важно быть частью развивающего сообщества?",
        "a": ["Не особо важно", "Интересно, если там есть что-то полезное", "Очень важно — мне этого не хватает"]
    },
    {
        "q": "4. Как ты относишься к теме саморазвития и работы над собой?",
        "a": ["Скептически", "Иногда интересно", "Это важно и необходимо"]
    },
    {
        "q": "5. Готова ли ты выполнять короткие задания, связанные с самоанализом и размышлениями?",
        "a": ["Нет", "Если будет время", "Да, я это люблю, мне это необходимо"]
    },
    {
        "q": "6. Насколько для тебя актуальны такие темы, как уверенность, принятие себя, сексуальность, чувство вины и травмы прошлого?",
        "a": ["Почти не касаются", "Иногда возникают", "Очень откликаются"]
    },
    {
        "q": "7. Готова ли ты инвестировать небольшую сумму (например, $10 в месяц) в участие в сообществе, которое даёт тебе поддержку и рост?",
        "a": ["Нет, я не плачу за такие вещи", "Возможно, если увижу ценность", "Да, я считаю это хорошей инвестицией"]
    },
    {
        "q": "8. Какой формат тебе ближе?",
        "a": ["Самостоятельная работа над собой", "Что-то, что будет меня направлять", "Мне нужен хороший наставник"]
    },
    {
        "q": "9. Что тебе сейчас нужнее всего?",
        "a": ["Ничего, у меня всё в порядке", "Поддержка и понимание", "Инструменты для работы над собой"]
    },
    {
        "q": "10. Хочешь ли ты также помогать и другим?",
        "a": ["Нет, пока не до этого", "Да, но не знаю как", "Я уже помогаю"]
    }
]

# Сообщения ответов на основе результатов теста
responses = {
    "high": "Ты готова начать путь своей личной трансформации. Подай заявку на вступление в нашу Школу.",
    "medium": "У тебя есть потенциал, и ты можешь раскрыться с поддержкой. Мы будем рядом. Подай заявку на вступление:",
    "low": "Сейчас ты, возможно, ещё не готов(а) к процессу личной трансформации. Возвращайся, когда почувствуешь внутренний зов."
}

# Словарь для хранения данных пользователя во время теста
# Структура: {user_id: {step: int, score: {a: int, b: int, c: int}, username: str, answers: []}}
user_data = {}

# Создаем роутер
router = Router()

async def send_question(bot, user_id):
    """
    Отправить вопрос пользователю на основе его текущего шага теста.
    
    Args:
        bot: Экземпляр Telegram бота
        user_id: ID пользователя в Telegram
    """
    try:
        data = user_data.get(user_id)
        if not data:
            logger.error(f"User data not found for user {user_id}")
            return await bot.send_message(user_id, "Произошла ошибка. Пожалуйста, напишите /start чтобы начать заново.")
        
        step = data["step"]
        if step >= len(questions):
            logger.error(f"Invalid step {step} for user {user_id}")
            return await bot.send_message(user_id, "Произошла ошибка. Пожалуйста, напишите /start чтобы начать заново.")
            
        q = questions[step]
        
        # Создаем inline-клавиатуру с вариантами ответов
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for i, option in enumerate(["a", "b", "c"]):
            button = InlineKeyboardButton(
                text=f"{chr(97+i)}) {q['a'][i]}",
                callback_data=option
            )
            keyboard.inline_keyboard.append([button])
        
        await bot.send_message(user_id, q["q"], reply_markup=keyboard)
        logger.info(f"Sent question {step+1} to user {user_id}")
    except Exception as e:
        logger.error(f"Error sending question to user {user_id}: {e}")
        await bot.send_message(user_id, "Произошла ошибка при отправке вопроса. Пожалуйста, напишите /start чтобы начать заново.")

async def process_test_results(bot, user_id):
    """
    Обработать результаты теста, отправить обратную связь пользователю и уведомить администратора.
    
    Args:
        bot: Экземпляр Telegram бота
        user_id: ID пользователя в Telegram
    """
    try:
        data = user_data[user_id]
        # Извлекаем оценки
        a = data["score"]["a"]
        b = data["score"]["b"]
        c = data["score"]["c"]
        
        # Получаем информацию о пользователе из сохраненных данных
        username = data.get("username")
        profile_link = f"https://t.me/{username}" if username else f"tg://user?id={user_id}"
        
        # Получаем ответы пользователя
        user_answers = data.get("answers", [])
        
        # Пытаемся получить больше информации о пользователе, если доступно
        try:
            user_info = await bot.get_chat(user_id)
            first_name = user_info.first_name or ""
            last_name = user_info.last_name or ""
            full_name = f"{first_name} {last_name}".strip()
            
            # Готовим сообщение с результатами для администратора с подробной информацией
            summary = "Новый участник прошёл тест:\n\n"
            summary += f"Имя: {full_name}\n"
            summary += f"Username: @{username}\n" if username else ""
            summary += f"Ссылка на профиль: {profile_link}\n\n"
            
            # Добавляем сводку оценок
            summary += f"Ответов a: {a}\n"
            summary += f"Ответов b: {b}\n"
            summary += f"Ответов c: {c}\n\n"
            
            # Добавляем подробные ответы
            if user_answers:
                summary += "Детальные ответы:\n\n"
                for i, answer_data in enumerate(user_answers, 1):
                    question = answer_data.get("question", f"Вопрос {i}")
                    answer_option = answer_data.get("answer_option", "?")
                    answer_text = answer_data.get("answer_text", "Нет ответа")
                    summary += f"{i}. {question}\n"
                    summary += f"   Ответ: {answer_option.upper()}) {answer_text}\n\n"
            
            result_text = summary
            
        except Exception as e:
            # Запасной вариант с базовой информацией, если подробная информация недоступна
            logger.error(f"Error getting detailed user info: {e}")
            result_text = f"Результаты теста от {profile_link}\n\n"
            result_text += f"Ответов a: {a}\n"
            result_text += f"Ответов b: {b}\n"
            result_text += f"Ответов c: {c}\n\n"
            
            # Добавляем базовую информацию об ответах даже в случае ошибки
            if user_answers:
                result_text += "Ответы:\n\n"
                for i, answer_data in enumerate(user_answers, 1):
                    answer_option = answer_data.get("answer_option", "?")
                    answer_text = answer_data.get("answer_text", "Нет ответа")
                    result_text += f"{i}. Ответ: {answer_option.upper()}) {answer_text}\n"
        
        # Сообщение может быть слишком длинным для одного сообщения
        # Разделим его, если необходимо (у Telegram лимит 4096 символов на сообщение)
        MAX_MESSAGE_LENGTH = 4000  # Чуть меньше 4096 для надежности
        
        if len(result_text) > MAX_MESSAGE_LENGTH:
            # Сначала отправляем информацию о пользователе и оценки
            intro_text = result_text.split("Детальные ответы")[0]
            await bot.send_message(ADMIN_ID, intro_text)
            
            # Отправляем детальные ответы отдельно
            answers_text = "Детальные ответы:\n\n"
            for i, answer_data in enumerate(user_answers, 1):
                question = answer_data.get("question", f"Вопрос {i}")
                answer_option = answer_data.get("answer_option", "?")
                answer_text = answer_data.get("answer_text", "Нет ответа")
                answer_block = f"{i}. {question}\n   Ответ: {answer_option.upper()}) {answer_text}\n\n"
                
                # Проверяем, не превысит ли добавление этого блока лимит сообщения
                if len(answers_text) + len(answer_block) > MAX_MESSAGE_LENGTH:
                    await bot.send_message(ADMIN_ID, answers_text)
                    answers_text = answer_block
                else:
                    answers_text += answer_block
            
            # Отправляем оставшиеся ответы, если есть
            if answers_text:
                await bot.send_message(ADMIN_ID, answers_text)
        else:
            # Отправляем всё в одном сообщении, если оно не слишком длинное
            await bot.send_message(ADMIN_ID, result_text)
        
        logger.info(f"Sent test results for user {user_id} to admin")
        
        # Определяем соответствующий ответ на основе оценок
        if c >= HIGH_READINESS_THRESHOLD:
            await bot.send_message(user_id, f"{responses['high']}\n{CHANNEL_LINK}")
            logger.info(f"User {user_id} received high readiness response")
        elif b >= MEDIUM_READINESS_THRESHOLD:
            await bot.send_message(user_id, f"{responses['medium']}\n{CHANNEL_LINK}")
            logger.info(f"User {user_id} received medium readiness response")
        else:
            await bot.send_message(user_id, f"{responses['low']}\n{CHANNEL_LINK}")
            logger.info(f"User {user_id} received low readiness response")
        
        # Очищаем данные пользователя, чтобы освободить память
        del user_data[user_id]
        logger.info(f"Cleared data for user {user_id}")
    except Exception as e:
        logger.error(f"Error processing test results for user {user_id}: {e}")
        await bot.send_message(user_id, "Произошла ошибка при обработке результатов. Пожалуйста, напишите /start чтобы начать заново.")

@router.message(Command("start"))
async def cmd_start(message: Message):
    """
    Обработать команду /start - инициализировать тест для пользователя.
    
    Args:
        message: Объект сообщения Telegram
    """
    try:
        if message.from_user is None:
            logger.error("User information is missing")
            await message.answer("Произошла ошибка при запуске теста. Пожалуйста, попробуйте еще раз позже.")
            return
            
        user_id = message.from_user.id
        username = message.from_user.username
        
        # Инициализируем данные пользователя
        user_data[user_id] = {
            "step": 0,
            "score": {"a": 0, "b": 0, "c": 0},
            "username": username,
            "answers": []  # Сохраняем ответы пользователя
        }
        
        # Отправляем приветственное сообщение
        await message.answer("Привет. Ответь на 10 коротких вопросов — и мы поймём, готова ли ты к трансформации.")
        logger.info(f"Started test for user {user_id}")
        
        # Отправляем первый вопрос
        await send_question(message.bot, user_id)
    except Exception as e:
        user_id = message.from_user.id if message.from_user else "unknown"
        logger.error(f"Error starting test for user {user_id}: {e}")
        await message.answer("Произошла ошибка при запуске теста. Пожалуйста, попробуйте еще раз позже.")

@router.message(Command("help"))
async def cmd_help(message: Message):
    """
    Обработать команду /help - предоставить информацию о боте.
    
    Args:
        message: Объект сообщения Telegram
    """
    help_text = (
        "Этот бот проводит тест для определения вашей готовности к личностной трансформации.\n\n"
        "Команды:\n"
        "/start - Начать тест\n"
        "/help - Показать эту справку\n\n"
        "Тест состоит из 10 вопросов. После завершения вы получите индивидуальную обратную связь."
    )
    await message.answer(help_text)
    if message.from_user:
        logger.info(f"Sent help information to user {message.from_user.id}")
    else:
        logger.info("Sent help information to user (unknown)")

@router.callback_query()
async def process_callback(call: CallbackQuery):
    """
    Обработать запросы обратного вызова от кнопок inline-клавиатуры.
    
    Args:
        call: Объект запроса обратного вызова
    """
    try:
        if call.from_user is None:
            logger.error("User information is missing in callback")
            await call.message.answer("Произошла ошибка. Пожалуйста, напишите /start чтобы начать заново.")
            await call.answer()
            return
            
        user_id = call.from_user.id
        
        # Проверяем, есть ли у пользователя активный тест
        if user_id not in user_data:
            await call.message.answer("Напиши /start чтобы начать тест.")
            await call.answer()
            return
        
        data = user_data[user_id]
        if call.data is None:
            logger.error(f"Callback data is missing for user {user_id}")
            await call.message.answer("Произошла ошибка. Пожалуйста, напишите /start чтобы начать заново.")
            await call.answer()
            return
            
        answer = call.data  # "a", "b", or "c"
        current_step = data["step"]
        
        # Обновляем оценку пользователя
        data["score"][answer] += 1
        
        # Сохраняем ответ пользователя с текстом вопроса и выбранным текстом ответа
        option_index = ord(answer) - ord('a')  # Преобразуем 'a', 'b', 'c' в 0, 1, 2
        question_text = questions[current_step]["q"]
        answer_text = questions[current_step]["a"][option_index]
        
        # Сохраняем ответ
        data["answers"].append({
            "question": question_text,
            "answer_option": answer,
            "answer_text": answer_text
        })
        
        # Переходим к следующему вопросу
        data["step"] += 1
        
        # Подтверждаем запрос обратного вызова
        await call.answer()
        
        # Проверяем, завершен ли тест
        if data["step"] < len(questions):
            # Отправляем следующий вопрос
            await send_question(call.bot, user_id)
        else:
            # Обрабатываем результаты теста
            await process_test_results(call.bot, user_id)
    except Exception as e:
        user_id = call.from_user.id if call.from_user else "unknown"
        logger.error(f"Error processing callback for user {user_id}: {e}")
        await call.message.answer("Произошла ошибка при обработке ответа. Пожалуйста, напишите /start чтобы начать заново.")
        await call.answer()

async def on_startup(bot):
    """
    Функция, вызываемая при запуске бота.
    
    Args:
        bot: Экземпляр Bot
    """
    logger.info("Bot is starting up...")
    # Здесь можно добавить любой код инициализации, который должен выполняться при запуске бота
    # Например, настройка команд бота
    await bot.set_my_commands([
        {"command": "start", "description": "Начать тест"},
        {"command": "help", "description": "Показать справку"}
    ])
    logger.info("Bot commands set")
    logger.info("Bot started successfully!")

async def on_shutdown(bot):
    """
    Функция, вызываемая при завершении работы бота.
    
    Args:
        bot: Экземпляр Bot
    """
    logger.info("Bot is shutting down...")
    logger.info("Bot shut down successfully!")

async def main():
    """
    Основная функция для инициализации и запуска бота.
    """
    try:
        # Инициализируем бота и диспетчера
        bot = Bot(
            token=BOT_TOKEN, 
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        
        # Регистрируем все обработчики
        dp.include_router(router)
        logger.info("Handlers registered successfully")
        
        # Настраиваем обработчики запуска и завершения
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        
        # Запускаем бота
        logger.info("Starting bot polling...")
        await dp.start_polling(bot, skip_updates=True)
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == "__main__":
    # Запуск бота
    asyncio.run(main())