QuizIT! – Django + Wagtail + Docker

📺 Videoprezentace: YouTube video k projektu

Webová aplikace pro interaktivní kvízy ve stylu Kahoot pro školy.
Učitel vytváří kvízy, otázky a odpovědi, studenti se připojují kódem a odpovídají v reálném čase. Výsledky vidí jak studenti, tak učitel (průběžné i finální hodnocení).

Hlavní funkce

Živé kvízy – učitel spouští kvíz v reálném čase, studenti se připojují pomocí kódu

Bodování podle rychlosti – rychlejší správné odpovědi získávají více bodů (1000-400 bodů)

Žolíky – studenti mohou použít žolíky (0-3 za hru), které smažou 2 špatné odpovědi

Nastavitelný čas – učitel může nastavit čas na odpověď pro každou otázku (5-300 sekund)

Průběžný žebříček – učitel vidí průběžné pořadí účastníků během kvízu

Real-time aktualizace – statistiky a výsledky se aktualizují v reálném čase pomocí Socket.IO

Export výsledků – učitel může stáhnout výsledky do CSV

Použité technologie

Backend: Django 4.2

CMS: Wagtail 7

Databáze: PostgreSQL (v Dockeru)

Autentizace: django-allauth

Real-time: python-socketio + samostatný Socket.IO server (v Dockeru, port 8001)

Front-end: Django šablony + vlastní CSS (kahootapp/static/css/kahootapp.css)

Název aplikace: QuizIT!

Modelový diagram: django-extensions + Graphviz (media/quiz_models.png)
