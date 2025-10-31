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

### Rychlý start (lokálně)
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
Aplikace poběží na `http://127.0.0.1:8000/`.

4) Administrátor (superuser)
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
