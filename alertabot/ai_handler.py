import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv
from db import get_profile_by_telegram_id

load_dotenv()

client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
Ты — умный и вежливый ИИ-ассистент сервиса Alerta, интегрированный в Telegram-бота.
Твоя задача — помогать пользователю, отвечать на его вопросы и предоставлять информацию об его аккаунте.
Общайся дружелюбно, на русском языке.

Если пользователь просит показать его профиль, информацию или статус, используй доступные функции (tools), чтобы получить реальные данные из базы.
"""

# Example of a tool to get user info
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_user_profile_info",
            "description": "Получить информацию о профиле пользователя из базы данных (имя пользователя, привязанные url).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

async def process_user_message(telegram_id: int, text: str, message_history: list = None) -> str:
    """
    Отправляет сообщение пользователя в OpenAI и возвращает ответ.
    """
    if message_history is None:
        message_history = []

    # Ensure system prompt is the first message
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + message_history
    messages.append({"role": "user", "content": text})

    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo", # or gpt-4o depending on preference
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        
        # Check if the model decided to call a function
        if response_message.tool_calls:
            # We handle the function call
            messages.append(response_message) # Append the assistant's function call message
            
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                
                if function_name == "get_user_profile_info":
                    profile = get_profile_by_telegram_id(telegram_id)
                    if profile:
                        function_response = json.dumps({
                            "status": "success", 
                            "username": profile.get("username", "Неизвестно"),
                            "urls": profile.get("urls", [])
                        }, ensure_ascii=False)
                    else:
                        function_response = json.dumps({"status": "error", "message": "Профиль не найден. Возможно, аккаунт не привязан."}, ensure_ascii=False)
                else:
                    function_response = json.dumps({"status": "error", "message": f"Неизвестная функция: {function_name}"}, ensure_ascii=False)
                
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                })
            
            # Send the function response back to OpenAI to get the final text answer
            second_response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages
            )
            return second_response.choices[0].message.content

        return response_message.content

    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return "Извините, произошла ошибка при обрабощении вашего запроса."
