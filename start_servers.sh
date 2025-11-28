#!/bin/bash

# Skript pro spuštění Django a Socket.IO serveru současně

# Zkontrolovat, jestli je aktivní virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment není aktivní. Aktivuji..."
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    else
        echo "❌ Virtual environment (.venv) nenalezen!"
        exit 1
    fi
fi

# Zjistit, který python příkaz použít (python3 nebo python)
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo "❌ Python nenalezen! Nainstaluj Python."
    exit 1
fi

echo "🚀 Spouštím Django server (port 8000)..."
$PYTHON_CMD manage.py runserver &
DJANGO_PID=$!

# Počkat chvíli, než se Django spustí
sleep 2

echo "🚀 Spouštím Socket.IO server (port 8001)..."
$PYTHON_CMD socketio_server.py &
SOCKETIO_PID=$!

echo ""
echo "✅ Oba servery jsou spuštěny!"
echo "   Django: http://localhost:8000"
echo "   Socket.IO: http://localhost:8001"
echo ""
echo "📝 Pro zastavení stiskni Ctrl+C"
echo ""

# Funkce pro ukončení obou procesů při Ctrl+C
cleanup() {
    echo ""
    echo "🛑 Ukončuji servery..."
    kill $DJANGO_PID $SOCKETIO_PID 2>/dev/null
    wait $DJANGO_PID $SOCKETIO_PID 2>/dev/null
    echo "✅ Servery ukončeny"
    exit
}

trap cleanup INT TERM

# Čekat na dokončení
wait

