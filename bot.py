# ============================================================
# 🤖 Бот «Путеводитель РУК»
# ============================================================

import asyncio
import json
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    BotCommand, BotCommandScopeDefault,
)
from aiogram.utils.chat_action import ChatActionSender
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ============================================================
# 🔑 НАСТРОЙКА
# ============================================================
BOT_TOKEN = "8565048229:AAGJqVuNRLBgnj1KkwkFDVjLW-w0aQejnSY"
ADMIN_ID = 5965370780

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
# 📚 ДАННЫЕ О РУК
# ============================================================

RUK_INFO = {
    "name": "Российский университет кооперации",
    "founded": "1912 год",
    "founder": "Центросоюз Российской Федерации",
    "address": "Московская обл., г. Мытищи, ул. Веры Волошиной, д. 12/30",
    "phone": "+7 (495) 640-57-11",
    "phone2": "+7 (495) 785-76-78",
    "email": "priem@ruc.su",
    "site": "https://ruc.su",
    "work_time": "Пн–Пт: 9:00–18:00, Сб: 9:00–14:00",
}


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


if not BELLS:
    BELLS = [
        {"name": "1 пара", "start": "09:00", "end": "10:30", "break": "10 мин"},
        {"name": "2 пара", "start": "10:40", "end": "12:10", "break": "30 мин"},
        {"name": "3 пара", "start": "12:40", "end": "14:10", "break": "10 мин"},
        {"name": "4 пара", "start": "14:20", "end": "15:50", "break": "10 мин"},
        {"name": "5 пара", "start": "16:00", "end": "17:30", "break": "10 мин"},
        {"name": "6 пара", "start": "17:40", "end": "19:10", "break": "—"},
    ]

if not PLACES:
    PLACES = {
        "📋 Деканат (основной)": {
            "where": "Корпус 3, 3 этаж, каб. 304",
            "steps": (
                "1️⃣ Заходишь в главный вход.\n"
                "2️⃣ Идёшь прямо до лестницы.\n"
                "3️⃣ Поднимаешься на 3 этаж.\n"
                "4️⃣ Находишь кабинет 304."
            ),
        },
        "🩺 Медицинский кабинет": {
            "where": "Корпус 2, 1 этаж",
            "steps": (
                "1️⃣ Идёшь к лестнице во 2-й корпус.\n"
                "2️⃣ Смотришь на указатели.\n"
                "3️⃣ Спускаешься на 1 этаж."
            ),
        },
        "📚 Читальный / компьютерный зал": {
            "where": "Корпус 3, 3 этаж",
            "steps": (
                "1️⃣ Идёшь в 3-й корпус.\n"
                "2️⃣ Поднимаешься на 3 этаж.\n"
                "3️⃣ Находишь читальный зал."
            ),
        },
        "🍽 Столовая": {
            "where": "Уточни у куратора",
            "steps": "📍 Уточняй у куратора или на стенде у входа.",
        },
        "🚻 Туалеты": {
            "where": "На каждом этаже",
            "steps": "📍 На каждом этаже, обычно в конце коридора.",
        },
    }
    _save(PLACES_FILE, PLACES)


# ============================================================
# 🎛 СОСТОЯНИЯ
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

def main_menu(user_id: int = 0):
    keyboard = [
        [KeyboardButton(text="🧭 Путеводитель")],
        [KeyboardButton(text="⏰ Звонки")],
        [KeyboardButton(text="📅 Расписание")],
        [KeyboardButton(text="👥 Моя группа")],
        [KeyboardButton(text="📢 Объявления")],
        [KeyboardButton(text="📋 Чек-лист"), KeyboardButton(text="📖 Словарь")],
        [KeyboardButton(text="🆘 SOS"), KeyboardButton(text="🏛 О РУК")],
        [KeyboardButton(text="📞 Контакты"), KeyboardButton(text="🔗 Ссылки")],
    ]
    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton(text="👨‍💼 Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def back_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ В главное меню")]],
        resize_keyboard=True,
    )


def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Группы"), KeyboardButton(text="📅 Расписание")],
            [KeyboardButton(text="⏰ Звонки"), KeyboardButton(text="📢 Объявления")],
            [KeyboardButton(text="📍 Карта мест")],
            [KeyboardButton(text="⬅️ В главное меню")],
        ],
        resize_keyboard=True,
    )


def admin_groups_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить группу")],
            [KeyboardButton(text="🗑 Удалить группу")],
            [KeyboardButton(text="📋 Список групп")],
            [KeyboardButton(text="⬅️ Назад в админку")],
        ],
        resize_keyboard=True,
    )


def admin_schedule_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить пары")],
            [KeyboardButton(text="🗑 Удалить день")],
            [KeyboardButton(text="⬅️ Назад в админку")],
        ],
        resize_keyboard=True,
    )


def admin_ann_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Новое объявление")],
            [KeyboardButton(text="🗑 Удалить объявление")],
            [KeyboardButton(text="🧹 Очистить объявления")],
            [KeyboardButton(text="⬅️ Назад в админку")],
        ],
        resize_keyboard=True,
    )


def admin_places_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить место")],
            [KeyboardButton(text="🗑 Удалить место")],
            [KeyboardButton(text="📋 Список мест")],
            [KeyboardButton(text="⬅️ Назад в админку")],
        ],
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
# 🚀 /start
# ============================================================

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    USERS.add(message.from_user.id)
    save_users()

    await message.answer(
        f"👋 Привет, *{message.from_user.first_name}*!\n\n"
        "Я — *Путеводитель РУК* 🧭\n\n"
        "🧭 Путеводитель\n⏰ Звонки\n📅 Расписание\n"
        "👥 Моя группа\n📢 Объявления\n📋 Чек-лист\n"
        "📖 Словарь\n🆘 SOS\n🏛 О РУК\n📞 Контакты\n🔗 Ссылки",
        reply_markup=main_menu(message.from_user.id),
        parse_mode="Markdown",
    )


@dp.message(Command("menu"))
@dp.message(F.text == "⬅️ В главное меню")
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    await send_typing(message, "🏠 *Главное меню*",
                      parse_mode="Markdown",
                      reply_markup=main_menu(message.from_user.id))


# ============================================================
# 👨‍💼 АДМИН-ПАНЕЛЬ
# ============================================================

@dp.message(Command("admin"))
@dp.message(F.text == "👨‍💼 Админ-панель")
async def admin_panel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для админа.")
        return
    await state.clear()
    await message.answer(
        "👨‍💼 *Админ-панель*\n\nВыбирай раздел 👇",
        parse_mode="Markdown",
        reply_markup=admin_menu(),
    )


@dp.message(F.text == "⬅️ Назад в админку")
async def back_to_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("👨‍💼 *Админ-панель*",
                         parse_mode="Markdown",
                         reply_markup=admin_menu())


@dp.message(F.text == "👥 Группы")
async def admin_groups(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("👥 *Управление группами*",
                         parse_mode="Markdown",
                         reply_markup=admin_groups_menu())


@dp.message(F.text == "📅 Расписание")
async def admin_schedule(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("📅 *Управление расписанием*",
                         parse_mode="Markdown",
                         reply_markup=admin_schedule_menu())


@dp.message(F.text == "⏰ Звонки")
async def admin_bells(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "⏰ *Звонки*\n\nОтправь список командой `/set_bells`",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="⬅️ Назад в админку")]],
            resize_keyboard=True,
        ),
    )


@dp.message(F.text == "📢 Объявления")
async def admin_ann(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("📢 *Управление объявлениями*",
                         parse_mode="Markdown",
                         reply_markup=admin_ann_menu())


@dp.message(F.text == "📍 Карта мест")
async def admin_places(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("📍 *Управление картой*",
                         parse_mode="Markdown",
                         reply_markup=admin_places_menu())


# ============ КНОПКИ-ДЕЙСТВИЯ ============

@dp.message(F.text == "➕ Добавить группу")
async def btn_add_group(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(GroupStates.waiting_name)
    await message.answer("👥 Введи название группы (например, `ИС-11`):",
                         parse_mode="Markdown")


@dp.message(F.text == "🗑 Удалить группу")
async def btn_del_group(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not GROUPS:
        await message.answer("Групп нет.")
        return
    await state.set_state(DelGroupStates.waiting_name)
    lst = ", ".join(f"`{g}`" for g in GROUPS)
    await message.answer(f"Введи группу для удаления:\n{lst}",
                         parse_mode="Markdown")


@dp.message(F.text == "📋 Список групп")
async def btn_list_groups(message: Message):
    if not is_admin(message.from_user.id):
        return
    if not GROUPS:
        await message.answer("Групп нет.", reply_markup=admin_menu())
        return
    text = "👥 *Группы:*\n\n"
    for g in GROUPS:
        days = ", ".join(SCHEDULE.get(g, {}).keys()) or "—"
        text += f"📚 *{g}* — дни: {days}\n"
    await message.answer(text, parse_mode="Markdown", reply_markup=admin_menu())


@dp.message(F.text == "➕ Добавить пары")
async def btn_add_pairs(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(ScheduleStates.waiting_group)
    await message.answer("📅 Шаг 1/3 — введи *название группы*:",
                         parse_mode="Markdown")


@dp.message(F.text == "🗑 Удалить день")
async def btn_del_day(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not SCHEDULE:
        await message.answer("Расписание пусто.")
        return
    await state.set_state(DelDayStates.waiting_group)
    groups = ", ".join(f"`{g}`" for g in SCHEDULE)
    await message.answer(f"Введи группу:\n{groups}", parse_mode="Markdown")


@dp.message(F.text == "➕ Новое объявление")
async def btn_new_ann(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AnnounceStates.waiting_text)
    await message.answer("📢 Напиши текст объявления:")


@dp.message(F.text == "🗑 Удалить объявление")
async def btn_del_ann(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not ANNOUNCES:
        await message.answer("Объявлений нет.")
        return
    text = "📢 *Объявления:*\n\n"
    for i, a in enumerate(ANNOUNCES, 1):
        text += f"*{i}.* {a['text'][:60]}...\n"
    text += "\nВведи *номер*:"
    await state.set_state(DelAnnounceStates.waiting_number)
    await message.answer(text, parse_mode="Markdown")


@dp.message(F.text == "🧹 Очистить объявления")
async def btn_clear_ann(message: Message):
    if not is_admin(message.from_user.id):
        return
    global ANNOUNCES
    ANNOUNCES = []
    _save(ANNOUNCES_FILE, ANNOUNCES)
    msg = await message.answer("✅ Очищено", reply_markup=admin_menu())
    await auto_delete(msg, 5)


@dp.message(F.text == "➕ Добавить место")
async def btn_add_place(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(PlaceStates.waiting_name)
    await message.answer("📍 Шаг 1/3 — введи *название* (например, `📚 Библиотека`):",
                         parse_mode="Markdown")


@dp.message(F.text == "🗑 Удалить место")
async def btn_del_place(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not PLACES:
        await message.answer("Карта пуста.")
        return
    await state.set_state(DelPlaceStates.waiting_name)
    lst = "\n".join(f"• `{n}`" for n in PLACES)
    await message.answer(f"Введи название:\n\n{lst}", parse_mode="Markdown")


@dp.message(F.text == "📋 Список мест")
async def btn_list_places(message: Message):
    if not is_admin(message.from_user.id):
        return
    if not PLACES:
        await message.answer("Карта пуста.", reply_markup=admin_menu())
        return
    text = "📍 *Места на карте:*\n\n"
    for name, p in PLACES.items():
        text += f"• *{name}* — {p['where']}\n"
    await message.answer(text, parse_mode="Markdown", reply_markup=admin_menu())


# ============================================================
# 💾 ОБРАБОТЧИКИ СОСТОЯНИЙ
# ============================================================

@dp.message(GroupStates.waiting_name)
async def add_group_finish(message: Message, state: FSMContext):
    name = message.text.strip()
    if name in GROUPS:
        await message.answer("⚠️ Такая группа уже есть.")
        return
    GROUPS.append(name)
    _save(GROUPS_FILE, GROUPS)
    await state.clear()
    msg = await message.answer(f"✅ Группа *{name}* добавлена",
                               parse_mode="Markdown", reply_markup=admin_menu())
    await auto_delete(msg, 5)


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
                                   parse_mode="Markdown", reply_markup=admin_menu())
        await auto_delete(msg, 5)
    else:
        await message.answer("❌ Группа не найдена.")


@dp.message(ScheduleStates.waiting_group)
async def set_sched_group(message: Message, state: FSMContext):
    grp = message.text.strip()
    if grp not in GROUPS:
        GROUPS.append(grp)
        _save(GROUPS_FILE, GROUPS)
    await state.update_data(group=grp)
    await state.set_state(ScheduleStates.waiting_day)
    await message.answer("📅 Шаг 2/3 — введи *день* (`Пн`, `Вт`, `Ср`, `Чт`, `Пт`, `Сб`):",
                         parse_mode="Markdown")


@dp.message(ScheduleStates.waiting_day)
async def set_sched_day(message: Message, state: FSMContext):
    await state.update_data(day=message.text.strip())
    await state.set_state(ScheduleStates.waiting_pairs)
    await message.answer("📅 Шаг 3/3 — введи пары через запятую:\n\n"
                         "`Математика 201, Русский 305, Физкультура`",
                         parse_mode="Markdown")


@dp.message(ScheduleStates.waiting_pairs)
async def set_sched_pairs(message: Message, state: FSMContext):
    data = await state.get_data()
    grp, day = data["group"], data["day"]
    pairs = [p.strip() for p in message.text.split(",") if p.strip()]
    SCHEDULE.setdefault(grp, {})[day] = pairs
    _save(SCHEDULE_FILE, SCHEDULE)
    await state.clear()
    msg = await message.answer(
        f"✅ Расписание для *{grp}* ({day}) сохранено!\nПар: {len(pairs)}",
        parse_mode="Markdown", reply_markup=admin_menu())
    await auto_delete(msg, 5)


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
                                   reply_markup=admin_menu())
        await auto_delete(msg, 5)
    else:
        await message.answer("❌ День не найден.")


@dp.message(Command("set_bells"))
async def set_bells_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для админа.")
        return
    await state.set_state(BellsStates.waiting_data)
    await message.answer(
        "⏰ Отправь список — каждая строка:\n"
        "`название, начало, конец, перемена`\n\n"
        "Пример:\n"
        "`1 пара, 09:00, 10:30, 10 мин`",
        parse_mode="Markdown")


@dp.message(BellsStates.waiting_data)
async def set_bells_data(message: Message, state: FSMContext):
    global BELLS
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
                                   reply_markup=admin_menu())
        await auto_delete(msg, 5)
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}", parse_mode="Markdown")


@dp.message(AnnounceStates.waiting_text)
async def announce_send(message: Message, state: FSMContext):
    text = message.text.strip()
    date = datetime.now().strftime("%d.%m.%Y %H:%M")
    ANNOUNCES.append({"text": text, "date": date})
    _save(ANNOUNCES_FILE, ANNOUNCES)
    await state.clear()

    sent = 0
    for uid in list(USERS):
        try:
            await bot.send_message(uid,
                f"📢 *Новое объявление!*\n\n{text}\n\n🕐 _{date}_",
                parse_mode="Markdown")
            sent += 1
        except Exception:
            pass

    await message.answer(f"✅ Отправлено: {sent} из {len(USERS)}",
                         reply_markup=admin_menu())


@dp.message(DelAnnounceStates.waiting_number)
async def del_ann_finish(message: Message, state: FSMContext):
    try:
        idx = int(message.text.strip()) - 1
        if 0 <= idx < len(ANNOUNCES):
            del ANNOUNCES[idx]
            _save(ANNOUNCES_FILE, ANNOUNCES)
            await state.clear()
            msg = await message.answer("✅ Удалено", reply_markup=admin_menu())
            await auto_delete(msg, 5)
        else:
            await message.answer("❌ Неверный номер.")
    except ValueError:
        await message.answer("❌ Введи число.")


@dp.message(PlaceStates.waiting_name)
async def add_place_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(PlaceStates.waiting_where)
    await message.answer("📍 Шаг 2/3 — *где находится* (например, `Корпус 3, 3 этаж`):",
                         parse_mode="Markdown")


@dp.message(PlaceStates.waiting_where)
async def add_place_where(message: Message, state: FSMContext):
    await state.update_data(where=message.text.strip())
    await state.set_state(PlaceStates.waiting_steps)
    await message.answer("📍 Шаг 3/3 — *маршрут по шагам* (каждый с новой строки):",
                         parse_mode="Markdown")


@dp.message(PlaceStates.waiting_steps)
async def add_place_steps(message: Message, state: FSMContext):
    data = await state.get_data()
    PLACES[data["name"]] = {"where": data["where"], "steps": message.text.strip()}
    _save(PLACES_FILE, PLACES)
    await state.clear()
    msg = await message.answer(f"✅ Место *{data['name']}* добавлено!",
                               parse_mode="Markdown", reply_markup=admin_menu())
    await auto_delete(msg, 5)


@dp.message(DelPlaceStates.waiting_name)
async def del_place_finish(message: Message, state: FSMContext):
    name = message.text.strip()
    if name in PLACES:
        del PLACES[name]
        _save(PLACES_FILE, PLACES)
        await state.clear()
        msg = await message.answer(f"✅ Удалено: *{name}*",
                                   parse_mode="Markdown", reply_markup=admin_menu())
        await auto_delete(msg, 5)
    else:
        await message.answer("❌ Не найдено.")


# ============================================================
# 🧭 ПУТЕВОДИТЕЛЬ
# ============================================================

@dp.message(F.text == "🧭 Путеводитель")
async def navigator(message: Message):
    if not PLACES:
        await message.answer("🧭 Карта пуста.", reply_markup=back_menu())
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"nav:{name}")]
        for name in PLACES
    ])
    await send_typing(message, "🧭 *Куда хочешь дойти?*",
                      parse_mode="Markdown", reply_markup=kb)


@dp.callback_query(F.data.startswith("nav:"))
async def show_route(callback: CallbackQuery):
    name = callback.data.split(":", 1)[1]
    place = PLACES.get(name)
    if not place:
        await callback.answer("Не найдено", show_alert=True)
        return
    text = (f"*{name}*\n\n📍 *Где:* {place['where']}\n\n"
            f"🗺 *Как дойти:*\n\n{place['steps']}")
    await callback.message.answer(text, parse_mode="Markdown",
                                  reply_markup=back_menu())
    await callback.answer()


# ============================================================
# 👥 МОЯ ГРУППА
# ============================================================

@dp.message(F.text == "👥 Моя группа")
async def my_group(message: Message):
    if not GROUPS:
        await message.answer("👥 Групп пока нет.", reply_markup=back_menu())
        return
    uid = str(message.from_user.id)
    current = USER_GROUPS.get(uid)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{'✅ ' if g == current else ''}📚 {g}",
            callback_data=f"mygrp:{g}")]
        for g in GROUPS
    ])
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
    await callback.message.answer(f"✅ Группа *{grp}* выбрана",
                                  parse_mode="Markdown", reply_markup=back_menu())
    await callback.answer()


# ============================================================
# ⏰ ЗВОНКИ
# ============================================================

@dp.message(F.text == "⏰ Звонки")
async def bells_cmd(message: Message):
    if not BELLS:
        await message.answer("⏰ Звонков нет.", reply_markup=back_menu())
        return
    text = "⏰ *Звонки*\n\n"
    for b in BELLS:
        text += f"🔔 *{b['name']}*  {b['start']} — {b['end']}  (⏸ {b['break']})\n"
    await send_typing(message, text, parse_mode="Markdown", reply_markup=back_menu())


# ============================================================
# 📅 РАСПИСАНИЕ
# ============================================================

@dp.message(F.text == "📅 Расписание")
async def schedule_cmd(message: Message):
    if not SCHEDULE:
        await message.answer("📅 Расписание пусто.", reply_markup=back_menu())
        return
    uid = str(message.from_user.id)
    my_grp = USER_GROUPS.get(uid)

    if my_grp and my_grp in SCHEDULE:
        days = SCHEDULE[my_grp]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"📆 {day}",
                                  callback_data=f"sched_day:{my_grp}:{day}")]
            for day in days
        ] + [[InlineKeyboardButton(text="🔄 Другая группа",
                                   callback_data="sched_all")]])
        await send_typing(message, f"📅 *{my_grp}*\n\nВыбери день 👇",
                          parse_mode="Markdown", reply_markup=kb)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📚 {grp}",
                              callback_data=f"sched_grp:{grp}")]
        for grp in SCHEDULE
    ])
    await send_typing(message, "📅 *Выбери группу:*",
                      parse_mode="Markdown", reply_markup=kb)


@dp.callback_query(F.data == "sched_all")
async def sched_all(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📚 {grp}",
                              callback_data=f"sched_grp:{grp}")]
        for grp in SCHEDULE
    ])
    await callback.message.answer("📅 *Выбери группу:*",
                                  parse_mode="Markdown", reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("sched_grp:"))
async def show_group_days(callback: CallbackQuery):
    grp = callback.data.split(":", 1)[1]
    days = SCHEDULE.get(grp, {})
    if not days:
        await callback.answer("Пусто", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📆 {day}",
                              callback_data=f"sched_day:{grp}:{day}")]
        for day in days
    ])
    await callback.message.answer(f"📚 *{grp}*\n\nВыбери день 👇",
                                  parse_mode="Markdown", reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("sched_day:"))
async def show_day(callback: CallbackQuery):
    _, grp, day = callback.data.split(":", 2)
    pairs = SCHEDULE.get(grp, {}).get(day, [])
    if not pairs:
        await callback.message.answer(f"📅 *{grp}, {day}*\n\n🎉 Пар нет!",
                                      parse_mode="Markdown", reply_markup=back_menu())
        await callback.answer()
        return
    text = f"📅 *{grp}, {day}*\n\n"
    for i, pair in enumerate(pairs, 1):
        text += f"*{i}.* {pair}\n"
    await callback.message.answer(text, parse_mode="Markdown",
                                  reply_markup=back_menu())
    await callback.answer()


# ============================================================
# 📢 ОБЪЯВЛЕНИЯ
# ============================================================

@dp.message(F.text == "📢 Объявления")
async def announces_cmd(message: Message):
    if not ANNOUNCES:
        await message.answer("📢 Объявлений нет.", reply_markup=back_menu())
        return
    text = "📢 *Объявления*\n\n"
    for i, a in enumerate(ANNOUNCES, 1):
        text += f"*{i}.* {a['text']}\n🕐 _{a['date']}_\n\n"
    await send_typing(message, text, parse_mode="Markdown", reply_markup=back_menu())


# ============================================================
# 📋 ЧЕК-ЛИСТ
# ============================================================

CHECKLIST_ITEMS = [
    "Познакомиться с куратором",
    "Записать номер куратора",
    "Узнать, где деканат (каб. 304)",
    "Найти свою группу в расписании",
    "Выбрать свою группу в боте",
    "Найти библиотеку",
    "Узнать, где столовая",
    "Оформить студенческий",
    "Получить логин/пароль от ЛК",
    "Взять справку об обучении",
    "Найти медкабинет",
    "Познакомиться с группой",
]


def checklist_text(done):
    text = "📋 *Чек-лист*\n\n"
    for i, item in enumerate(CHECKLIST_ITEMS, 1):
        mark = "✅" if i in done else "⬜"
        text += f"{mark} {i}. {item}\n"
    text += f"\nВыполнено: *{len(done)}/{len(CHECKLIST_ITEMS)}*"
    return text


def checklist_kb(done):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{'✅' if i in done else '⬜'} {i}",
                              callback_data=f"chk:{i}")]
        for i in range(1, len(CHECKLIST_ITEMS) + 1)
    ])


@dp.message(F.text == "📋 Чек-лист")
async def checklist_cmd(message: Message):
    uid = str(message.from_user.id)
    done = CHECKLISTS.get(uid, [])
    await send_typing(message, checklist_text(done),
                      parse_mode="Markdown", reply_markup=checklist_kb(done))


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
    "Академ": "Академический отпуск.",
    "Куратор": "Преподаватель, закреплённый за группой.",
    "Деканат": "Административный отдел по вопросам учёбы.",
    "Ведомость": "Список студентов с оценками.",
    "Отработка": "Занятие за пропуск.",
    "Зачёт": "Форма проверки знаний без оценки.",
    "Стипендия": "Выплата за хорошую учёбу.",
    "ЛК": "Личный кабинет студента.",
}


@dp.message(F.text == "📖 Словарь")
async def dict_cmd(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=word, callback_data=f"dict:{word}")]
        for word in DICTIONARY
    ])
    await send_typing(message, "📖 *Словарь студента*",
                      parse_mode="Markdown", reply_markup=kb)


@dp.callback_query(F.data.startswith("dict:"))
async def show_dict(callback: CallbackQuery):
    word = callback.data.split(":", 1)[1]
    meaning = DICTIONARY.get(word)
    if not meaning:
        await callback.answer("Не найдено", show_alert=True)
        return
    await callback.message.answer(f"📖 *{word}*\n\n💡 {meaning}",
                                  parse_mode="Markdown", reply_markup=back_menu())
    await callback.answer()


# ============================================================
# 🆘 SOS
# ============================================================

SOS = {
    "Потерял студенческий": "🆘 *Потерял студенческий*\n\n1️⃣ Сообщи в деканат (каб. 304).\n2️⃣ Напиши заявление.\n3️⃣ Получи новый билет.",
    "Заболел и пропустил пары": "🆘 *Заболел*\n\n1️⃣ Возьми справку у врача.\n2️⃣ Отдай в деканат.\n3️⃣ Уточни у куратора.",
    "Не нашёл кабинет": "🆘 *Не нашёл кабинет*\n\n1️⃣ Спроси у охраны.\n2️⃣ Найди стенд с расписанием.\n3️⃣ Используй «🧭 Путеводитель».",
    "Не сдал зачёт": "🆘 *Не сдал зачёт*\n\n1️⃣ Узнай дату пересдачи.\n2️⃣ Подготовься.\n3️⃣ Приди вовремя.",
}


@dp.message(F.text == "🆘 SOS")
async def sos_cmd(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=q, callback_data=f"sos:{q}")]
        for q in SOS
    ])
    await send_typing(message, "🆘 *Что делать, если…*",
                      parse_mode="Markdown", reply_markup=kb)


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
# 🏛 О РУК / КОНТАКТЫ / ССЫЛКИ
# ============================================================

@dp.message(F.text == "🏛 О РУК")
async def about_ruk(message: Message):
    info = RUK_INFO
    await send_typing(
        message,
        f"🏛 *{info['name']}*\n\n"
        f"📅 *Основан:* {info['founded']}\n"
        f"🏛 *Учредитель:* {info['founder']}\n\n"
        f"📍 {info['address']}\n"
        f"📞 {info['phone']}\n"
        f"📞 {info['phone2']}\n"
        f"✉️ {info['email']}\n"
        f"🌐 {info['site']}\n"
        f"🕐 {info['work_time']}",
        parse_mode="Markdown", reply_markup=back_menu())


@dp.message(F.text == "📞 Контакты")
async def contacts(message: Message):
    info = RUK_INFO
    await send_typing(
        message,
        f"📞 *Контакты РУК*\n\n📍 {info['address']}\n"
        f"☎️ {info['phone']}\n☎️ {info['phone2']}\n"
        f"✉️ {info['email']}\n🌐 {info['site']}\n\n🕐 {info['work_time']}",
        parse_mode="Markdown", reply_markup=back_menu())


@dp.message(F.text == "🔗 Ссылки")
async def links_cmd(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Сайт РУК", url="https://ruc.su")],
        [InlineKeyboardButton(text="👤 Личный кабинет", url="https://lk.ruc.su")],
    ])
    await send_typing(message, "🔗 *Ссылки:*",
                      parse_mode="Markdown", reply_markup=kb)
    await message.answer("👆 Выбери раздел", reply_markup=back_menu())


# ============================================================
# 🤔 FALLBACK
# ============================================================

@dp.message()
async def fallback(message: Message):
    await message.answer(
        "🤔 Я тебя не понял. Воспользуйся кнопками меню.",
        reply_markup=main_menu(message.from_user.id),
    )


# ============================================================
# ▶️ ЗАПУСК + УСТАНОВКА КОМАНД (для кнопки «Меню»)
# ============================================================

async def main():
    # Регистрируем команды — они появятся в синей кнопке «Меню»
    commands = [
        BotCommand(command="start", description="🚀 Запустить"),
        BotCommand(command="menu", description="🏠 Меню"),
        BotCommand(command="admin", description="👨‍💼 Админ-панель"),
        BotCommand(command="bells", description="⏰ Звонки"),
        BotCommand(command="schedule", description="📅 Расписание"),
        BotCommand(command="announces", description="📢 Объявления"),
        BotCommand(command="set_bells", description="🔧 Задать звонки"),
        BotCommand(command="add_group", description="➕ Добавить группу"),
        BotCommand(command="set_schedule", description="📅 Добавить расписание"),
        BotCommand(command="announce", description="📢 Создать объявление"),
        BotCommand(command="add_place", description="📍 Добавить место"),
        BotCommand(command="help", description="❓ Помощь"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())

    print("🧭 Бот «Путеводитель РУК» запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен")
