import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

admin_state = {}
withdraw_state = {}

def setup_features(bot, users, set_setting, get_setting, ADMIN_ID):

    # =========================
    # USER SAVE + TRACK
    # =========================
    def update_user(user_id, username):
        if not users.find_one({"user_id": user_id}):
            users.insert_one({
                "user_id": user_id,
                "username": username,
                "balance": 0,
                "ref_count": 0,
                "vip": False,
                "last_active": time.time()
            })
        else:
            users.update_one(
                {"user_id": user_id},
                {"$set": {"last_active": time.time()}}
            )

    # =========================
    # MENU BUTTON SYSTEM (NEW)
    # =========================
    def user_menu():
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("💰 Earn Money", "👥 Refer & Earn")
        kb.add("💎 Wallet", "📤 Withdraw")
        kb.add("🏆 Leaderboard")
        return kb

    @bot.message_handler(commands=['menu'])
    def menu(msg):
        update_user(msg.from_user.id, msg.from_user.username)
        bot.send_message(msg.chat.id, "💎 Earning Panel Open", reply_markup=user_menu())

    # =========================
    # WALLET
    # =========================
    @bot.message_handler(commands=['wallet'])
    def wallet(msg):
        user = users.find_one({"user_id": msg.from_user.id})
        balance = user.get("balance", 0)
        refs = user.get("ref_count", 0)

        text = f"""
💰 <b>YOUR WALLET</b>

👥 Referrals: {refs}
💎 Balance: ₹{balance}
"""
        bot.send_message(msg.chat.id, text, parse_mode="HTML")

    # =========================
    # WITHDRAW
    # =========================
    @bot.message_handler(commands=['withdraw'])
    def withdraw(msg):
        withdraw_state[msg.from_user.id] = True
        bot.send_message(msg.chat.id, "💸 Send UPI ID or QR")

    # =========================
    # BROADCAST
    # =========================
    @bot.message_handler(commands=['broadcast'])
    def broadcast_cmd(msg):
        if msg.from_user.id == ADMIN_ID:
            admin_state[msg.from_user.id] = "broadcast"
            bot.send_message(msg.chat.id, "📢 Send message")

    # =========================
    # PAYMENT REQUEST (VIP)
    # =========================
    @bot.message_handler(commands=['pay'])
    def pay_cmd(msg):
        bot.send_message(msg.chat.id, "💰 Send payment screenshot")

    # =========================
    # LEADERBOARD COMMAND
    # =========================
    @bot.message_handler(commands=['leaderboard'])
    def leaderboard(msg):

        top_users = users.find().sort("ref_count", -1).limit(10)

        text = "🏆 <b>TOP REFERRERS</b>\n\n"

        rank = 1
        for user in top_users:
            username = user.get("username") or "NoName"
            refs = user.get("ref_count", 0)

            text += f"{rank}. @{username} - {refs} 👥\n"
            rank += 1

        bot.send_message(msg.chat.id, text, parse_mode="HTML")

    # =========================
    # BUTTON HANDLER (NEW)
    # =========================
    @bot.message_handler(func=lambda msg: msg.text in [
        "💰 Earn Money","👥 Refer & Earn","💎 Wallet","📤 Withdraw","🏆 Leaderboard"
    ])
    def button_handler(msg):

        user_id = msg.from_user.id
        update_user(user_id, msg.from_user.username)

        if msg.text == "👥 Refer & Earn":
            link = f"https://t.me/YOUR_BOT_USERNAME?start={user_id}"
            bot.send_message(msg.chat.id, f"👥 Invite & Earn\n\n🔗 {link}")

        elif msg.text == "💎 Wallet":
            user = users.find_one({"user_id": user_id})
            bot.send_message(
                msg.chat.id,
                f"💰 Wallet\n\n👥 Referrals: {user.get('ref_count',0)}\n💎 Balance: ₹{user.get('balance',0)}"
            )

        elif msg.text == "📤 Withdraw":
            withdraw_state[user_id] = True
            bot.send_message(msg.chat.id, "💸 Send UPI ID or QR")

        elif msg.text == "🏆 Leaderboard":
            top_users = users.find().sort("ref_count", -1).limit(10)

            text = "🏆 TOP REFERRERS\n\n"
            rank = 1

            for user in top_users:
                text += f"{rank}. {user.get('ref_count',0)} referrals\n"
                rank += 1

            bot.send_message(msg.chat.id, text)

        elif msg.text == "💰 Earn Money":
            bot.send_message(msg.chat.id, "💰 Invite users & earn money!")

    # =========================
    # HANDLE ALL (UNCHANGED)
    # =========================
    @bot.message_handler(content_types=['text','photo','video'])
    def handle_all(msg):

        user_id = msg.from_user.id
        update_user(user_id, msg.from_user.username)

        if admin_state.get(user_id) == "broadcast":
            for user in users.find():
                try:
                    bot.copy_message(user["user_id"], msg.chat.id, msg.message_id)
                except:
                    pass
            bot.send_message(msg.chat.id, "✅ Broadcast Done")
            admin_state.pop(user_id)
            return

        if withdraw_state.get(user_id):
            user = users.find_one({"user_id": user_id})
            balance = user.get("balance", 0)

            if balance < 10:
                bot.send_message(user_id, "❌ Min ₹10 required")
                withdraw_state.pop(user_id)
                return

            users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "withdraw_status": "pending",
                        "withdraw_data": msg.text if msg.content_type == "text" else "QR"
                    }
                }
            )

            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton("✅ Pay Done", callback_data=f"pay_{user_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"wreject_{user_id}")
            )

            bot.send_message(ADMIN_ID, f"💸 Withdraw Request\nUser: {user_id}\n₹{balance}", reply_markup=kb)
            bot.send_message(user_id, "⏳ Request Sent")
            withdraw_state.pop(user_id)
            return

        if msg.content_type == "photo":
            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
            )

            bot.send_photo(ADMIN_ID, msg.photo[-1].file_id,
                caption=f"💰 Payment Request\nUser: {user_id}",
                reply_markup=kb)

            bot.send_message(user_id, "⏳ Payment Under Review")

    # =========================
    # ADMIN PANEL (UNCHANGED)
    # =========================
    @bot.message_handler(commands=['admin'])
    def admin_panel(msg):
        if msg.from_user.id == ADMIN_ID:

            total = users.count_documents({})
            now = time.time()

            active = users.count_documents({"last_active": {"$gt": now - 86400}})
            dead = users.count_documents({"last_active": {"$lt": now - 86400}})

            approved = users.count_documents({"payment_status": "approved"})
            rejected = users.count_documents({"payment_status": "rejected"})
            pending = users.count_documents({"payment_status": {"$exists": False}})

            withdraws = users.count_documents({"withdraw_status": "pending"})

            text = f"""
🔥 <b>VIP ADMIN PANEL</b> 🔥

👥 Total: {total}
🟢 Active: {active}
🔴 Dead: {dead}

💰 Approved: {approved}
❌ Rejected: {rejected}
⏳ Pending: {pending}

💸 Withdraw Req: {withdraws}
"""

            kb = InlineKeyboardMarkup(row_width=2)

            kb.add(
                InlineKeyboardButton("📢 Broadcast", callback_data="broadcast"),
                InlineKeyboardButton("💸 Withdraw", callback_data="withdraw_list")
            )

            kb.add(
                InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"),
                InlineKeyboardButton("👑 VIP Users", callback_data="vip")
            )

            kb.add(
                InlineKeyboardButton("✅ Approved", callback_data="approved"),
                InlineKeyboardButton("❌ Rejected", callback_data="rejected")
            )

            bot.send_message(msg.chat.id, text, reply_markup=kb, parse_mode="HTML")

    # =========================
    # CALLBACK (UNCHANGED)
    # =========================
    @bot.callback_query_handler(func=lambda call: True)
    def callback_handler(call):

        data = call.data

        if data.startswith("approve_"):
            user_id = int(data.split("_")[1])
            users.update_one({"user_id": user_id}, {"$set": {"vip": True, "payment_status": "approved"}})
            bot.send_message(user_id, "✅ VIP Activated")

        elif data.startswith("reject_"):
            user_id = int(data.split("_")[1])
            users.update_one({"user_id": user_id}, {"$set": {"payment_status": "rejected"}})
            bot.send_message(user_id, "❌ Payment Rejected")

        elif data.startswith("pay_"):
            user_id = int(data.split("_")[1])
            users.update_one({"user_id": user_id}, {"$set": {"withdraw_status": "paid", "balance": 0}})
            bot.send_message(user_id, "✅ Payment Sent")

        elif data.startswith("wreject_"):
            user_id = int(data.split("_")[1])
            users.update_one({"user_id": user_id}, {"$set": {"withdraw_status": "rejected"}})
            bot.send_message(user_id, "❌ Withdraw Rejected")

        elif data == "withdraw_list":
            count = users.count_documents({"withdraw_status": "pending"})
            bot.send_message(call.message.chat.id, f"💸 Pending Withdraw: {count}")

        elif data == "leaderboard":
            top_users = users.find().sort("ref_count", -1).limit(10)

            text = "🏆 TOP REFERRERS\n\n"
            rank = 1

            for user in top_users:
                username = user.get("username") or "NoName"
                refs = user.get("ref_count", 0)

                text += f"{rank}. @{username} - {refs}\n"
                rank += 1

            bot.send_message(call.message.chat.id, text)
