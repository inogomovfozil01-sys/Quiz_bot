import json
import random
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

BOT_TOKEN = "8436402948:AAHugLr2sYKxngLQxcb0_7G7CxoFQ8wU8VI"
CHANNEL_ID = -1003242981049
ADMIN_ID = [6690476979]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

with open("questions.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

try:
    with open("used_questions.json", "r", encoding="utf-8") as f:
        used_questions = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    used_questions = {}
    with open("used_questions.json", "w", encoding="utf-8") as f:
        json.dump(used_questions, f, ensure_ascii=False, indent=4)

answered_users = {}  # {question_id: [user_ids]}


def get_remaining_questions():
    all_used = sum(used_questions.values(), [])
    return [q for q in questions if q["id"] not in all_used]


def save_used_question(question_id):
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in used_questions:
        used_questions[today] = []
    used_questions[today].append(question_id)
    with open("used_questions.json", "w", encoding="utf-8") as f:
        json.dump(used_questions, f, ensure_ascii=False, indent=4)


async def send_question(q):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=opt, callback_data=f"answer|{q['id']}|{opt}")]
            for opt in q["options"]
        ]
    )
    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=f"❓ {q['question']}",
        reply_markup=keyboard
    )


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Привет! 👋 Я бот-викторина по BMW.\nИспользуй /admin, если у тебя есть права администратора.")


@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        await message.answer("🚫 Доступ запрещён")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Опубликовать вопрос", callback_data="publish_one")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")]
    ])
    await message.answer("Панель администратора:", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data in ["publish_one", "stats"])
async def admin_callbacks(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_ID:
        await callback.answer("🚫 Доступ запрещён", show_alert=True)
        return

    if callback.data == "publish_one":
        remaining = get_remaining_questions()
        if not remaining:
            remaining = questions
        q = random.choice(remaining)
        await send_question(q)
        save_used_question(q["id"])
        await callback.answer("✅ Вопрос опубликован!")

    elif callback.data == "stats":
        today = datetime.now().strftime("%Y-%m-%d")
        today_q = used_questions.get(today, [])
        total = sum(len(v) for v in used_questions.values())
        msg = f"📊 Сегодня опубликовано: {len(today_q)}\nВсего: {total}"
        await callback.message.answer(msg)
        await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("answer|"))
async def handle_answer(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    _, qid, chosen = callback.data.split("|")

    if user_id in answered_users.get(qid, []):
        await callback.answer("⚠️ Вы уже ответили на этот вопрос.", show_alert=True)
        return

    q = next((x for x in questions if str(x["id"]) == qid), None)
    if not q:
        await callback.answer("Ошибка: вопрос не найден", show_alert=True)
        return

    correct = q["answer"]
    if chosen == correct:
        await callback.answer("✅ Верно!", show_alert=True)
    else:
        await callback.answer(f"❌ Неверно.\nПравильный ответ: {correct}", show_alert=True)

    if qid not in answered_users:
        answered_users[qid] = []
    answered_users[qid].append(user_id)


async def send_daily_question():
    today = datetime.now().strftime("%Y-%m-%d")
    if today in used_questions:
        return

    remaining = get_remaining_questions()
    if len(remaining) < 5:
        remaining = questions

    for q in random.sample(remaining, 5):
        await send_question(q)
        save_used_question(q["id"])


async def scheduler():
    while True:
        now = datetime.now()
        if now.hour == 10 and now.minute == 0:
            await send_daily_question()
            await asyncio.sleep(60)
        await asyncio.sleep(20)


async def main():
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)


if __name__ == "__main__":
    print("[INFO] Bot is working...")
    asyncio.run(main())