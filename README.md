📅 EventPlanner – Mobilní plánovač událostí s přáteli
EventPlanner je multiplatformní mobilní aplikace pro snadné plánování výletů, akcí a setkání s přáteli. Umožňuje vytváření skupin, hlasování o čase a místě, chatování i přidání počasí a veřejných akcí z Opavy.

🔧 Technologie
Část	Technologie
Frontend	Flutter
Backend	Django REST API / Firebase
Databáze	PostgreSQL / Firebase Firestore
Počasí	OpenWeatherMap API
Kalendář	table_calendar, device_calendar
Notifikace	Firebase Cloud Messaging (FCM)
Reálný čas	Firebase Realtime DB / WebSocket
Mapy	flutter_map nebo Google Maps

🗂️ Funkce
✅ Základní
👥 Tvorba skupin přátel (např. „Rodina“, „Kolegové“)

📅 Vytváření událostí s více lokacemi a termíny

🗳️ Hlasování o lokaci a čase

👤 Potvrzení účasti (ano / ne / možná)

💬 Chat nebo komentáře k událostem

🔔 Notifikace (upozornění, výsledky hlasování)

☀️ Zobrazení předpovědi počasí pro daný den a místo

📍 Veřejné akce (Opava)
🔎 Načítání kulturních a veřejných událostí z Opavy (API / RSS)

🤝 Možnost přidat veřejnou akci do skupiny a domluvit se s přáteli

🗓️ Integrace s kalendářem zařízení

🧭 Roadmapa vývoje
1. 📐 Fáze návrhu
 Návrh databázového modelu (uživatel, skupina, událost, hlasování…)

 Návrh API (pokud se používá vlastní backend)

 UI wireframy (Flutter obrazovky)

2. 💻 Frontend (Flutter)
 Autentizace (Firebase Auth)

 Tvorba / správa skupin

 Tvorba událostí + návrh míst a termínů

 Hlasování o čase a místě

 Potvrzení účasti

 Chat (Firebase Realtime Database)

 Kalendář událostí (table_calendar)

 Widget s počasím (OpenWeatherMap API)

 Notifikace (FCM)

3. 🌐 Integrace veřejných akcí
 Získávání dat z API / RSS města Opava

 Zobrazení veřejných akcí v appce

 Tvorba soukromé skupiny k veřejné události

4. 🧪 Testování a ladění
 Testy logiky a UI (Flutter testy)

 Testování na různých zařízeních

 UX ladění a responzivita

5. 🚀 Publikace
 Build pro Android (Google Play)

 Build pro iOS (TestFlight / App Store)

 Web verze (volitelně Flutter Web)

📎 Plánované rozšíření (bonusy)
📤 Sdílení událostí přes odkaz

📸 Přidání fotek a map k událostem


####KAHOOT pro skoly (office ucty, Oauth2,wagtail)

Nastavení přihlášení přes Microsoft (Azure AD)
------------------------------------------------

1) V Azure Portal vytvořte App registration
- Název: Kahoot pro školu
- Supported account types: Accounts in this organizational directory only (Single tenant)
- Redirect URI (web): http://localhost:8000/accounts/microsoft/login/callback/

2) Zkopírujte Client ID a Client Secret a uložte je do prostředí

Mac/Linux (shell):
```bash
export MS_CLIENT_ID="<APPLICATION_CLIENT_ID>"
export MS_CLIENT_SECRET="<CLIENT_SECRET>"
# volitelné: omezte na svůj tenant
export MS_TENANT="<YOUR_TENANT_ID>"  # nebo nechte prázdné = "common"
```

Docker (doporučeno přes .env):
Vytvořte soubor `.env` vedle `Dockerfile`:
```env
MS_CLIENT_ID=<APPLICATION_CLIENT_ID>
MS_CLIENT_SECRET=<CLIENT_SECRET>
MS_TENANT=<YOUR_TENANT_ID>
```
Pak přidejte načtení proměnných v `docker run` nebo `docker-compose`.

3) Instalace závislostí
```bash
pip install -r requirements.txt
```

4) Migrace a spuštění
```bash
python manage.py migrate
python manage.py runserver
```

5) Ověření
- Navštivte /accounts/login/ nebo použijte tlačítko „Přihlásit se přes Microsoft“ v horní liště.
- Po úspěchu budete přesměrováni na `/`.

Poznámky
- Přihlašování využívá `django-allauth` a poskytovatele `microsoft`.
- Přihlašování je povoleno i bez e-mailové verifikace (školní účty mají být ověřeny v Azure AD).




📊 Statistiky účasti a populárních míst

📡 Offline režim a synchronizace

🔄 iCal / Google Calendar export
