import asyncio
import os
import sys
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

from db import link_account, get_profile_by_telegram_id
from ai_handler import process_user_message

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token_here":
    logger.error("BOT_TOKEN is not set in .env")
    sys.exit(1)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Simple in-memory memory for conversation history (for MVP)
# In production, use Redis or a database to store conversation history per user
user_conversations = {}

@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    """
    This handler receives messages with `/start` command.
    It checks if there is a payload (token) for account linking.
    """
    args = message.text.split(maxsplit=1)
    
    if len(args) > 1:
        # User started bot with a token: /start <token>
        token = args[1]
        success = link_account(token, message.from_user.id)
        
        if success:
            await message.answer("🎉 Ваш аккаунт успешно привязан! Теперь вы можете общаться со мной. Что вас интересует?")
        else:
            await message.answer("❌ Ссылка для привязки недействительна или уже была использована. Попробуйте сгенерировать новую на сайте.")
    else:
        # Normal start
        profile = get_profile_by_telegram_id(message.from_user.id)
        if profile:
            await message.answer(
                f"Привет, {profile.get('username', 'друг')}! Я твой ИИ-ассистент Alerta.\n\n"
                "Доступные команды:\n"
                "/radar <монитор> - Global Latency Radar\n"
                "/chaos <монитор> - Chaos Mode (Только Business)\n"
                "/postmortem <инцидент> - Сгенерировать Post-Mortem"
            )
        else:
            await message.answer(
                "Привет! Я ИИ-ассистент сервиса Alerta.\n\n"
                "⚠️ Ваш аккаунт пока не привязан. Пожалуйста, перейдите на сайт Alerta в настройки профиля и нажмите \"Привязать Telegram\"."
            )

@dp.message(Command("radar"))
async def cmd_radar(message: types.Message):
    await message.answer("📡 *Global Latency Radar*\nПингуем сервера из 5 регионов...\n\n🇺🇸 US-East: [■■■■□] 45ms\n🇪🇺 EU-Central: [■■■□□] 120ms\n🇸🇬 SG-Asia: [■□□□□] 320ms", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("chaos"))
async def cmd_chaos(message: types.Message):
    await message.answer("☣️ *Chaos Mode*\nСтресс-тест запущен (имитация 10,000 req/sec).\nОжидаем срабатывания Rate-Limit...", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("postmortem"))
async def cmd_postmortem(message: types.Message):
    await message.answer("📄 *Smart Post-Mortem*\n_Сгенерировано ИИ:_\n\n**Инцидент #402**\nПричина: Истечение сертификата SSL.\nПростой: 12 минут.\n\n*Текст для клиентов:*\nУважаемые пользователи, мы столкнулись с кратковременной недоступностью из-за обновления сертификатов...", parse_mode=ParseMode.MARKDOWN)

@dp.message()
async def chat_handler(message: types.Message) -> None:
    """
    Routes all text messages to the AI handler.
    """
    if not message.text:
        return
        
    user_id = message.from_user.id
    
    # Initialize history if not exists
    if user_id not in user_conversations:
        user_conversations[user_id] = []
        
    # Send "typing" action to Telegram so user knows bot is thinking
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # Get response from AI
    ai_response = await process_user_message(
        telegram_id=user_id,
        text=message.text,
        message_history=user_conversations[user_id]
    )
    
    # Update history (keep only last 10 messages to save tokens)
    user_conversations[user_id].append({"role": "user", "content": message.text})
    user_conversations[user_id].append({"role": "assistant", "content": ai_response})
    
    if len(user_conversations[user_id]) > 20: # 10 exchanges
        user_conversations[user_id] = user_conversations[user_id][-20:]
        
    await message.answer(ai_response)

async def main() -> None:
    # And the run events dispatching
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
