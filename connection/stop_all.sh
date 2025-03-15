#!/bin/bash

echo "Останавливаем все процессы..."
pkill -f "python3 bot.py"
sleep 2

# Для особо упрямых процессов
pkill -9 -f "python3 bot.py"
sleep 1

echo "Все процессы остановлены" 