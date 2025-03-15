## База данных

Бот использует SQLite для хранения данных пользователей. База данных создается автоматически при первом запуске бота.

Структура таблицы `users`:
- `user_id` - ID пользователя в Telegram (первичный ключ)
- `username` - Имя пользователя
- `wallet_address` - Адрес кошелька (может быть NULL)
- `coins` - Количество монет (по умолчанию 10)
- `referrer_id` - ID пользователя, пригласившего текущего пользователя (может быть NULL)
- `referral_code` - Уникальный реферальный код пользователя

# Инструкция по развертыванию Telegram бота на хостинге

## Данные для подключения
```
Сервер (Hostname): 77.222.40.254
Логин (Username): avdeygoolu
Пароль (Password): A8deyGolubko8
Порт (Port): 22
```

## Ручное развертывание

### 1. Подключение к серверу через SSH
```bash
ssh avdeygoolu@77.222.40.254 -p 22
```
После выполнения команды введите пароль: A8deyGolubko8

### 2. Загрузка файлов на сервер

Создайте архив с файлами бота если его еще нет:

```bash
zip bot_files.zip bot.py clean_start.sh requirements.txt START.md
```

Откройте новый терминал (не закрывая SSH-сессию) и выполните:
```bash
scp -P 22 bot_files.zip avdeygoolu@77.222.40.254:~/
```

### 3. Настройка и запуск бота
Вернитесь в окно с SSH-сессией и выполните следующие команды:

```bash
# Создаем директорию для бота (если её нет)
mkdir -p ~/telegrambot

# Распаковываем архив
unzip -o bot_files.zip -d ~/telegrambot/

# Переходим в директорию бота
cd ~/public_html

# Запускаем бота автоматически
chmod +x ./clean_start.sh 

для остановки процессов
chmod +x ./stop_all.sh

nohup ./clean_start.sh &

там еще пандас надо установить ./venv/bin/pip install pandas

затем активируем бекенд на фласк 
chmod +x run.sh
nohup ./run.sh &

чтоб остановить пайтон надо - killall python

для входа в вирт окруж - source venv/bin/activate
для выхода - deactivate

для запуска сервера  - nohup npm start &

# Для остановки бота в директории бота надо выполнить:
pkill -9 -f "python3 bot.py"

scp -P 22 "chupa-chups (Копия).zip" avdeygoolu@77.222.40.254:~/
