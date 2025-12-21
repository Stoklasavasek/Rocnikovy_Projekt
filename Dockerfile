FROM python:3.12-slim-bookworm

# V kontejneru používáme neprivilegovaného uživatele "wagtail".
RUN useradd wagtail

# Výchozí port pro Django / Gunicorn.
EXPOSE 8000

# Základní proměnné prostředí:
# - PYTHONUNBUFFERED: okamžitý výpis logů do STDOUT,
# - PORT: port, na kterém běží Gunicorn (musí souhlasit s EXPOSE).
ENV PYTHONUNBUFFERED=1 \
    PORT=8000

# Systemové balíčky potřebné pro Django, Wagtail a nástroje kolem Graphvizu.
RUN apt-get update --yes --quiet && apt-get install --yes --quiet --no-install-recommends \
    build-essential \
    libpq-dev \
    libmariadb-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libwebp-dev \
    graphviz \
 && rm -rf /var/lib/apt/lists/*

# Aplikační server – Gunicorn.
RUN pip install "gunicorn==20.0.4"

# Závislosti projektu.
COPY requirements.txt /
RUN pip install -r /requirements.txt

# `/app` je kořen projektu uvnitř kontejneru.
WORKDIR /app

# Nastavení vlastníka složky, aby mohl zapisovat např. do SQLite / media.
RUN chown wagtail:wagtail /app

# Kopie zdrojového kódu do kontejneru.
COPY --chown=wagtail:wagtail . .

# Entrypoint skript, který spouští Django (Gunicorn) + Socket.IO server.
COPY --chown=wagtail:wagtail docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Vše běží pod uživatelem "wagtail".
USER wagtail

# Otevíráme porty pro:
# - 8000: Django (Gunicorn),
# - 8001: Socket.IO server.
EXPOSE 8000 8001

ENTRYPOINT ["/app/docker-entrypoint.sh"]
