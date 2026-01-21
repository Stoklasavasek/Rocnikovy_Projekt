# 🎓 QuizIT!

**QuizIT!** je webová aplikace pro tvorbu a hraní **interaktivních kvízů v reálném čase**, inspirovaná nástroji jako Kahoot.  
Je určená především pro školy – učitelé vytvářejí kvízy, studenti se připojují pomocí kódu a odpovídají v reálném čase.

📺 **Videoprezentace projektu:**  
👉 https://www.youtube.com/watch?v=_vaSvGkfJBQ

---

## 🚀 Hlavní funkce

### 🧑‍🏫 Pro učitele
- **Živé kvízy** – spuštění kvízu v reálném čase
- **Správa obsahu** – tvorba kvízů, otázek a odpovědí přes Wagtail CMS
- **Nastavitelný čas** – 5–300 sekund na otázku
- **Průběžný žebříček** – sledování pořadí účastníků během hry
- **Export výsledků** – stažení výsledků do CSV
- **Přehledné statistiky** – průběžné i finální vyhodnocení

### 👨‍🎓 Pro studenty
- **Připojení pomocí kódu**
- **Bodování podle rychlosti odpovědi**  
  *(správná odpověď = 400–1000 bodů)*
- **Žolíky** – možnost smazat 2 špatné odpovědi (0–3 za hru)
- **Okamžitá zpětná vazba** a přehled výsledků

---

## ⚡ Real-time funkce
- Aktualizace otázek, odpovědí, skóre a statistik **v reálném čase**
- Komunikace mezi klienty a serverem pomocí **Socket.IO**
- Samostatný Socket.IO server běžící v Dockeru

---

## 🛠 Použité technologie

### Backend
- **Django 4.2**
- **Wagtail 7** (CMS)
- **PostgreSQL** (běžící v Dockeru)
- **django-allauth** (autentizace)

### Real-time komunikace
- **python-socketio**
- **Socket.IO server** (Docker, port `8001`)

### Frontend
- **Django templates**
- **Tailwind CSS** (styling a responzivní layout)
- Vlastní úpravy stylů (`kahootapp/static/css/`)

### Dev & nástroje
- **Docker & Docker Compose**
- **django-extensions**
- **Graphviz** – generování modelového diagramu

---

## 🧩 Architektura
- Backend + CMS běží v Django aplikaci
- Samostatný Socket.IO server pro real-time komunikaci
- Databáze PostgreSQL v Docker kontejneru

📊 **Modelový diagram databáze:**  
`media/quiz_models.png`

---

## ▶️ Spuštění projektu (lokálně)

```bash
docker-compose up --build
