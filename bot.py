"""DebtFree_kz_bot — помощник по кредитам и долгам."""
import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

TOKEN = os.environ["BOT_TOKEN"]
dp = Dispatcher(storage=MemoryStorage())


def money(x: float) -> str:
    return f"{round(x):,}".replace(",", " ") + " ₸"


def num(text: str):
    try:
        v = float(text.replace(" ", "").replace(",", ".").replace("₸", ""))
        return v if v > 0 else None
    except ValueError:
        return None


MENU = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💰 Посчитать кредит", callback_data="calc")],
    [InlineKeyboardButton(text="🔎 Проверить займ", callback_data="check")],
    [InlineKeyboardButton(text="📋 Мои долги", callback_data="debts")],
    [InlineKeyboardButton(text="📊 Мой бюджет", callback_data="budget")],
    [InlineKeyboardButton(text="⭐ Подписка", callback_data="sub")],
])
BACK = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")]])

HELLO = ("Салам! Я Помощник 👋\n\nПомогу разобраться с кредитами и долгами: "
         "посчитаю переплату, проверю займ и составлю план, как выбраться.\n\n"
         "Что нужно?")


class Calc(StatesGroup):
    amount = State(); months = State(); payment = State()


class Check(StatesGroup):
    where = State(); amount = State(); months = State(); total = State()


class Debts(StatesGroup):
    list = State(); budget = State()


class Budget(StatesGroup):
    income = State(); expenses = State()


@dp.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(HELLO, reply_markup=MENU)


@dp.callback_query(F.data == "menu")
async def menu(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.answer("Что нужно?", reply_markup=MENU)
    await c.answer()


ASK_NUM = "Напиши просто число, например 500000"


# ---------- Посчитать кредит ----------
@dp.callback_query(F.data == "calc")
async def calc0(c: CallbackQuery, state: FSMContext):
    await state.set_state(Calc.amount)
    await c.message.answer("Какую сумму берёшь? (в тенге)")
    await c.answer()


@dp.message(Calc.amount)
async def calc1(m: Message, state: FSMContext):
    v = num(m.text or "")
    if not v:
        return await m.answer(ASK_NUM)
    await state.update_data(amount=v)
    await state.set_state(Calc.months)
    await m.answer("На сколько месяцев?")


@dp.message(Calc.months)
async def calc2(m: Message, state: FSMContext):
    v = num(m.text or "")
    if not v:
        return await m.answer("Напиши число месяцев, например 12")
    await state.update_data(months=v)
    await state.set_state(Calc.payment)
    await m.answer("Какой платёж в месяц?")


@dp.message(Calc.payment)
async def calc3(m: Message, state: FSMContext):
    v = num(m.text or "")
    if not v:
        return await m.answer(ASK_NUM)
    d = await state.get_data()
    total = v * d["months"]
    over = total - d["amount"]
    await state.clear()
    if over <= 0:
        text = (f"Ты берёшь {money(d['amount'])} и вернёшь {money(total)}. "
                "Переплаты нет — проверь цифры, это необычно.")
    else:
        pct = over / d["amount"] * 100
        rate = annual_rate(d["amount"], v, int(d["months"]))
        text = (f"Ты берёшь {money(d['amount'])}, а вернёшь {money(total)}.\n\n"
                f"Переплата — {money(over)}, это {pct:.0f}% сверху.\n"
                f"Реальная ставка — около {rate:.0f}% годовых.")
    await m.answer(text, reply_markup=BACK)


def annual_rate(amount: float, payment: float, months: int) -> float:
    """Годовая ставка по равным платежам (метод деления пополам)."""
    if payment * months <= amount:
        return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(100):
        r = (lo + hi) / 2
        pv = payment * (1 - (1 + r) ** -months) / r
        if pv > amount:
            lo = r
        else:
            hi = r
    return ((1 + r) ** 12 - 1) * 100


# ---------- Проверить займ ----------
WHERE = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Банк", callback_data="w_bank"),
     InlineKeyboardButton(text="МФО", callback_data="w_mfo")],
    [InlineKeyboardButton(text="Ломбард", callback_data="w_lomb"),
     InlineKeyboardButton(text="Частник", callback_data="w_priv")],
])


@dp.callback_query(F.data == "check")
async def check0(c: CallbackQuery, state: FSMContext):
    await state.set_state(Check.where)
    await c.message.answer("Где берёшь займ?", reply_markup=WHERE)
    await c.answer()


@dp.callback_query(Check.where, F.data.startswith("w_"))
async def check1(c: CallbackQuery, state: FSMContext):
    await state.update_data(where=c.data)
    await state.set_state(Check.amount)
    await c.message.answer("Какую сумму берёшь?")
    await c.answer()


@dp.message(Check.amount)
async def check2(m: Message, state: FSMContext):
    v = num(m.text or "")
    if not v:
        return await m.answer(ASK_NUM)
    await state.update_data(amount=v)
    await state.set_state(Check.months)
    await m.answer("На сколько месяцев?")


@dp.message(Check.months)
async def check3(m: Message, state: FSMContext):
    v = num(m.text or "")
    if not v:
        return await m.answer("Напиши число месяцев, например 6")
    await state.update_data(months=v)
    await state.set_state(Check.total)
    await m.answer("Сколько всего нужно вернуть?")


@dp.message(Check.total)
async def check4(m: Message, state: FSMContext):
    v = num(m.text or "")
    if not v:
        return await m.answer(ASK_NUM)
    d = await state.get_data()
    await state.clear()
    months = int(d["months"])
    rate = annual_rate(d["amount"], v / months, months)
    over = v - d["amount"]
    if rate < 25:
        verdict = "✅ Нормально. Ставка обычная для Казахстана."
    elif rate < 56:
        verdict = "⚠️ Дорого. Поищи предложение дешевле или рассрочку."
    else:
        verdict = "⛔ Опасно — не бери. Ставка грабительская, легко попасть в долговую яму."
    extra = ""
    if d["where"] == "w_priv":
        extra = "\n\nЗайм у частника — без договора ты не защищён законом."
    await m.answer(f"Переплата — {money(over)}.\nРеальная ставка — около "
                   f"{rate:.0f}% годовых.\n\n{verdict}{extra}", reply_markup=BACK)


# ---------- Мои долги ----------
@dp.callback_query(F.data == "debts")
async def debts0(c: CallbackQuery, state: FSMContext):
    await state.set_state(Debts.list)
    await c.message.answer(
        "Напиши все кредиты, каждый с новой строки, тремя числами:\n"
        "остаток  платёж в месяц  ставка %\n\n"
        "Например:\n500000 30000 35\n200000 15000 56")
    await c.answer()


@dp.message(Debts.list)
async def debts1(m: Message, state: FSMContext):
    loans = []
    for line in (m.text or "").splitlines():
        parts = line.replace(",", ".").split()
        if len(parts) != 3:
            continue
        try:
            bal, pay, rate = map(float, parts)
        except ValueError:
            continue
        loans.append([bal, pay, rate])
    if not loans:
        return await m.answer("Не понял. Каждый кредит — строка из трёх чисел: "
                              "остаток, платёж, ставка. Например: 500000 30000 35")
    await state.update_data(loans=loans)
    await state.set_state(Debts.budget)
    minimum = sum(l[1] for l in loans)
    await m.answer(f"Сейчас обязательные платежи — {money(minimum)} в месяц.\n\n"
                   "Сколько всего можешь отдавать на долги в месяц?")


def simulate(loans, budget):
    loans = [l[:] for l in loans]
    months, interest = 0, 0.0
    while any(l[0] > 0.5 for l in loans) and months < 600:
        months += 1
        for l in loans:
            if l[0] > 0:
                i = l[0] * l[2] / 100 / 12
                l[0] += i
                interest += i
        left = budget
        for l in loans:
            p = min(l[1], l[0])
            l[0] -= p
            left -= p
        for l in sorted(loans, key=lambda x: -x[2]):
            if left <= 0:
                break
            p = min(left, l[0])
            l[0] -= p
            left -= p
    return months, interest


@dp.message(Debts.budget)
async def debts2(m: Message, state: FSMContext):
    v = num(m.text or "")
    if not v:
        return await m.answer(ASK_NUM)
    d = await state.get_data()
    loans = d["loans"]
    minimum = sum(l[1] for l in loans)
    if v < minimum:
        return await m.answer(f"Этого меньше обязательных платежей ({money(minimum)}). "
                              "Напиши сумму не меньше, или обратись к юристу по реструктуризации.")
    await state.clear()
    m1, i1 = simulate(loans, minimum)
    m2, i2 = simulate(loans, v)
    order = sorted(range(len(loans)), key=lambda k: -loans[k][2])
    lines = [f"{n+1}. Кредит {k+1} — ставка {loans[k][2]:.0f}%" for n, k in enumerate(order)]
    text = ("Гаси в таком порядке (самый дорогой — первым):\n" + "\n".join(lines) +
            f"\n\nВсе платят минимум, лишнее идёт на верхний в списке.\n\n"
            f"📅 Станешь свободен через {m2} мес.")
    if m2 < m1:
        text += f"\n💸 Сэкономишь {money(i1 - i2)} и {m1 - m2} мес. по сравнению с минимальными платежами."
    await m.answer(text, reply_markup=BACK)


# ---------- Мой бюджет ----------
@dp.callback_query(F.data == "budget")
async def budget0(c: CallbackQuery, state: FSMContext):
    await state.set_state(Budget.income)
    await c.message.answer("Какой у тебя доход в месяц?")
    await c.answer()


@dp.message(Budget.income)
async def budget1(m: Message, state: FSMContext):
    v = num(m.text or "")
    if not v:
        return await m.answer(ASK_NUM)
    await state.update_data(income=v)
    await state.set_state(Budget.expenses)
    await m.answer("Напиши расходы в месяц пятью числами через пробел:\n"
                   "жильё  еда  транспорт  кредиты  прочее\n\n"
                   "Например: 120000 90000 30000 60000 40000")


NAMES = ["жильё", "еда", "транспорт", "кредиты", "прочее"]


@dp.message(Budget.expenses)
async def budget2(m: Message, state: FSMContext):
    try:
        vals = [float(x) for x in (m.text or "").replace(",", ".").split()]
    except ValueError:
        vals = []
    if len(vals) != 5:
        return await m.answer("Нужно ровно пять чисел через пробел. "
                              "Например: 120000 90000 30000 60000 40000")
    d = await state.get_data()
    await state.clear()
    inc, spent = d["income"], sum(vals)
    rest = inc - spent
    text = f"Доход {money(inc)}, расходы {money(spent)}.\n"
    if rest >= 0:
        text += f"✅ Остаётся {money(rest)}. Откладывай хотя бы {money(inc * 0.1)} в месяц."
    else:
        text += f"⛔ Не хватает {money(-rest)} каждый месяц — так растут долги."
    if vals[3] > inc * 0.4:
        text += "\n\n⚠️ Кредиты съедают больше 40% дохода — это опасно. Загляни в «Мои долги»."
    k = max([0, 1, 2, 4], key=lambda i: vals[i])
    text += f"\n\nБольше всего уходит на «{NAMES[k]}» — начни экономить с этого."
    await m.answer(text, reply_markup=BACK)


# ---------- Подписка ----------
@dp.callback_query(F.data == "sub")
async def sub(c: CallbackQuery):
    await c.message.answer(
        "⭐ Подписка: я веду твой план, напоминаю о платежах и пересчитываю его.\n\n"
        "Период на выбор: день, несколько дней, неделя, 10 дней или месяц "
        "(месяц — 1 500 ₸).\n\nОплата скоро появится.", reply_markup=BACK)
    await c.answer()


@dp.message()
async def fallback(m: Message):
    await m.answer("Выбери, что нужно 👇", reply_markup=MENU)


async def main():
    # Маленькая веб-страница, чтобы бесплатный сервер Render считал бота живым
    from aiohttp import web
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="ok"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000))).start()
    await dp.start_polling(Bot(TOKEN))


if __name__ == "__main__":
    asyncio.run(main())
