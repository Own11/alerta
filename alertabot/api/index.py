import os
import sys
import logging
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# Import logic from the root folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import link_account, get_profile_by_telegram_id
from ai_handler import process_user_message

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") # e.g. https://your-vercel-app.vercel.app/api/webhook

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
app = FastAPI()

user_conversations = {}

@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        token = args[1]
        success = link_account(token, message.from_user.id)
        if success:
            await message.answer("🎉 Ваш аккаунт успешно привязан! Теперь вы можете общаться со мной.")
        else:
            await message.answer("❌ Ссылка для привязки недействительна или уже была использована.")
    else:
        profile = get_profile_by_telegram_id(message.from_user.id)
        if profile:
            await message.answer(f"Привет, {profile.get('username', 'друг')}! Я твой ИИ-ассистент Alerta.")
        else:
            await message.answer("Привет! Я ИИ-ассистент. Ваш аккаунт пока не привязан.")

@dp.message()
async def chat_handler(message: types.Message) -> None:
    if not message.text:
        return
        
    user_id = message.from_user.id
    if user_id not in user_conversations:
        user_conversations[user_id] = []
        
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    ai_response = await process_user_message(
        telegram_id=user_id,
        text=message.text,
        message_history=user_conversations[user_id]
    )
    
    user_conversations[user_id].append({"role": "user", "content": message.text})
    user_conversations[user_id].append({"role": "assistant", "content": ai_response})
    if len(user_conversations[user_id]) > 20:
        user_conversations[user_id] = user_conversations[user_id][-20:]
        
    await message.answer(ai_response)

@app.on_event("startup")
async def on_startup():
    if WEBHOOK_URL:
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url != f"{WEBHOOK_URL}/api/webhook":
            await bot.set_webhook(url=f"{WEBHOOK_URL}/api/webhook")
            logger.info(f"Webhook set to {WEBHOOK_URL}/api/webhook")

@app.post("/api/webhook")
async def bot_webhook(request: Request):
    update_data = await request.json()
    update = types.Update(**update_data)
    await dp.feed_update(bot=bot, update=update)
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"status": "Bot is running on Vercel!"}
