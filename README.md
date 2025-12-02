## Kahoot pro školy – Django aplikace s Wagtail

Krátká webová aplikace ve stylu Kahoot pro školy. Umožňuje učitelům vytvářet kvízy, otázky a odpovědi a studentům se připojit pomocí kódu a odesílat své odpovědi. Součástí je i Wagtail CMS pro správu obsahu.

Odkaz inspirace/kontext: [README v repozitáři Rocnikovy_Projekt](https://github.com/Stoklasavasek/Rocnikovy_Projekt/blob/main/README.md)

### Hlavní funkce
- Tvorba kvízů učitelem (název, automaticky generovaný kód pro připojení)
- Správa otázek a odpovědí (správné/nesprávné)
- Připojení studenta do kvízu pomocí join kódu
- Vyhodnocení odpovědí (správnost se vyhodnocuje automaticky)
- Wagtail stránky pro správu obsahu (volitelné)

### Technologie
- Backend: Django
- CMS: Wagtail
- Databáze: SQLite (výchozí, pro produkci doporučen PostgreSQL)
- Autentizace: Django auth (s možností rozšíření o `django-allauth`)

### Rychlý start

#### Varianta A: S Dockerem (doporučeno - nejjednodušší)

**Instalace Dockeru přes terminál:**

**macOS:**
```bash
# 1. Nainstalovat Homebrew (pokud ho nemáš)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Nainstalovat Docker Desktop
brew install --cask docker

# 3. Spustit Docker Desktop (poprvé musíš spustit aplikaci ručně)
open /Applications/Docker.app

# 4. Počkat, až se Docker spustí (ikona v menu bar)
```

**Linux (Ubuntu/Debian):**
```bash
# 1. Aktualizovat balíčky
sudo apt update

# 2. Nainstalovat Docker
sudo apt install docker.io docker-compose -y

# 3. Spustit Docker službu
sudo systemctl start docker
sudo systemctl enable docker

# 4. Přidat uživatele do docker skupiny (aby nemusel sudo)
sudo usermod -aG docker $USER

# 5. Odhlásit se a znovu přihlásit (nebo restartovat terminál)
# Pak už můžeš používat docker bez sudo
```

**Windows (WSL2):**
```bash
# 1. Nainstalovat WSL2 (v PowerShell jako admin)
wsl --install

# 2. Restartovat počítač

# 3. V WSL terminálu nainstalovat Docker
sudo apt update
sudo apt install docker.io docker-compose -y

# 4. Spustit Docker službu
sudo service docker start
```

**Ověření instalace:**
```bash
docker --version
docker-compose --version
```

Pokud příkazy fungují, Docker je nainstalovaný!

**Postup po instalaci Dockeru:**
```bash
# 1. Stáhnout projekt
git clone <repo-url>
cd krasa

# 2. Spustit vše jedním příkazem
docker-compose up
```

Docker automaticky:
- Postaví Docker image
- Spustí PostgreSQL databázi
- Spustí Django server (port 8000)
- Spustí Socket.IO server (port 8001)

Aplikace bude dostupná na: `http://localhost:8000`

**Pro zastavení:**
```bash
docker-compose down
```

---

#### Varianta B: Bez Dockeru (klasický způsob)

**Požadavky:**
- Python 3.9+
- PostgreSQL (volitelně, výchozí je SQLite)

**Postup:**
1) Vytvoření a aktivace virtuálního prostředí
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2) Instalace závislostí
```bash
pip install -r requirements.txt
```

3) Migrace a spuštění
```bash
python manage.py migrate
python manage.py runserver
```

4) V **samostatném terminálu** spustit Socket.IO server:
```bash
source .venv/bin/activate
python socketio_server.py
```

Aplikace poběží na `http://127.0.0.1:8000/`.

5) Administrátor (superuser)
```bash
python manage.py createsuperuser
```
Přihlášení do adminu: `http://127.0.0.1:8000/admin/`

### Role a oprávnění
V aplikaci jsou používány tři role:
- Admin: superuser, má plná oprávnění v Django adminu i aplikaci.
- Učitel (Teacher): člen skupiny `Teacher` nebo uživatel se statusem staff (viz `quiz/roles.py`).
- Student: běžný uživatel bez přístupu do adminu.

Nastavení doporučení:
- V adminu vytvoř skupinu `Teacher` a přiřaď ji učitelům. Učitelům můžeš nechat `is_staff = True` pro přístup do adminu.
- Studentům `is_staff = False`, nepřiřazuj skupinu `Teacher`.

Kontroly v kódu:
- `quiz/roles.py` obsahuje:
  - `user_is_teacher(user)`: vrátí True, pokud je uživatel ve skupině `Teacher` nebo má `is_staff = True`.
  - `teacher_required(view)`: dekorátor pro omezení přístupu na učitelské obrazovky.

Chování můžeš upravit tak, aby učitelem byl pouze člen skupiny (bez `is_staff`).

### Modely a vztahy
Datové modely hlavní aplikace jsou v `quiz/models.py`:
- `Quiz` (title, created_by, join_code)
- `Question` (text, vazba na `Quiz`)
- `Answer` (text, is_correct, vazba na `Question`)
- `StudentAnswer` (student, question, selected_answer, correct)

Textový popis modelů a vztahů (pro jednoduché vygenerování diagramu) je uložen v:
- `MODELS_TEXT.txt` (v kořeni projektu)

Volitelně můžeš vytvořit i diagram (Mermaid/obrázek). Pokud nechceš řešit Graphviz, vlož obsah z `MODELS_TEXT.txt` do nástroje, který ti vygeneruje ERD.

### Struktura projektu (zkráceně)
- `kahootapp/` – projektové nastavení a šablony
- `quiz/` – jádro aplikace (modely, pohledy, šablony kvízu)
- `home/` – Wagtail HomePage, statiky a šablony
- `search/` – vyhledávání
- `db.sqlite3` – lokální databáze
- `requirements.txt` – závislosti

### Užitečné příkazy
- Spuštění serveru: `python manage.py runserver`
- Migrace: `python manage.py makemigrations && python manage.py migrate`
- Vytvoření admina: `python manage.py createsuperuser`

### Poznámky
- Pro produkční nasazení použij PostgreSQL a nastav proměnné prostředí (SECRET_KEY, DEBUG=False atd.).
- Wagtail oprávnění nastav ve skupinách podle potřeby (přístup do Wagtail adminu, práva ke stránkám, dokumentům a obrázkům).


### Socket.IO - Real-time komunikace

Aplikace používá Socket.IO pro real-time aktualizace během kvízů.

**Spuštění:**

1. Spusť Django server (port 8000):
```bash
python manage.py runserver
```

2. V **samostatném terminálu** spusť Socket.IO server (port 8001):
```bash
python socketio_server.py
```

**Funkce:**
- Real-time aktualizace stavu session (waiting/question/finished)
- Real-time aktualizace statistik odpovědí pro učitele
- Automatické přesměrování při změně otázky
- Fallback na polling pokud Socket.IO není dostupný


### Implementované funkce
- hash URL - generátor hash pro session URL
- vyhodnocování postupně mezi otázkami