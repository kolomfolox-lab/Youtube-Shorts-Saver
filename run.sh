#!/bin/bash
cd "$(dirname "$0")"

echo "Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate

echo "Установка зависимостей..."
pip install -r requirements.txt

echo "Запуск бота..."
# Используем python из виртуального окружения
python bot.py
