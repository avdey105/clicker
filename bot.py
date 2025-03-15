import logging
import sqlite3
import pandas as pd
import io
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
WALLET_ADDRESS, CONFIRM_WALLET_CHANGE, ADMIN_PASSWORD, ADMIN_BROADCAST, ADMIN_USER_INFO, ADMIN_MODIFY_COINS, ADMIN_MODIFY_COINS_AMOUNT = range(7)

# Константы для callback_data
PROFILE, WALLET, REFERRAL = "profile", "wallet", "referral"

# Пароль администратора
ADMIN_PASSWORD_VALUE = "g23qsUFO"

# Декоратор для управления соединением с базой данных
def with_database(func):
    def wrapper(*args, **kwargs):
        conn = sqlite3.connect('users.db')
        try:
            return func(conn, *args, **kwargs)
        finally:
            conn.close()
    return wrapper

# Создание базы данных
@with_database
def setup_database(conn):
    conn.cursor().execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        wallet_address TEXT DEFAULT NULL,
        coins INTEGER DEFAULT 10,
        referrer_id INTEGER DEFAULT NULL,
        referral_code TEXT DEFAULT NULL
    )
    ''')
    conn.commit()

# Регистрация пользователя
@with_database
def register_user(conn, user_id, username, referrer_id=None):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        return False
    import uuid
    referral_code = str(uuid.uuid4())[:8]
    cursor.execute("INSERT INTO users (user_id, username, coins, referrer_id, referral_code) VALUES (?, ?, ?, ?, ?)",
                   (user_id, username, 10, referrer_id, referral_code))
    if referrer_id:
        cursor.execute("UPDATE users SET coins = coins + 5 WHERE user_id = ?", (referrer_id,))
    conn.commit()
    return True

# Главное меню
def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Мой профиль", callback_data=PROFILE),
         InlineKeyboardButton("💰 Кошелек", callback_data=WALLET)],
        [InlineKeyboardButton("🔗 Реферальная ссылка", callback_data=REFERRAL)]
    ])

# Отправка главного меню
def send_main_menu(update, context, message):
    update.message.reply_text(message, reply_markup=get_main_keyboard(), parse_mode='Markdown')

# Команда /start
def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_id, username = user.id, user.username or f"{user.first_name} {user.last_name}".strip()
    referrer_id = None
    if context.args:
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE referral_code = ?", (context.args[0],))
            result = cursor.fetchone()
            referrer_id = result[0] if result else None
    is_new = register_user(user_id, username, referrer_id)
    message = (f"🍭 Привет, {username}! Добро пожаловать в игру-кликер ChupsCoin! 🍭\n\n"
               "У вас уже есть 10 монет на счету! 🪙\n\n"
               "🎮 Что это за игра?\n"
               "• Хлопайте Чупа-чупса по жопе и копите монетки!\n"
               "• В разделе календарь можно посмотреть общее количество монет и время до раздачи\n"
               "• На лидерборде вы увидите топ игроков\n\n"
               "💎 Скоро мы выпустим свой токен! Не спешите продавать его сразу - мы будем:\n"
               "• Устраивать разные приколюхи\n"
               "• Пампить цену\n"
               "• Выводить токен на биржу\n"
               "• Наша цель - 1$ за 1 монету!\n\n"
               "⚠️ Важно! Не забудьте добавить свой кошелек TON Keeper. Если при раздаче кошелек не будет указан, токены не придут!\n\n"
               "📢 Все подробности в нашем канале: [ChupsCoin](https://t.me/ChupsCoin)") if is_new else (
        f"🍭 С возвращением, {username}!\n\n"
        "Продолжайте хлопать Чупа-чупса по жопе и копить монетки!\n"
        "📢 Следите за новостями в канале: [ChupsCoin](https://t.me/ChupsCoin)")
    send_main_menu(update, context, message)

# Обработчик "Мой профиль"
@with_database
def profile_callback(conn, update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    cursor = conn.cursor()
    cursor.execute("SELECT username, wallet_address, coins FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,))
    referrals_count = cursor.fetchone()[0]
    message = (f"📊 Профиль пользователя {user_data[0]}:\n\n🪙 Монеты: {user_data[2]}\n👥 Количество рефералов: {referrals_count}\n"
               f"💼 Адрес кошелька: {user_data[1] or 'не указан'}\n" + ("Нажмите на кнопку 'Кошелек', чтобы добавить адрес кошелька." if not user_data[1] else "")) if user_data else (
        "Ошибка: ваш профиль не найден. Пожалуйста, используйте команду /start для регистрации.")
    query.edit_message_text(text=message, reply_markup=get_main_keyboard())

# Обработчик "Кошелек"
def wallet_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    context.user_data.update({'message_id': query.message.message_id, 'chat_id': query.message.chat_id})
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT wallet_address FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
    if result and result[0]:
        query.edit_message_text(
            text=f"У вас уже есть кошелек: {result[0]}\n\nВы хотите изменить адрес кошелька?",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Да, изменить", callback_data="change_wallet_yes"),
                                               InlineKeyboardButton("Нет, отмена", callback_data="change_wallet_no")]]))
        return CONFIRM_WALLET_CHANGE
    query.edit_message_text("Пожалуйста, отправьте адрес вашего кошелька в следующем сообщении.")
    return WALLET_ADDRESS

# Подтверждение смены кошелька
def confirm_wallet_change(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if query.data == "change_wallet_yes":
        query.edit_message_text("Пожалуйста, отправьте новый адрес вашего кошелька в следующем сообщении.")
        return WALLET_ADDRESS
    query.edit_message_text("Операция отменена. Адрес кошелька остался прежним.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

# Сохранение кошелька
@with_database
def save_wallet_address(conn, update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    wallet_address = update.message.text
    conn.cursor().execute("UPDATE users SET wallet_address = ? WHERE user_id = ?", (wallet_address, user_id))
    conn.commit()
    update.message.reply_text(f"Адрес кошелька успешно сохранен: {wallet_address}", reply_markup=get_main_keyboard())
    if 'message_id' in context.user_data:
        try:
            context.bot.delete_message(chat_id=context.user_data['chat_id'], message_id=context.user_data['message_id'])
        except Exception as e:
            logger.error(f"Не удалось удалить сообщение: {e}")
    return ConversationHandler.END

# Обработчик "Реферальная ссылка"
@with_database
def referral_callback(conn, update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    cursor = conn.cursor()
    cursor.execute("SELECT referral_code FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        referral_link = f"https://t.me/{context.bot.username}?start={result[0]}"
        message = f"🔗 Ваша реферальная ссылка:\n\n`{referral_link}`\n\nПоделитесь этой ссылкой с друзьями. За каждого приглашенного друга вы получите 5 монет!"
        query.edit_message_text(text=message, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Назад", callback_data="back")]]), parse_mode='Markdown')
    else:
        query.edit_message_text("Ошибка: ваш профиль не найден. Пожалуйста, используйте команду /start для регистрации.", reply_markup=get_main_keyboard())

# Кнопка "Назад"
def back_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    query.edit_message_text("Главное меню. Выберите действие:", reply_markup=get_main_keyboard())

# Обработчик кнопок
def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    data = query.data
    if data == PROFILE:
        profile_callback(update, context)
    elif data == REFERRAL:
        referral_callback(update, context)
    elif data == "back":
        back_callback(update, context)

# Команда /admin
def admin_command(update: Update, context: CallbackContext) -> int:
    message = update.message.reply_text("Пожалуйста, введите пароль администратора:")
    context.user_data['admin_password_message_id'] = message.message_id
    return ADMIN_PASSWORD

# Меню администратора
def show_admin_menu(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("📢 Рассылка всем пользователям", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👤 Информация о пользователе", callback_data="admin_user_info")],
        [InlineKeyboardButton("🪙 Изменить количество монет", callback_data="admin_modify_coins")],
        [InlineKeyboardButton("📊 Выгрузить базу данных", callback_data="admin_export_db")],
        [InlineKeyboardButton("❌ Выйти из режима администратора", callback_data="admin_exit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "✅ Панель администратора. Выберите действие:"
    if update.callback_query:
        update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        update.message.reply_text(text, reply_markup=reply_markup)

# Обработчик кнопок администратора
def admin_button_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    if not context.user_data.get('is_admin', False):
        query.edit_message_text("У вас нет прав администратора.")
        return ConversationHandler.END
    action = query.data
    if action == "admin_broadcast":
        query.edit_message_text("Введите сообщение для рассылки всем пользователям:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Назад в меню админа", callback_data="admin_back")]]))
        return ADMIN_BROADCAST
    elif action == "admin_user_info":
        query.edit_message_text("Введите ID пользователя или имя пользователя для получения информации:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Назад в меню админа", callback_data="admin_back")]]))
        return ADMIN_USER_INFO
    elif action == "admin_modify_coins":
        query.edit_message_text("Введите ID или имя пользователя (@username), которому нужно изменить количество монет:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Назад в меню админа", callback_data="admin_back")]]))
        return ADMIN_MODIFY_COINS
    elif action == "admin_export_db":
        export_database(update, context)
        return ConversationHandler.END
    elif action == "admin_exit":
        context.user_data['is_admin'] = False
        query.edit_message_text("Вы вышли из режима администратора.")
        user = update.effective_user
        username = user.username or f"{user.first_name} {user.last_name}".strip()
        message = f"🍭 С возвращением, {username}!\n\nПродолжайте хлопать Чупа-чупса по жопе и копить монетки!\n📢 Следите за новостями в канале: [ChupsCoin](https://t.me/ChupsCoin)"
        context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=get_main_keyboard(), parse_mode='Markdown')
        return ConversationHandler.END
    elif action == "admin_back":
        show_admin_menu(update, context)
        return ConversationHandler.END

# Информация о пользователе
@with_database
def admin_get_user_info(conn, update: Update, context: CallbackContext) -> int:
    user_identifier = update.message.text.strip()
    cursor = conn.cursor()
    try:
        if user_identifier.isdigit():
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (int(user_identifier),))
        else:
            user_identifier = user_identifier[1:] if user_identifier.startswith('@') else user_identifier
            cursor.execute("SELECT * FROM users WHERE username = ?", (user_identifier,))
        user_data = cursor.fetchone() or cursor.execute("SELECT * FROM users WHERE username LIKE ?", (f"%{user_identifier}%",)).fetchone()
        if user_data:
            user_id, username, wallet_address, coins, referrer_id, referral_code = user_data
            cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,))
            referrals_count = cursor.fetchone()[0]
            message = (f"📋 Информация о пользователе:\n\n🆔 ID: {user_id}\n👤 Имя пользователя: {username}\n🪙 Монеты: {coins}\n"
                       f"💼 Адрес кошелька: {wallet_address or 'не указан'}\n👥 Количество рефералов: {referrals_count}\n🔗 Реферальный код: {referral_code}\n")
            if referrer_id:
                cursor.execute("SELECT username FROM users WHERE user_id = ?", (referrer_id,))
                referrer = cursor.fetchone()
                if referrer:
                    message += f"👑 Пригласил: {referrer[0]} (ID: {referrer_id})\n"
        else:
            message = "❌ Пользователь не найден."
        update.message.reply_text(message)
        show_admin_menu(update, context)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        update.message.reply_text("❌ Произошла ошибка при получении информации о пользователе.")
        show_admin_menu(update, context)
    return ConversationHandler.END

# Изменение монет (шаг 1)
@with_database
def admin_modify_user_coins(conn, update: Update, context: CallbackContext) -> int:
    user_identifier = update.message.text.strip()
    cursor = conn.cursor()
    try:
        if user_identifier.isdigit():
            cursor.execute("SELECT user_id, username, coins FROM users WHERE user_id = ?", (int(user_identifier),))
        else:
            user_identifier = user_identifier[1:] if user_identifier.startswith('@') else user_identifier
            cursor.execute("SELECT user_id, username, coins FROM users WHERE username = ?", (user_identifier,))
        user_data = cursor.fetchone() or cursor.execute("SELECT user_id, username, coins FROM users WHERE username LIKE ?", (f"%{user_identifier}%",)).fetchone()
        if user_data:
            context.user_data.update({'target_user_id': user_data[0], 'target_username': user_data[1], 'current_coins': user_data[2]})
            update.message.reply_text(f"Пользователь: {user_data[1]}\nТекущее количество монет: {user_data[2]}\n\nВведите новое количество монет или изменение (например, +10 или -5):",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Назад в меню админа", callback_data="admin_back")]]))
            return ADMIN_MODIFY_COINS_AMOUNT
        update.message.reply_text("❌ Пользователь не найден.")
        show_admin_menu(update, context)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        update.message.reply_text("❌ Произошла ошибка при поиске пользователя.")
        show_admin_menu(update, context)
        return ConversationHandler.END

# Изменение монет (шаг 2)
@with_database
def admin_update_user_coins(conn, update: Update, context: CallbackContext) -> int:
    coins_input = update.message.text.strip()
    target_user_id = context.user_data.get('target_user_id')
    if not target_user_id:
        update.message.reply_text("❌ Ошибка: ID пользователя не найден. Начните процесс заново.")
        show_admin_menu(update, context)
        return ConversationHandler.END
    try:
        current_coins = context.user_data['current_coins']
        new_coins = current_coins + int(coins_input) if coins_input[0] in ['+', '-'] else int(coins_input)
        new_coins = max(0, new_coins)
        conn.cursor().execute("UPDATE users SET coins = ? WHERE user_id = ?", (new_coins, target_user_id))
        conn.commit()
        update.message.reply_text(f"✅ Количество монет для пользователя {context.user_data['target_username']} (ID: {target_user_id}) обновлено:\nБыло: {current_coins}\nСтало: {new_coins}")
        show_admin_menu(update, context)
    except ValueError:
        update.message.reply_text("❌ Некорректный формат. Пожалуйста, введите число или изменение (например, +10 или -5).")
        show_admin_menu(update, context)
    finally:
        # Удаляем только ненужные данные, оставляя is_admin
        context.user_data.pop('target_user_id', None)
        context.user_data.pop('target_username', None)
        context.user_data.pop('current_coins', None)
    return ConversationHandler.END

# Экспорт базы данных
def export_database(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    with sqlite3.connect('users.db') as conn:
        users_df = pd.read_sql_query("SELECT * FROM users", conn)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        users_df.to_excel(writer, sheet_name='Users', index=False)
    output.seek(0)
    context.bot.send_document(chat_id=query.message.chat_id, document=output, filename='users_database.xlsx', caption="📊 База данных пользователей")
    query.answer()
    keyboard = [
        [InlineKeyboardButton("📢 Рассылка всем пользователям", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👤 Информация о пользователе", callback_data="admin_user_info")],
        [InlineKeyboardButton("🪙 Изменить количество монет", callback_data="admin_modify_coins")],
        [InlineKeyboardButton("📊 Выгрузить базу данных", callback_data="admin_export_db")],
        [InlineKeyboardButton("❌ Выйти из режима администратора", callback_data="admin_exit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=query.message.chat_id, text="✅ Панель администратора. Выберите действие:", reply_markup=reply_markup)

# Проверка пароля администратора
def check_admin_password(update: Update, context: CallbackContext) -> int:
    if update.message.text == ADMIN_PASSWORD_VALUE:
        context.user_data['is_admin'] = True
        show_admin_menu(update, context)
        try:
            update.message.delete()
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=context.user_data.pop('admin_password_message_id'))
        except Exception as e:
            logger.error(f"Не удалось удалить сообщение: {e}")
    else:
        update.message.reply_text("❌ Неверный пароль. Доступ запрещен.")
        try:
            update.message.delete()
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=context.user_data.pop('admin_password_message_id'))
        except Exception as e:
            logger.error(f"Не удалось удалить сообщение: {e}")
    return ConversationHandler.END

# Рассылка сообщений
@with_database
def admin_broadcast_message(conn, update: Update, context: CallbackContext) -> int:
    message = update.message.text
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    success_count, fail_count = 0, 0
    for user in users:
        try:
            context.bot.send_message(chat_id=user[0], text=message)
            success_count += 1
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            fail_count += 1
    update.message.reply_text(f"Рассылка завершена!\n✅ Успешно отправлено: {success_count}\n❌ Ошибок: {fail_count}\n\nВернитесь в админ-панель с помощью /admin")
    return ConversationHandler.END

# Неизвестные сообщения
def unknown_message(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    username = user.username or f"{user.first_name} {user.last_name}".strip()
    update.message.reply_text("🤔 Очень интересно, но ничего не понятно. Открываю главное меню.")
    message = f"🍭 Привет, {username}!\n\nПродолжайте хлопать Чупа-чупса по жопе и копить монетки!\n📢 Следите за новостями в канале: [ChupsCoin](https://t.me/ChupsCoin)"
    send_main_menu(update, context, message)

# Основная функция
def main() -> None:
    setup_database()
    updater = Updater("АБРАКАДАБРА")
    dp = updater.dispatcher
    updater.bot.delete_webhook()
    dp.add_error_handler(lambda u, c: logger.error(f"Ошибка: {c.error}"))
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(ConversationHandler(
        entry_points=[CommandHandler("admin", admin_command), CallbackQueryHandler(admin_button_callback, pattern="^admin_")],
        states={
            ADMIN_PASSWORD: [MessageHandler(Filters.text & ~Filters.command, check_admin_password)],
            ADMIN_BROADCAST: [MessageHandler(Filters.text & ~Filters.command, admin_broadcast_message)],
            ADMIN_USER_INFO: [MessageHandler(Filters.text & ~Filters.command, admin_get_user_info)],
            ADMIN_MODIFY_COINS: [MessageHandler(Filters.text & ~Filters.command, admin_modify_user_coins)],
            ADMIN_MODIFY_COINS_AMOUNT: [MessageHandler(Filters.text & ~Filters.command, admin_update_user_coins)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END), CallbackQueryHandler(admin_button_callback, pattern="^admin_")],
        per_message=False
    ))
    dp.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(wallet_callback, pattern=f"^{WALLET}$")],
        states={
            WALLET_ADDRESS: [MessageHandler(Filters.text & ~Filters.command, save_wallet_address)],
            CONFIRM_WALLET_CHANGE: [CallbackQueryHandler(confirm_wallet_change, pattern="^change_wallet_(yes|no)$")],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    ))
    dp.add_handler(CallbackQueryHandler(button_callback))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, unknown_message))
    updater.start_polling(drop_pending_updates=True, allowed_updates=['message', 'callback_query'])
    updater.idle()

if __name__ == '__main__':
    main()
