## QuizIT! – Django + Wagtail + Docker

Webová aplikace pro interaktivní kvízy ve stylu Kahoot pro školy.  
Učitel vytváří kvízy, otázky a odpovědi, studenti se připojují kódem a odpovídají v reálném čase. Výsledky vidí jak studenti, tak učitel (průběžné i finální hodnocení).

### Hlavní funkce

- **Živé kvízy** – učitel spouští kvíz v reálném čase, studenti se připojují pomocí kódu
- **Bodování podle rychlosti** – rychlejší správné odpovědi získávají více bodů (1000-400 bodů)
- **Žolíky** – studenti mohou použít žolíky (0-3 za hru), které smažou 2 špatné odpovědi
- **Nastavitelný čas** – učitel může nastavit čas na odpověď pro každou otázku (5-300 sekund)
- **Průběžný žebříček** – učitel vidí průběžné pořadí účastníků během kvízu
- **Real-time aktualizace** – statistiky a výsledky se aktualizují v reálném čase pomocí Socket.IO
- **Export výsledků** – učitel může stáhnout výsledky do CSV

### Použité technologie
- **Backend**: Django 4.2
- **CMS**: Wagtail 7
- **Databáze**: PostgreSQL (v Dockeru)
- **Autentizace**: `django-allauth`
- **Real-time**: `python-socketio` + samostatný Socket.IO server (v Dockeru, port 8001)
- **Front-end**: Django šablony + vlastní CSS (`kahootapp/static/css/kahootapp.css`)
- **Název aplikace**: QuizIT!
- **Modelový diagram**: `django-extensions` + Graphviz (`media/quiz_models.png`)

---

### Jak projekt spustit (Docker, to používáš teď)

Požadavky:
- Docker + Docker Compose (Docker Desktop na macOS/Windows, nebo docker/docker-compose na Linuxu)

V kořeni projektu (`/Users/vaclavstoklasa/Desktop/projekt/28.10/krasa`) spusť:

```bash
cd /Users/vaclavstoklasa/Desktop/projekt/28.10/krasa

# build image (použij při prvním spuštění nebo po změně Dockerfile / requirements.txt)
docker-compose build web

# start databáze + Django + Socket.IO server
docker-compose up -d
```

Aplikace pak běží na:

- **Django (web)**: `http://localhost:8000`
- **Socket.IO server**: `http://localhost:8001` (používají ho prohlížeče, ty ho ručně neotvíráš)

Zastavení:

```bash
docker-compose down
```

Plné smazání databáze (reset dat):

```bash
docker-compose down -v
rm -rf data/
```

---

### Jak projekt spustit bez Dockeru (jen pro vývoj / školní PC)

Požadavky:
- Python 3.10+
- (Volitelně) PostgreSQL, jinak můžeš použít SQLite po úpravě settings.

```bash
cd /Users/vaclavstoklasa/Desktop/projekt/28.10/krasa

# vytvoření virtuálního prostředí
python3 -m venv .venv
source .venv/bin/activate

# instalace závislostí
pip install -r requirements.txt

# migrace databáze
python manage.py migrate

# spuštění Django serveru
python manage.py runserver
```

Aplikace poběží na `http://127.0.0.1:8000/`.

Socket.IO server (pokud bys ho chtěl spouštět mimo Docker):

```bash
source .venv/bin/activate
python socketio_server.py
```

---

### Role a oprávnění

V aplikaci jsou tři základní typy uživatelů:
- **Admin** – Django superuser, plná práva (`/django-admin/`, Wagtail, nastavení).
- **Učitel (Teacher)** – vytváří a spouští kvízy, vidí průběžné výsledky, ovládá sezení.
- **Student** – připojuje se k sezení pomocí kódu a odpovídá na otázky.

Role učitele je určena funkcí v `quiz/roles.py`:
- `user_is_teacher(user)` – rozpozná učitele (skupina Teacher / staff).

---

### Struktura projektu (zjednodušeně)

- `kahootapp/` – projekt, globální šablony, nastavení (dev/production).
- `quiz/` – hlavní logika kvízů (modely, view, šablony, Socket.IO integrace).
- `home/` – Wagtail stránka (úvodní/welcome screen).
- `static/`, `kahootapp/static/`, `home/static/` – CSS, JS a obrázky.
- `media/` – nahrané soubory (obrázky otázek, diagram modelů apod.).

Hlavní modely jsou v `quiz/models.py`:
- `Quiz` – kvíz s nastavitelným počtem žolíků (`jokers_count`)
- `Question` – otázka s nastavitelným časem na odpověď (`duration_seconds`)
- `Answer` – odpověď s příznakem správnosti
- `StudentAnswer` – odpovědi studentů v jednoduchém režimu
- `QuizSession` – živé sezení s unikátním kódem a hashem
- `Participant` – účastník sezení s počtem použitých žolíků
- `QuestionRun` – běh konkrétní otázky v sezení
- `Response` – odpověď účastníka s výpočtem bodů podle rychlosti (`calculate_points()`)

---

### Generování diagramu modelů (volitelné)

Pro appku `quiz` máš nastavené:
- `django-extensions` v `INSTALLED_APPS`
- `graphviz` a `pydotplus` v `requirements.txt`

Jak znovu vygenerovat diagram:

```bash
cd /Users/vaclavstoklasa/Desktop/projekt/28.10/krasa

# vygeneruje .dot soubor do sdíleného adresáře media (uvnitř kontejneru)
docker-compose exec web python manage.py graph_models quiz --dot -o /app/media/quiz_models.dot

# na host systému vytvoří PNG z .dot
dot -Tpng media/quiz_models.dot -o media/quiz_models.png
```

Výsledný obrázek najdeš jako `media/quiz_models.png`.

---

### Užitečné příkazy (shrnutí)

- Spuštění přes Docker: `docker-compose up -d`
- Zastavení: `docker-compose down`
- Migrace uvnitř Dockeru:  
  `docker-compose exec web python manage.py migrate`
- Vytvoření admin účtu:  
  `docker-compose exec web python manage.py createsuperuser`
- Zobrazení logů:  
  `docker-compose logs -f web`

---

### Bodování

Body se počítají podle rychlosti a správnosti odpovědi:
- **Špatná odpověď**: 0 bodů
- **Správná odpověď**:
  - 0-2 sekundy: 900-1000 bodů (lineární pokles)
  - 2-15 sekund: 400-900 bodů (lineární pokles)
  - 15+ sekund: 400 bodů (minimálně)

Výpočet probíhá v metodě `Response.calculate_points()` v `quiz/models.py`.

---

### Žolíky

Každý kvíz může mít nastavený počet žolíků (0-3 za celou hru). Žolík:
- Smaže 2 náhodné špatné odpovědi
- S 50% pravděpodobností (pokud je sudý počet odpovědí >= 4) zobrazí pouze polovinu možností
- Jinak zobrazí všechny odpovědi kromě 2 smazaných špatných

Žolíky lze použít pouze během běžící otázky, před odpovědí.
