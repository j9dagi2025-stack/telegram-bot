import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import qrcode
from io import BytesIO

from config import TOKEN, ADMIN_ID
from db import add_user, set_setting, get_setting, get_all_users

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

admin_wait = {}
offer_price = {}
pending_screenshot = {}


# =========================
# STORE
# =========================
def get_store():
    old = get_setting("premium", "")
    if old:
        set_setting("premium_link", old)
    return {
        "upi": get_setting("upi", ""),
        "demo": get_setting("demo", ""),
         "price": int(get_setting("price", "0")),
        "name": get_setting("name", ""),
        "premium_link": get_setting("premium_link", ""),
        "start_text": get_setting("start_text", ""),
        "photo": get_setting("photo", None),
        "sales": int(get_setting("sales", "0")),
        "revenue": int(get_setting("revenue", "0")),
    }


# =========================
# PAYMENT TEXT
# =========================
def payment_text(store, price):
    return f"""

â¡ ððððððð ððððððð

ð ððððð¬ð¬: {store['name'] or "Not Set"}
ðµ ðð¦ð¨ð®ð§ð­: â¹{price}
ð¦ ððð ðð: <code>{store['upi'] or "Not Set"}</code>

1ï¸â£ ðððð§ ðð ðð¨ðð
2ï¸â£ ððð² ð®ð¬ð¢ð§ð  ððð
3ï¸â£ ðð¥ð¢ðð¤ ðð®ð­ð­ð¨ð§ ððð¥ð¨ð°

ð¸ Send screenshot after payment
"""


# =========================
# START
# =========================
@bot.message_handler(commands=["start"])
def start(message):
    store = get_store()
    add_user(message.chat.id)

    custom = store["start_text"]

    if custom:
        text = custom
    else:
        text = "Welcome!"

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("ð³ BUY PREMIUM", callback_data="buy"))
    kb.add(InlineKeyboardButton("ð¬ DEMO", url=store["demo"]))

    photo = store.get("photo")

    if photo:
        try:
            bot.send_photo(message.chat.id, photo, caption=text, reply_markup=kb)
        except:
            bot.send_message(message.chat.id, text, reply_markup=kb)
    else:
        bot.send_message(message.chat.id, text, reply_markup=kb)


# =========================
# ADMIN PANEL
# =========================
@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if int(message.chat.id) != int(ADMIN_ID):
        return

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("â SET NAME", callback_data="set_name"))
    kb.add(InlineKeyboardButton("ð° SET PRICE", callback_data="set_price"))
    kb.add(InlineKeyboardButton("ð¦ SET UPI", callback_data="set_upi"))
    kb.add(InlineKeyboardButton("ð¬ SET DEMO", callback_data="set_demo"))
    kb.add(InlineKeyboardButton("ð SET PREMIUM LINK", callback_data="set_premium"))
    kb.add(InlineKeyboardButton("ð¼ SET PHOTO", callback_data="set_photo"))
    kb.add(InlineKeyboardButton("â SET START TEXT", callback_data="set_start_text"))
    kb.add(InlineKeyboardButton("ð¥ USERS", callback_data="users"))
    kb.add(InlineKeyboardButton("ð STATS", callback_data="stats"))

    bot.send_message(message.chat.id, "ð *ADMIN PANEL*", reply_markup=kb)


# =========================
# ADMIN SET
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def admin_set(c):
    if int(c.from_user.id) != int(ADMIN_ID):
        return

    admin_wait[c.from_user.id] = c.data.replace("set_", "")
    bot.send_message(c.message.chat.id, "â Send value now:")


# =========================
# MESSAGE HANDLER (ADMIN + SCREENSHOT)
# =========================
@bot.message_handler(content_types=['text', 'photo'])
def handle_all(m):

    user_id = m.from_user.id

    # ================= ADMIN UPDATE =================
    if user_id in admin_wait:
        action = admin_wait[user_id]

        if action == "photo":
            if m.photo:
                set_setting("photo", m.photo[-1].file_id)
                bot.send_message(m.chat.id, "ð¼ PHOTO UPDATED")
            admin_wait.pop(user_id, None)
            return

        if m.text:
            set_setting(action, m.text)
            bot.send_message(m.chat.id, "â UPDATED")

        admin_wait.pop(user_id, None)
        return

    # ================= SCREENSHOT FLOW =================
    if pending_screenshot.get(user_id):

        if not m.photo:
            bot.send_message(m.chat.id, "ð¸ Please send a valid screenshot image.")
            return

        pending_screenshot.pop(user_id, None)
        store = get_store()

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("â APPROVE", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton("â REJECT", callback_data=f"reject_{user_id}")
        )

        bot.send_photo(
            ADMIN_ID,
            m.photo[-1].file_id,
            caption=f"ð° PAYMENT PROOF\nUser: {user_id}",
            reply_markup=kb
        )

        bot.send_message(
            m.chat.id,
            "â Screenshot received!\nâ³ Verification in progress...\nð Access will be sent soon."
        )


# =========================
# BUY
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "buy")
def buy(c):
    store = get_store()

    price = offer_price.get(c.from_user.id, store["price"])

    # QR
    qr_link = f"upi://pay?pa={store['upi']}&am={price}&cu=INR"

    qr = qrcode.QRCode()
    qr.add_data(qr_link)
    qr.make(fit=True)

    img = qr.make_image(fill="black", back_color="white")

    bio = BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)

    # PAY URL
    pay_url = f"https://j9dagi2025-stack.github.io/index.html//?am={29}"

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("ð PAY NOW", url=pay_url))
    kb.add(InlineKeyboardButton("ð³ I HAVE PAID", callback_data="paid"))
    kb.add(InlineKeyboardButton("â CANCEL ORDER", callback_data="cancel"))

    bot.send_photo(
        c.message.chat.id,
        bio,
        caption=payment_text(store, price),
        reply_markup=kb
    )


# =========================
# PAID BUTTON
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "paid")
def paid(c):
    pending_screenshot[c.from_user.id] = True

    bot.send_message(
        c.message.chat.id,
        "ð¸ Please send your <b>payment screenshot</b> here."
    )


# =========================
# CANCEL
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "cancel")
def cancel(c):
    store = get_store()

    old_price = int(store["price"])
    new_price = max(1, old_price - 2)

    offer_price[c.from_user.id] = new_price

    qr_link = f"upi://pay?pa={store['upi']}&am={new_price}&cu=INR"

    qr = qrcode.QRCode()
    qr.add_data(qr_link)
    qr.make(fit=True)

    img = qr.make_image(fill="black", back_color="white")

    bio = BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)

    # ð¥ PRO HIGH-CONVERTING TEXT
    text = f"""
    â <b>ORDER CANCELLED</b>

    ð Miss ho gaya...

    ð¥ <b>EXCLUSIVE DEAL UNLOCKED</b>

     âââââââââââââââ
    ð° <s>â¹{old_price}</s> â
    ð <b>Now Only:</b> â¹{new_price} â
     âââââââââââââââ

    â³ <b>Only few users can grab this deal</b>
    â¡ <b>Instant Access</b>
    ð <b>Private Premium Content</b>

    ð¨ <b>Hurry! Offer may expire anytime</b>

    ð <b>Tap below to grab now</b>
"""

    # ð¥ PRO BUTTON
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("ð¥ LIMITED OFFER - GRAB NOW", callback_data="buy"))

    bot.send_photo(c.message.chat.id, bio, caption=text, reply_markup=kb)


# =========================
# APPROVE / REJECT (FIXED)
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("approve_"))
def approve(c):
    user_id = int(c.data.split("_")[1])
    store = get_store()

    # ð YE LINE ADD KAR
    print("PREMIUM LINK:", store["premium_link"])

    set_setting("sales", str(int(store["sales"]) + 1))
    set_setting("revenue", str(int(store["revenue"]) + int(store["price"])))

    offer_price.pop(user_id, None)

    caption = c.message.caption or ""

    bot.edit_message_caption(
    chat_id=c.message.chat.id,
    message_id=c.message.message_id,
    caption=caption + "\n\nâ APPROVED & LINK SENT",
    reply_markup=None
)
    
    try:
        bot.send_message(
            user_id,
            f"""ð <b>APPROVED!</b>

ð¥ <b>Access Granted Successfully</b>

ð <b>Join Here:</b>
{store["premium_link"]}"""
        )
    except Exception as e:
        print("ERROR SENDING LINK:", e)



@bot.callback_query_handler(func=lambda c: c.data.startswith("reject_"))
def reject(c):
    user_id = int(c.data.split("_")[1])

    offer_price.pop(user_id, None)

    caption = c.message.caption or ""

    bot.edit_message_caption(
    chat_id=c.message.chat.id,
    message_id=c.message.message_id,
    caption=caption + "\n\nâ PAYMENT REJECTED",
    reply_markup=None
)
    bot.send_message(user_id, "â Payment rejected")


# =========================
# USERS / STATS
# =========================
@bot.callback_query_handler(func=lambda c: c.data == "users")
def users(c):
    users = get_all_users()
    bot.send_message(c.message.chat.id, f"ð¥ USERS: {len(users)}")


@bot.callback_query_handler(func=lambda c: c.data == "stats")
def stats(c):
    store = get_store()
    bot.send_message(c.message.chat.id, f"ð SALES: {store['sales']}\nð° REVENUE: â¹{store['revenue']}")


print("Bot Running...")
bot.infinity_polling(skip_pending=True)
