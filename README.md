Kahoot – Ročníkový projekt

Popis projektu
Tento projekt je webová aplikace inspirovaná systémem Kahoot.
Umožňuje učitelům vytvářet kvízy a studentům se do nich připojovat v reálném čase pomocí kódu hry.

Hlavní funkce
- Registrace a přihlášení uživatelů (učitelé, studenti)
- Vytváření a správa kvízů (otázky s více možnostmi odpovědí)
- Spuštění hry a generování PIN kódu pro připojení
- Připojení hráčů pomocí kódu a zadání jména
- Odpovídání na otázky v reálném čase
- Vyhodnocení správných odpovědí a bodování hráčů
- Zobrazení výsledků na konci hry

Použité technologie
- Python 3
- Django – hlavní webový framework
- Django ORM – správa databáze
- SQLite – databáze (možno nahradit PostgreSQL/MySQL)
- Django Templates – renderování HTML
- Bootstrap / CSS – jednoduchý design a responzivita
- JavaScript – interaktivní prvky
- Git / GitHub – správa verzí
- pip / venv – správa závislostí a virtuální prostředí

Instalace a spuštění
1. Naklonuj repozitář:
   git clone https://github.com/Stoklasavasek/Rocnikovy_Projekt.git
   cd Rocnikovy_Projekt
2. Vytvoř virtuální prostředí a nainstaluj závislosti:
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
3. Proveď migrace databáze:
   python manage.py migrate
4. Spusť server:
   python manage.py runserver
5. Otevři aplikaci v prohlížeči:
   http://localhost:8000/

Struktura projektu
- kahootapp/ – hlavní aplikace (registrace, přihlášení, správa uživatelů)
- quiz/ – správa kvízů (otázky, odpovědi, hry)
- search/ – vyhledávání a připojování do her
- templates/ – HTML šablony
- static/ – CSS, JS, obrázky
- db.sqlite3 – databáze
- manage.py – spouštěcí skript Django

Plánovaná rozšíření
- Real-time komunikace (WebSockets / Django Channels) pro živé hry
- Vylepšení vizuálního designu (Bootstrap → Tailwind)
- Export výsledků kvízů (CSV, PDF)
- Sdílení kvízů mezi učiteli
- Administrátorský panel pro lepší správu her
- Přihlášení přes školní účet (OAuth2 / Microsoft)



<img width="857" height="794" alt="Untitled" src="https://github.com/user-attachments/assets/afe538dd-4f84-4ff5-b57d-2193d0b3543d" />
