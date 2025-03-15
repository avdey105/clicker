#!/bin/bash

# Останавливаем все процессы бота
echo "Останавливаем все процессы бота..."
pkill -9 -f "python3 bot.py" || true

# Удаляем базу данных для чистого старта
echo "Удаляем базу данных для чистого старта..."
rm -f users.db

# Ждем, чтобы убедиться, что все процессы остановлены
echo "Ждем завершения всех процессов..."
sleep 3

# Проверяем наличие виртуального окружения
if [ ! -d "venv" ]; then
    echo "Виртуальное окружение не найдено. Создаем новое..."
    python3 -m venv venv
    
    echo "Активируем виртуальное окружение..."
    source venv/bin/activate
    
    echo "Устанавливаем зависимости..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Явно устанавливаем библиотеки для работы с таблицами
    echo "Устанавливаем библиотеки для работы с таблицами..."
    pip install openpyxl xlsxwriter
else
    echo "Активируем существующее виртуальное окружение..."
    source venv/bin/activate
    
    echo "Обновляем зависимости..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Явно устанавливаем библиотеки для работы с таблицами
    echo "Устанавливаем библиотеки для работы с таблицами..."
    pip install openpyxl xlsxwriter
fi

# Запускаем бота
echo "Запускаем бота..."
python3 bot.py 