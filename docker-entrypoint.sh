#!/bin/bash
# Entrypoint skript pro Docker kontejner
# Spouští Django server a Socket.IO server současně

set -e  # Ukončit při chybě

# Čekání na připojení databáze (pokud je nastavená)
if [ -n "$DB_HOST" ]; then
    echo "Čekám na připojení databáze..."
    until python -c "import psycopg2; psycopg2.connect(host='$DB_HOST', port='${DB_PORT:-5432}', user='$DB_USER', password='$DB_PASSWORD', dbname='$DB_NAME')" 2>/dev/null; do
        echo "Databáze ještě není připravená, čekám..."
        sleep 2
    done
    echo "Databáze je připravená!"
fi

# Spuštění migrací databáze
echo "Spouštím migrace..."
python manage.py migrate --noinput

# Shromáždění statických souborů (CSS, JS, obrázky) do jedné složky
python manage.py collectstatic --noinput

# Spuštění Django serveru na pozadí (port 8000)
echo "Spouštím Django server (port 8000)..."
python manage.py runserver 0.0.0.0:8000 &
DJANGO_PID=$!

# Krátká pauza pro inicializaci Django serveru
sleep 3

# Spuštění Socket.IO serveru na pozadí (port 8001) pro real-time komunikaci
echo "Spouštím Socket.IO server (port 8001)..."
python socketio_server.py &
SOCKETIO_PID=$!

echo ""
echo "✅ Oba servery jsou spuštěny!"
echo "   Django: http://localhost:8000"
echo "   Socket.IO: http://localhost:8001"
echo ""


# Funkce pro čisté ukončení obou serverů při zastavení kontejneru
cleanup() {
    echo ""
    echo "🛑 Ukončuji servery..."
    kill $DJANGO_PID $SOCKETIO_PID 2>/dev/null || true
    wait $DJANGO_PID $SOCKETIO_PID 2>/dev/null || true
    echo "✅ Servery ukončeny"
    exit
}

# Nastavení trap pro zachycení signálů SIGTERM a SIGINT (Ctrl+C)
trap cleanup SIGTERM SIGINT

# Čekání na ukončení (kontejner běží dokud není zastaven)
wait

