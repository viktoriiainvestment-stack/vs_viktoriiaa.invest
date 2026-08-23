import os
import telebot
import anthropic

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
claude = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

SYSTEM_PROMPT = """
Ты — профессиональный контент-стратег и эксперт по автоворонкам.
Твоя задача — принимать от пользователя аналитику прошлых постов, делать выводы и создавать новый контент-план.

Структура твоей работы:
1. Краткая рефлексия (2 вывода: что сработало лучше всего и почему).
2. Контент-план на 3 поста/Reels с учетом прошлых ошибок и успехов.
3. Формат для каждого поста: [Рубрика] -> [Хук/Заголовок] -> [Сценарий/Текст] -> [Призыв к действию / CTA].

Пиши четко, без вводного флуда, с фокусом на привлечение лидов.
"""

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    bot.reply_to(message, "🧠 Анализирую показатели и генерирую новый план...")
    
    try:
        response = claude.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": message.text}
            ]
        )
        
        reply_text = response.content[0].text
        bot.send_message(message.chat.id, reply_text)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {str(e)}")

print("Бот запущен...")
bot.polling(none_stop=True)
