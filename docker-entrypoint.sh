#!/bin/bash
set -e

# Počkat, až bude databáze připravená (pokud používáme PostgreSQL)
if [ -n "$DB_HOST" ]; then
    echo "Čekám na připojení databáze..."
    until python -c "import psycopg2; psycopg2.connect(host='$DB_HOST', port='${DB_PORT:-5432}', user='$DB_USER', password='$DB_PASSWORD', dbname='$DB_NAME')" 2>/dev/null; do
        echo "Databáze ještě není připravená, čekám..."
        sleep 2
    done
    echo "Databáze je připravená!"
fi

# Spustit migrace
echo "Spouštím migrace..."
python manage.py migrate --noinput

# Spustit collectstatic (pokud ještě neběželo)
python manage.py collectstatic --noinput

# Spustit Django server na pozadí
echo "Spouštím Django server (port 8000)..."
python manage.py runserver 0.0.0.0:8000 &
DJANGO_PID=$!

# Počkat chvíli, než se Django spustí
sleep 3

# Spustit Socket.IO server na pozadí
echo "Spouštím Socket.IO server (port 8001)..."
python socketio_server.py &
SOCKETIO_PID=$!

echo ""
echo "✅ Oba servery jsou spuštěny!"
echo "   Django: http://localhost:8000"
echo "   Socket.IO: http://localhost:8001"
echo ""

# Funkce pro ukončení obou procesů při ukončení kontejneru
cleanup() {
    echo ""
    echo "🛑 Ukončuji servery..."
    kill $DJANGO_PID $SOCKETIO_PID 2>/dev/null || true
    wait $DJANGO_PID $SOCKETIO_PID 2>/dev/null || true
    echo "✅ Servery ukončeny"
    exit
}

trap cleanup SIGTERM SIGINT

# Čekat na dokončení
wait

