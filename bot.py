# ============================================================
# 🧭 Бот «Путеводитель РУК»
# Твой личный гид по Российскому университету кооперации
# Меню для всех + админка по командам
# ============================================================

import asyncio
import json
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.chat_action import ChatActionSender
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ============================================================
# 🔑 НАСТРОЙКА
# ============================================================
BOT_TOKEN = "8565048229:AAGJqVuNRLBgnj1KkwkFDVjLW-w0aQejnSY"
ADMIN_ID = 5965370780

# Файлы данных
GROUPS_FILE = "groups.json"
SCHEDULE_FILE = "schedule.json"
BELLS_FILE = "bells.json"
ANNOUNCES_FILE = "announces.json"
PLACES_FILE = "places.json"
USERS_FILE = "users.json"
CHECKLIST_FILE = "checklists.json"
USER_GROUPS_FILE = "user_groups.json"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ============================================================
# 🏛 ИНФОРМАЦИЯ О РУК
# ============================================================

RUK_INFO = {
    "name": "Российский университет кооперации",
    "short_name": "РУК",
    "founded": "1912 год",
    "founder": "Центросоюз Российской Федерации",
    "address": "Московская обл., г. Мытищи, ул. Веры Волошиной, д. 12/30",
    "phone": "+7 (495) 640-57-11",
    "phone2": "+7 (495) 785-76-78",
    "email": "priem@ruc.su",
    "site": "https://ruc.su",
    "work_time": "Пн–Пт: 9:00–18:00, Сб: 9:00–14:00",
}


# ============================================================
# 💾 РАБОТА С ФАЙЛАМИ
# ============================================================

def _load(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Ошибка чтения {path}: {e}")
        return default


def _save(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка сохранения {path}: {e}")


GROUPS = _load(GROUPS_FILE, [])
SCHEDULE = _load(SCHEDULE_FILE, {})
BELLS = _load(BELLS_FILE, [])
ANNOUNCES = _load(ANNOUNCES_FILE, [])
PLACES = _load(PLACES_FILE, {})
USERS = set(_load(USERS_FILE, []))
CHECKLISTS = _load(CHECKLIST_FILE, {})
USER_GROUPS = _load(USER_GROUPS_FILE, {})


def save_users():
    _save(USERS_FILE, list(USERS))


# Звонки по умолчанию
if not BELLS:
    BELLS = [
        {"name": "1 пара", "start": "09:00", "end": "10:30", "break": "10 мин"},
        {"name": "2 пара", "start": "10:40", "end": "12:10", "break": "30 мин"},
        {"name": "3 пара", "start": "12:40", "end": "14:10", "break": "10 мин"},
        {"name": "4 пара", "start": "14:20", "end": "15:50", "break": "10 мин"},
        {"name": "5 пара", "start": "16:00", "end": "17:30", "break": "10 мин"},
        {"name": "6 пара", "start": "17:40", "end": "19:10", "break": "—"},
    ]

# Места на карте по умолчанию
if not PLACES:
    PLACES = {
        "📋 Деканат (основной)": {
            "where": "Корпус 3, 3 этаж, кабинет 304",
            "steps": (
                "1️⃣ Заходишь в главный вход.\n"
                "2️⃣ Идёшь прямо по коридору до лестницы.\n"
                "3️⃣ Поднимаешься на 3 этаж.\n"
                "4️⃣ Находишь кабинет 304.\n\n"
                "💡 Здесь получают справки, решают вопросы по учёбе."
            ),
        },
        "🩺 Медицинский кабинет": {
            "where": "Корпус 2, 1 этаж",
            "steps": (
                "1️⃣ От главного входа идёшь к лестнице во 2-й корпус.\n"
                "2️⃣ Смотришь на указатели.\n"
                "3️⃣ Спускаешься на 1 этаж 2-го корпуса.\n\n"
                "💡 Здесь справки для физкультуры, медосмотр."
            ),
        },
        "📚 Читальный / компьютерный зал": {
            "where": "Корпус 3, 3 этаж",
            "steps": (
                "1️⃣ Идёшь в 3-й корпус.\n"
                "2️⃣ Поднимаешься на 3 этаж.\n"
                "3️⃣ Находишь читальный / компьютерный зал.\n\n"
                "💡 Готовься к парам, работай за ПК, бери учебники."
            ),
        },
        "🍽 Столовая": {
            "where": "Уточни у куратора",
            "steps": (
                "📍 Точное расположение уточняй у куратора "
                "или на стенде у входа.\n\n"
                "💡 Работает в перерывах между парами."
            ),
        },
        "🏀 Спортзал": {
            "where": "Уточни у куратора",
            "steps": (
                "📍 Точное расположение уточняй у куратора.\n\n"
                "💡 Занятия по физкультуре и секции."
            ),
        },
        "🚻 Туалеты": {
            "where": "На каждом этаже",
            "steps": (
                "📍 Туалеты есть на каждом этаже всех корпусов.\n\n"
                "💡 Обычно в конце коридора."
            ),
        },
        "🚪 Гардероб": {
            "where": "1 этаж главного корпуса",
            "steps": (
                "1️⃣ Заходишь в главный вход.\n"
                "2️⃣ Гардероб прямо или слева от входа.\n\n"
                "💡 Оставляй верхнюю одежду здесь."
            ),
        },
    }
    _save(PLACES_FILE, PLACES)


# ============================================================
# 🎛 СОСТОЯНИЯ FSM
# ============================================================

class BellsStates(StatesGroup):
    waiting_data = State()


class ScheduleStates(StatesGroup):
    waiting_group = State()
    waiting_day = State()
    waiting_pairs = State()


class DelDayStates(StatesGroup):
    waiting_group = State()
    waiting_day = State()


class GroupStates(StatesGroup):
    waiting_name = State()


class DelGroupStates(StatesGroup):
    waiting_name = State()


class AnnounceStates(StatesGroup):
    waiting_text = State()


class DelAnnounceStates(StatesGroup):
    waiting_number = State()


class PlaceStates(StatesGroup):
    waiting_name = State()
    waiting_where = State()
    waiting_steps = State()


class DelPlaceStates(StatesGroup):
    waiting_name = State()


# ============================================================
# ⌨️ КЛАВИАТУРЫ
# ============================================================

def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧭 Путеводитель")],
            [KeyboardButton(text="⏰ Звонки")],
            [KeyboardButton(text="📅 Расписание")],
            [KeyboardButton(text="👥 Моя группа")],
            [KeyboardButton(text="📢 Объявления")],
            [KeyboardButton(text="📋 Чек-лист"), KeyboardButton(text="📖 Словарь")],
            [KeyboardButton(text="🆘 SOS"), KeyboardButton(text="🏛 О РУК")],
            [KeyboardButton(text="📞 Контакты"), KeyboardButton(text="🔗 Ссылки")],
        ],
        resize_keyboard=True,
    )


def back_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ В главное меню")]],
        resize_keyboard=True,
    )


# ============================================================
# 🛠 ХЕЛПЕРЫ
# ============================================================

async def send_typing(message: Message, text: str, **kwargs):
    async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
        await asyncio.sleep(0.3)
        await message.answer(text, **kwargs)


async def auto_delete(message: Message, delay: int = 5):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ============================================================
# 🚀 СТАРТ / МЕНЮ
# ============================================================

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    USERS.add(message.from_user.id)
    save_users()

    async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
        await asyncio.sleep(0.6)

    await message.answer(
        f"👋 Привет, *{message.from_user.first_name}*!\n\n"
        "Я — *Путеводитель РУК* 🧭\n"
        "Твой личный гид по Российскому университету кооперации.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🧭 *Путеводитель* — куда хочешь дойти?\n"
        "⏰ *Звонки* — расписание пар\n"
        "📅 *Расписание* — занятия по группам\n"
        "👥 *Моя группа* — выбрать свою группу\n"
        "📢 *Объявления* — важное от кураторов\n"
        "📋 *Чек-лист* — что сделать первокурснику\n"
        "📖 *Словарь* — расшифровка терминов\n"
        "🆘 *SOS* — что делать, если…\n"
        "🏛 *О РУК* — история и контакты\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Выбирай в меню ниже 👇",
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )


@dp.message(Command("menu"))
@dp.message(F.text == "⬅️ В главное меню")
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    await send_typing(message, "🏠 *Главное меню*",
                      parse_mode="Markdown",
                      reply_markup=main_menu())


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await send_typing(
        message,
        "ℹ️ *Справка*\n\n"
        "*Команды:*\n"
        "/start — запустить\n"
        "/menu — главное меню\n"
        "/navigator — путеводитель\n"
        "/bells — звонки\n"
        "/schedule — расписание\n"
        "/announces — объявления\n"
        "/about — о боте",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


@dp.message(Command("about"))
async def cmd_about(message: Message):
    await send_typing(
        message,
        "🤖 *О боте «Путеводитель РУК»*\n\n"
        "Бот для студентов Российского университета кооперации.\n\n"
        "📌 *Что умеет:*\n"
        "• карта-путеводитель по колледжу\n"
        "• расписание звонков и занятий\n"
        "• объявления от кураторов\n"
        "• чек-лист первокурсника\n"
        "• словарь студента и SOS-помощь\n\n"
        "💙 Сделан с заботой о студентах.",
        parse_mode="Markdown",
        reply_markup=back_menu(),
    )


# ============================================================
# 🧭 ПУТЕВОДИТЕЛЬ
# ============================================================

@dp.message(Command("navigator"))
@dp.message(F.text == "🧭 Путеводитель")
async def navigator(message: Message):
    if not PLACES:
        await send_typing(message,
                          "🧭 *Путеводитель*\n\nКарта пока пуста.",
                          parse_mode="Markdown",
                          reply_markup=back_menu())
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=f"nav:{name}")]
            for name in PLACES
        ]
    )
    await send_typing(
        message,
        "🧭 *Куда хочешь дойти?*\n\nВыбери место — покажу маршрут 👇",
        parse_mode="Markdown",
        reply_markup=kb,
    )


@dp.callback_query(F.data.startswith("nav:"))
async def show_route(callback: CallbackQuery):
    name = callback.data.split(":", 1)[1]
    place = PLACES.get(name)
    if not place:
        await callback.answer("Не найдено", show_alert=True)
        return
    text = (
        f"*{name}*\n\n"
        f"📍 *Где:* {place['where']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🗺 *Как дойти:*\n\n{place['steps']}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    await callback.message.answer(text, parse_mode="Markdown",
                                  reply_markup=back_menu())
    await callback.answer()


# ============================================================
# 👥 МОЯ ГРУППА
# ============================================================

@dp.message(F.text == "👥 Моя группа")
async def my_group(message: Message):
    if not GROUPS:
        await send_typing(message,
                          "👥 *Группы*\n\nПока список пуст.",
                          parse_mode="Markdown",
                          reply_markup=back_menu())
        return

    uid = str(message.from_user.id)
    current = USER_GROUPS.get(uid)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{'✅ ' if g == current else ''}📚 {g}",
                callback_data=f"mygrp:{g}")]
            for g in GROUPS
        ]
    )
    text = "👥 *Выбери свою группу:*"
    if current:
        text += f"\n\nТекущая: *{current}*"
    await send_typing(message, text, parse_mode="Markdown", reply_markup=kb)


@dp.callback_query(F.data.startswith("mygrp:"))
async def set_my_group(callback: CallbackQuery):
    grp = callback.data.split(":", 1)[1]
    uid = str(callback.from_user.id)
    USER_GROUPS[uid] = grp
    _save(USER_GROUPS_FILE, USER_GROUPS)
    await callback.message.answer(
        f"✅ Ты выбрал группу *{grp}*\n\n"
        f"При нажатии «📅 Расписание» покажу её.",
        parse_mode="Markdown",
        reply_markup=back_menu(),
    )
    await callback.answer()


# ============================================================
# ⏰ ЗВОНКИ
# ============================================================

@dp.message(Command("bells"))
@dp.message(F.text == "⏰ Звонки")
async def bells_cmd(message: Message):
    if not BELLS:
        await send_typing(message, "⏰ Звонков пока нет.",
                          reply_markup=back_menu())
        return
    text = "⏰ *Расписание звонков*\n\n━━━━━━━━━━━━━━━━━━━━\n"
    for b in BELLS:
        text += (f"🔔 *{b['name']}*  {b['start']} — {b['end']}\n"
                 f"     ⏸ {b['break']}\n\n")
    text += "━━━━━━━━━━━━━━━━━━━━"
    await send_typing(message, text, parse_mode="Markdown",
                      reply_markup=back_menu())


# ============================================================
# 📅 РАСПИСАНИЕ
# ============================================================

@dp.message(Command("schedule"))
@dp.message(F.text == "📅 Расписание")
async def schedule_cmd(message: Message):
    if not SCHEDULE:
        await send_typing(message,
                          "📅 *Расписание*\n\nПока пусто.",
                          parse_mode="Markdown",
                          reply_markup=back_menu())
        return

    uid = str(message.from_user.id)
    my_grp = USER_GROUPS.get(uid)

    if my_grp and my_grp in SCHEDULE:
        days = SCHEDULE[my_grp]
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"📆 {day}",
                                      callback_data=f"sched_day:{my_grp}:{day}")]
                for day in days
            ] + [[InlineKeyboardButton(text="🔄 Другая группа",
                                       callback_data="sched_all")]]
        )
        await send_typing(message,
                          f"📅 *{my_grp}*\n\nВыбери день 👇",
                          parse_mode="Markdown",
                          reply_markup=kb)
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"📚 {grp}",
                                  callback_data=f"sched_grp:{grp}")]
            for grp in SCHEDULE
        ]
    )
    await send_typing(message,
                      "📅 *Расписание*\n\nВыбери группу 👇",
                      parse_mode="Markdown",
                      reply_markup=kb)


@dp.callback_query(F.data == "sched_all")
async def sched_all(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"📚 {grp}",
                                  callback_data=f"sched_grp:{grp}")]
            for grp in SCHEDULE
        ]
    )
    await callback.message.answer("📅 *Выбери группу:*",
                                  parse_mode="Markdown",
                                  reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("sched_grp:"))
async def show_group_days(callback: CallbackQuery):
    grp = callback.data.split(":", 1)[1]
    days = SCHEDULE.get(grp, {})
    if not days:
        await callback.answer("Пусто", show_alert=True)
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"📆 {day}",
                                  callback_data=f"sched_day:{grp}:{day}")]
            for day in days
        ]
    )
    await callback.message.answer(f"📚 *{grp}*\n\nВыбери день 👇",
                                  parse_mode="Markdown",
                                  reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("sched_day:"))
async def show_day(callback: CallbackQuery):
    _, grp, day = callback.data.split(":", 2)
    pairs = SCHEDULE.get(grp, {}).get(day, [])
    if not pairs:
        await callback.message.answer(f"📅 *{grp}, {day}*\n\n🎉 Пар нет!",
                                      parse_mode="Markdown",
                                      reply_markup=back_menu())
        await callback.answer()
        return
    text = f"📅 *{grp}, {day}*\n\n━━━━━━━━━━━━━━━━━━━━\n"
    for i, pair in enumerate(pairs, 1):
        text += f"*{i}.* {pair}\n"
    text += "━━━━━━━━━━━━━━━━━━━━"
    await callback.message.answer(text, parse_mode="Markdown",
                                  reply_markup=back_menu())
    await callback.answer()


# ============================================================
# 📢 ОБЪЯВЛЕНИЯ
# ============================================================

@dp.message(Command("announces"))
@dp.message(F.text == "📢 Объявления")
async def announces_cmd(message: Message):
    if not ANNOUNCES:
        await send_typing(message,
                          "📢 *Объявления*\n\nПока нет активных.",
                          parse_mode="Markdown",
                          reply_markup=back_menu())
        return
    text = "📢 *Объявления*\n\n━━━━━━━━━━━━━━━━━━━━\n"
    for i, a in enumerate(ANNOUNCES, 1):
        text += f"*{i}.* {a['text']}\n🕐 _{a['date']}_\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━"
    await send_typing(message, text, parse_mode="Markdown",
                      reply_markup=back_menu())


# ============================================================
# 📋 ЧЕК-ЛИСТ
# ============================================================

CHECKLIST_ITEMS = [
    "Познакомиться с куратором",
    "Записать номер куратора",
    "Узнать, где деканат (каб. 304)",
    "Найти свою группу в расписании",
    "Выбрать свою группу в боте",
    "Найти библиотеку и читальный зал",
    "Узнать, где столовая",
    "Оформить студенческий билет",
    "Получить логин/пароль от ЛК",
    "Взять справку об обучении",
    "Найти медкабинет",
    "Познакомиться с группой",
]


def checklist_text(done):
    text = "📋 *Чек-лист первокурсника*\n\n━━━━━━━━━━━━━━━━━━━━\n"
    for i, item in enumerate(CHECKLIST_ITEMS, 1):
        mark = "✅" if i in done else "⬜"
        text += f"{mark} {i}. {item}\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"Выполнено: *{len(done)}/{len(CHECKLIST_ITEMS)}*"
    return text


def checklist_kb(done):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{'✅' if i in done else '⬜'} {i}",
                                  callback_data=f"chk:{i}")]
            for i in range(1, len(CHECKLIST_ITEMS) + 1)
        ]
    )


@dp.message(F.text == "📋 Чек-лист")
async def checklist_cmd(message: Message):
    uid = str(message.from_user.id)
    done = CHECKLISTS.get(uid, [])
    await send_typing(message, checklist_text(done),
                      parse_mode="Markdown",
                      reply_markup=checklist_kb(done))


@dp.callback_query(F.data.startswith("chk:"))
async def toggle_check(callback: CallbackQuery):
    idx = int(callback.data.split(":", 1)[1])
    uid = str(callback.from_user.id)
    done = CHECKLISTS.get(uid, [])
    if idx in done:
        done.remove(idx)
    else:
        done.append(idx)
    CHECKLISTS[uid] = done
    _save(CHECKLIST_FILE, CHECKLISTS)
    try:
        await callback.message.edit_text(checklist_text(done),
                                         parse_mode="Markdown",
                                         reply_markup=checklist_kb(done))
    except Exception:
        pass
    await callback.answer()


# ============================================================
# 📖 СЛОВАРЬ
# ============================================================

DICTIONARY = {
    "Пара": "Занятие 1,5 часа (90 минут).",
    "Зачётка": "Зачётная книжка — документ с оценками.",
    "Сессия": "Период сдачи зачётов и экзаменов.",
    "Семестр": "Половина учебного года.",
    "Академ": "Академический отпуск — перерыв в учёбе.",
    "Куратор": "Преподаватель, закреплённый за группой.",
    "Деканат": "Административный отдел, где решают вопросы по учёбе.",
    "Ведомость": "Список студентов с оценками.",
    "Отработка": "Дополнительное занятие за пропуск.",
    "Зачёт": "Форма проверки знаний без оценки.",
    "Дифзачёт": "Зачёт с оценкой.",
    "Стипендия": "Денежная выплата за хорошую учёбу.",
    "ЛК": "Личный кабинет студента.",
    "СПО": "Среднее профессиональное образование.",
}


@dp.message(F.text == "📖 Словарь")
async def dict_cmd(message: Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=word, callback_data=f"dict:{word}")]
            for word in DICTIONARY
        ]
    )
    await send_typing(message,
                      "📖 *Словарь студента*\n\nВыбери термин 👇",
                      parse_mode="Markdown",
                      reply_markup=kb)


@dp.callback_query(F.data.startswith("dict:"))
async def show_dict(callback: CallbackQuery):
    word = callback.data.split(":", 1)[1]
    meaning = DICTIONARY.get(word)
    if not meaning:
        await callback.answer("Не найдено", show_alert=True)
        return
    await callback.message.answer(f"📖 *{word}*\n\n💡 {meaning}",
                                  parse_mode="Markdown",
                                  reply_markup=back_menu())
    await callback.answer()


# ============================================================
# 🆘 SOS
# ============================================================

SOS = {
    "Потерял студенческий": (
        "🆘 *Потерял студенческий*\n\n"
        "1️⃣ Сообщи в деканат (каб. 304).\n"
        "2️⃣ Напиши заявление на восстановление.\n"
        "3️⃣ Получи новый билет.\n\n"
        "💡 До восстановления — используй справку об обучении."
    ),
    "Заболел и пропустил пары": (
        "🆘 *Заболел, пропустил пары*\n\n"
        "1️⃣ Возьми справку у врача.\n"
        "2️⃣ Отдай в деканат.\n"
        "3️⃣ Уточни у куратора, что отработать.\n\n"
        "💡 Без справки пропуски = прогулы."
    ),
    "Не нашёл кабинет": (
        "🆘 *Не нашёл кабинет*\n\n"
        "1️⃣ Спроси у охраны на входе.\n"
        "2️⃣ Найди стенд с расписанием.\n"
        "3️⃣ Спроси у студентов.\n\n"
        "💡 Используй «🧭 Путеводитель» в меню."
    ),
    "Конфликт с преподавателем": (
        "🆘 *Конфликт с преподавателем*\n\n"
        "1️⃣ Сохраняй спокойствие.\n"
        "2️⃣ Поговори с куратором.\n"
        "3️⃣ Обратись в деканат.\n\n"
        "💡 Деканат — посредник."
    ),
    "Не сдал зачёт": (
        "🆘 *Не сдал зачёт*\n\n"
        "1️⃣ Узнай дату пересдачи.\n"
        "2️⃣ Подготовься.\n"
        "3️⃣ Приди вовремя.\n\n"
        "💡 3 несдачи — комиссия."
    ),
}


@dp.message(F.text == "🆘 SOS")
async def sos_cmd(message: Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=q, callback_data=f"sos:{q}")]
            for q in SOS
        ]
    )
    await send_typing(message,
                      "🆘 *Что делать, если…*\n\nВыбери ситуацию 👇",
                      parse_mode="Markdown",
                      reply_markup=kb)


@dp.callback_query(F.data.startswith("sos:"))
async def show_sos(callback: CallbackQuery):
    q = callback.data.split(":", 1)[1]
    ans = SOS.get(q)
    if not ans:
        await callback.answer("Не найдено", show_alert=True)
        return
    await callback.message.answer(ans, parse_mode="Markdown",
                                  reply_markup=back_menu())
    await callback.answer()


# ============================================================
# 🏛 О РУК
# ============================================================

@dp.message(F.text == "🏛 О РУК")
async def about_ruk(message: Message):
    info = RUK_INFO
    await send_typing(
        message,
        f"🏛 *{info['name']}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 *Основан:* {info['founded']}\n"
        f"🏛 *Учредитель:* {info['founder']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📍 *Адрес:*\n{info['address']}\n\n"
        f"🕐 *Режим работы:*\n{info['work_time']}\n\n"
        f"📞 *Телефоны:*\n{info['phone']}\n{info['phone2']}\n\n"
        f"✉️ *Email:* {info['email']}\n"
        f"🌐 *Сайт:* {info['site']}\n\n"
        "💡 *Совет:* приди за 15 минут до первой пары.",
        parse_mode="Markdown",
        reply_markup=back_menu(),
    )


# ============================================================
# 📞 КОНТАКТЫ И ССЫЛКИ
# ============================================================

@dp.message(F.text == "📞 Контакты")
async def contacts(message: Message):
    info = RUK_INFO
    await send_typing(
        message,
        "📞 *Контакты РУК*\n\n"
        f"📍 {info['address']}\n"
        f"☎️ {info['phone']}\n"
        f"☎️ {info['phone2']}\n"
        f"✉️ {info['email']}\n"
        f"🌐 {info['site']}\n\n"
        f"🕐 {info['work_time']}",
        parse_mode="Markdown",
        reply_markup=back_menu(),
    )


@dp.message(F.text == "🔗 Ссылки")
async def links_cmd(message: Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Официальный сайт РУК",
                                  url="https://ruc.su")],
            [InlineKeyboardButton(text="👤 Личный кабинет",
                                  url="https://lk.ruc.su")],
        ]
    )
    await send_typing(message, "🔗 *Полезные ссылки:*",
                      parse_mode="Markdown", reply_markup=kb)
    await message.answer("👆 Выбери раздел", reply_markup=back_menu())


# ============================================================
# 👨‍💼 АДМИНКА (по командам, студенты не видят)
# ============================================================

@dp.message(Command("admin"))
async def admin_cmd(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для админа.")
        return
    await state.clear()
    await message.answer(
        "👨‍💼 *Админ-панель*\n\n"
        "Все команды вводятся вручную:\n\n"
        "👥 *Группы:*\n"
        "/add_group — добавить группу\n"
        "/del_group — удалить группу\n"
        "/list_groups — список групп\n\n"
        "📅 *Расписание:*\n"
        "/set_schedule — добавить пары\n"
        "/del_day — удалить день\n\n"
        "⏰ *Звонки:*\n"
        "/set_bells — задать звонки\n\n"
        "📢 *Объявления:*\n"
        "/announce — создать\n"
        "/del_announce — удалить\n"
        "/clear_announces — очистить всё\n\n"
        "📍 *Карта:*\n"
        "/add_place — добавить место\n"
        "/del_place — удалить место\n"
        "/list_places — список мест",
        parse_mode="Markdown",
    )


# ---------- Группы ----------

@dp.message(Command("add_group"))
async def add_group_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для админа.")
        return    await state.set_state(GroupStates.waiting_name)
    await message.answer(
        "👥 *Добавление группы*\n\n"
        "Введи название (например, `ИС-11`):\n\n"
        "💡 `/cancel` — отмена",
        parse_mode="Markdown",
    )


@dp.message(GroupStates.waiting_name)
async def add_group_finish(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_menu())
        return
    name = message.text.strip()
    if name in GROUPS:
        await message.answer("⚠️ Такая группа уже есть.")
        return
    GROUPS.append(name)
    _save(GROUPS_FILE, GROUPS)
    await state.clear()
    msg = await message.answer(f"✅ Группа *{name}* добавлена",
                               parse_mode="Markdown",
                               reply_markup=main_menu())
    await auto_delete(msg, 5)


@dp.message(Command("del_group"))
async def del_group_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для админа.")
        return
    if not GROUPS:
        await message.answer("Групп нет.")
        return
    await state.set_state(DelGroupStates.waiting_name)
    lst = ", ".join(f"`{g}`" for g in GROUPS)
    await message.answer(f"Введи группу для удаления:\n{lst}",
                         parse_mode="Markdown")


@dp.message(DelGroupStates.waiting_name)
async def del_group_finish(message: Message, state: FSMContext):
    name = message.text.strip()
    if name in GROUPS:
        GROUPS.remove(name)
        _save(GROUPS_FILE, GROUPS)
        if name in SCHEDULE:
            del SCHEDULE[name]
            _save(SCHEDULE_FILE, SCHEDULE)
        await state.clear()
        msg = await message.answer(f"✅ Группа *{name}* удалена",
                                   parse_mode="Markdown",
                                   reply_markup=main_menu())
        await auto_delete(msg, 5)
    else:
        await message.answer("❌ Группа не найдена.")


@dp.message(Command("list_groups"))
async def list_groups(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для админа.")
        return
    if not GROUPS:
        await message.answer("Групп нет.")
        return
    text = "👥 *Группы:*\n\n"
    for g in GROUPS:
        days = ", ".join(SCHEDULE.get(g, {}).keys()) or "—"
        text += f"📚 *{g}* — дни: {days}\n"
    await message.answer(text, parse_mode="Markdown")


# ---------- Звонки ----------

@dp.message(Command("set_bells"))
async def set_bells_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для админа.")
        return
    await state.set_state(BellsStates.waiting_data)
    await message.answer(
        "⏰ *Настройка звонков*\n\n"
        "Отправь список — каждая пара с новой строки:\n"
        "`название, начало, конец, перемена`\n\n"
        "Пример:\n"
        "`1 пара, 09:00, 10:30, 10 мин`\n"
        "`2 пара, 10:40, 12:10, 30 мин`\n\n"
        "💡 `/cancel` — отмена",
        parse_mode="Markdown",
    )


@dp.message(BellsStates.waiting_data)
async def set_bells_data(message: Message, state: FSMContext):
    global BELLS
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_menu())
        return
    try:
        lines = [l.strip() for l in message.text.split("\n") if l.strip()]
        new_bells = []
        for line in lines:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 4:
                raise ValueError("Мало полей")
            new_bells.append({
                "name": parts[0], "start": parts[1],
                "end": parts[2], "break": parts[3],
            })
        BELLS = new_bells
        _save(BELLS_FILE, BELLS)
        await state.clear()
        msg = await message.answer(f"✅ Звонки обновлены ({len(BELLS)})",
                                   reply_markup=main_menu())
        await auto_delete(msg, 5)
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}\n\n"
                             "Формат: `название, начало, конец, перемена`",
                             parse_mode="Markdown")


# ---------- Расписание ----------

@dp.message(Command("set_schedule"))
async def set_schedule_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для админа.")
        return
    await state.set_state(ScheduleStates.waiting_group)
    await message.answer(
        "📅 *Добавление расписания*\n\n"
        "Шаг 1/3 — введи *название группы*:\n\n"
        "💡 `/cancel` — отмена",
        parse_mode="Markdown",
    )


@dp.message(ScheduleStates.waiting_group)
async def set_sched_group(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_menu())
        return
    grp = message.text.strip()
    if grp not in GROUPS:
        GROUPS.append(grp)
        _save(GROUPS_FILE, GROUPS)
    await state.update_data(group=grp)
    await state.set_state(ScheduleStates.waiting_day)
    await message.answer(
        "Шаг 2/3 — введи *день недели* (`Пн`, `Вт`, `Ср`, `Чт`, `Пт`, `Сб`):",
        parse_mode="Markdown",
    )


@dp.message(ScheduleStates.waiting_day)
async def set_sched_day(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_menu())
        return
    await state.update_data(day=message.text.strip())
    await state.set_state(ScheduleStates.waiting_pairs)
    await message.answer(
        "Шаг 3/3 — введи пары через запятую.\n\n"
        "Пример:\n`Математика 201, Русский 305, Физкультура`",
        parse_mode="Markdown",
    )


@dp.message(ScheduleStates.waiting_pairs)
async def set_sched_pairs(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_menu())
        return
    data = await state.get_data()
    grp, day = data["group"], data["day"]
    pairs = [p.strip() for p in message.text.split(",") if p.strip()]
    SCHEDULE.setdefault(grp, {})[day] = pairs
    _save(SCHEDULE_FILE, SCHEDULE)
    await state.clear()
    msg = await message.answer(
        f"✅ Расписание для *{grp}* ({day}) сохранено!\nПар: {len(pairs)}",
        parse_mode="Markdown", reply_markup=main_menu())
    await auto_delete(msg, 5)


@dp.message(Command("del_day"))
async def del_day_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для админа.")
        return
    if not SCHEDULE:
        await message.answer("Расписание пусто.")
        return
    await state.set_state(DelDayStates.waiting_group)
    groups = ", ".join(f"`{g}`" for g in SCHEDULE)
    await message.answer(f"📅 Введи группу:\n{groups}",
                         parse_mode="Markdown")


@dp.message(DelDayStates.waiting_group)
async def del_day_group(message: Message, state: FSMContext):
    grp = message.text.strip()
    if grp not in SCHEDULE:
        await message.answer("❌ Группа не найдена.")
        return
    await state.update_data(group=grp)
    await state.set_state(DelDayStates.waiting_day)
    days = ", ".join(f"`{d}`" for d in SCHEDULE[grp])
    await message.answer(f"Введи день:\n{days}", parse_mode="Markdown")


@dp.message(DelDayStates.waiting_day)
async def del_day_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    grp, day = data["group"], message.text.strip()
    if day in SCHEDULE.get(grp, {}):
        del SCHEDULE[grp][day]
        if not SCHEDULE[grp]:
            del SCHEDULE[grp]
        _save(SCHEDULE_FILE, SCHEDULE)
        await state.clear()
        msg = await message.answer(f"✅ Удалено: {grp}, {day}",
                                   reply_markup=main_menu())
        await auto_delete(msg, 5)
    else:
        await message.answer("❌ День не найден.")


# ---------- Объявления ----------

@dp.message(Command("announce"))
async def announce_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для админа.")
        return
    await state.set_state(AnnounceStates.waiting_text)
    await message.answer(
        "📢 *Новое объявление*\n\n"
        "Напиши текст. Он будет разослан всем студентам.\n\n"
        "💡 `/cancel` — отмена",
        parse_mode="Markdown",
    )


@dp.message(AnnounceStates.waiting_text)
async def announce_send(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_menu())
        return
    text = message.text.strip()
    date = datetime.now().strftime("%d.%m.%Y %H:%M")
    ANNOUNCES.append({"text": text, "date": date})
    _save(ANNOUNCES_FILE, ANNOUNCES)
    await state.clear()

    sent = 0
    for uid in list(USERS):
        try:
            await bot.send_message(
                uid,
                f"📢 *Новое объявление!*\n\n{text}\n\n🕐 _{date}_",
                parse_mode="Markdown")
            sent += 1
        except Exception:
            pass

    await message.answer(
        f"✅ Объявление отправлено!\n📨 Доставлено: {sent} из {len(USERS)}",
        reply_markup=main_menu())


@dp.message(Command("del_announce"))
async def del_announce_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для админа.")
        return
    if not ANNOUNCES:
        await message.answer("Объявлений нет.")
        return
    text = "📢 *Объявления:*\n\n"
    for i, a in enumerate(ANNOUNCES, 1):
        text += f"*{i}.* {a['text'][:60]}...\n"
    text += "\nВведи *номер* для удаления:"
    await state.set_state(DelAnnounceStates.waiting_number)
    await message.answer(text, parse_mode="Markdown")


@dp.message(DelAnnounceStates.waiting_number)
async def del_announce_finish(message: Message, state: FSMContext):
    try:
        idx = int(message.text.strip()) - 1
        if 0 <= idx < len(ANNOUNCES):
            del ANNOUNCES[idx]
            _save(ANNOUNCES_FILE, ANNOUNCES)
            await state.clear()
            msg = await message.answer("✅ Удалено", reply_markup=main_menu())
            await auto_delete(msg, 5)
        else:
            await message.answer("❌ Неверный номер.")
    except ValueError:
        await message.answer("❌ Введи число.")


@dp.message(Command("clear_announces"))
async def clear_announces(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для админа.")
        return
    global ANNOUNCES
    ANNOUNCES = []
    _save(ANNOUNCES_FILE, ANNOUNCES)
    msg = await message.answer("✅ Все объявления удалены",
                               reply_markup=main_menu())
    await auto_delete(msg, 5)


# ---------- Карта мест ----------

@dp.message(Command("add_place"))
async def add_place_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для админа.")
        return
    await state.set_state(PlaceStates.waiting_name)
    await message.answer(
        "📍 *Добавление места на карту*\n\n"
        "Шаг 1/3 — введи *название* (например, `📚 Библиотека`):\n\n"
        "💡 Можно с эмодзи. `/cancel` — отмена",
        parse_mode="Markdown",
    )


@dp.message(PlaceStates.waiting_name)
async def add_place_name(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_menu())
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(PlaceStates.waiting_where)
    await message.answer(
        "Шаг 2/3 — введи *где находится* (например, `Корпус 3, 3 этаж`):",
        parse_mode="Markdown",
    )


@dp.message(PlaceStates.waiting_where)
async def add_place_where(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_menu())
        return
    await state.update_data(where=message.text.strip())
    await state.set_state(PlaceStates.waiting_steps)
    await message.answer(
        "Шаг 3/3 — напиши *маршрут по шагам* (каждый шаг с новой строки):",
        parse_mode="Markdown",
    )


@dp.message(PlaceStates.waiting_steps)
async def add_place_steps(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=main_menu())
        return
    data = await state.get_data()
    PLACES[data["name"]] = {
        "where": data["where"],
        "steps": message.text.strip(),
    }
    _save(PLACES_FILE, PLACES)
    await state.clear()
    msg = await message.answer(
        f"✅ Место *{data['name']}* добавлено!",
        parse_mode="Markdown", reply_markup=main_menu())
    await auto_delete(msg, 5)


@dp.message(Command("del_place"))
async def del_place_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для админа.")
        return
    if not PLACES:
        await message.answer("Карта пуста.")
        return
    await state.set_state(DelPlaceStates.waiting_name)
    lst = "\n".join(f"• `{n}`" for n in PLACES)
    await message.answer(f"Введи название места для удаления:\n\n{lst}",
                         parse_mode="Markdown")


@dp.message(DelPlaceStates.waiting_name)
async def del_place_finish(message: Message, state: FSMContext):
    name = message.text.strip()
    if name in PLACES:
        del PLACES[name]
        _save(PLACES_FILE, PLACES)
        await state.clear()
        msg = await message.answer(f"✅ Место *{name}* удалено",
                                   parse_mode="Markdown",
                                   reply_markup=main_menu())
        await auto_delete(msg, 5)
    else:
        await message.answer("❌ Место не найдено.")


@dp.message(Command("list_places"))
async def list_places(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для админа.")
        return
    if not PLACES:
        await message.answer("Карта пуста.")
        return
    text = "📍 *Места на карте:*\n\n"
    for name, p in PLACES.items():
        text += f"• *{name}* — {p['where']}\n"
    await message.answer(text, parse_mode="Markdown")


# ============================================================
# 🤔 FALLBACK — обязательно последним!
# ============================================================

@dp.message()
async def fallback(message: Message):
    await message.answer(
        "🤔 Я тебя не понял. Воспользуйся кнопками меню "
        "или командой /menu.",
        reply_markup=main_menu(),
    )


# ============================================================
# ▶️ ЗАПУСК
# ============================================================

async def main():
    print("🧭 Бот «Путеводитель РУК» запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен")