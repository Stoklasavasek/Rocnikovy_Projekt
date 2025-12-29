# Testování Educational Materials (Vzdělávacích materiálů)

## Krok 1: Vytvoření a aplikování migrace

```bash
cd /Users/vaclavstoklasa/Desktop/projekt/28.10/krasa

# Vytvoření migrace
docker-compose exec web python manage.py makemigrations home

# Aplikování migrace
docker-compose exec web python manage.py migrate
```

## Krok 2: Vytvoření testovacího kvízu (pokud ještě nemáš)

1. Přihlas se do aplikace jako učitel
2. Vytvoř nový kvíz s několika otázkami
3. Poznamenej si **ID kvízu** (např. 1, 2, 3...) - najdeš ho v URL při úpravě kvízu nebo v Django adminu

## Krok 3: Vytvoření vzdělávacího materiálu v Wagtail adminu

1. Otevři **Wagtail admin**: `http://localhost:8000/admin/`
2. Přihlas se jako admin nebo učitel s přístupem do Wagtail
3. V levém menu klikni na **"Pages"**
4. Klikni na **"Add child page"** u Home stránky
5. Vyber **"Educational Material"**
6. Vyplň formulář:
   - **Title**: Např. "Úvod do matematiky"
   - **ID souvisejícího kvízu**: Zadej ID kvízu, který jsi vytvořil (např. 1)
   - **Typ materiálu**: Vyber typ (Textový materiál, Video, Externí odkaz, Dokument)
   - **Obsah materiálu**: Zadej text pomocí rich text editoru
   - **Externí URL**: (volitelné) Pokud je typ "Externí odkaz" nebo "Video"
   - **Zobrazení**:
     - ☑ Zobrazit před kvízem (pokud chceš, aby se zobrazil před kvízem)
     - ☑ Zobrazit po kvízu (pokud chceš, aby se zobrazil po kvízu)
7. Klikni **"Publish"** (publikovat)

## Krok 4: Testování zobrazení materiálů

### Test 1: Materiály před kvízem

1. Přihlas se jako student (nebo jiný uživatel)
2. Jdi na stránku s kvízem: `http://localhost:8000/quiz/1/start/` (nahraď 1 za ID tvého kvízu)
3. **Očekávaný výsledek**: 
   - Měl by se zobrazit sekce "📚 Vzdělávací materiály"
   - Seznam materiálů s `show_before_quiz=True`
   - Odkazy na jednotlivé materiály
   - Před formulářem s otázkami

### Test 2: Materiály po kvízu

1. Vyplň kvíz a odešli odpovědi
2. **Očekávaný výsledek**:
   - Na stránce s výsledky by se měla zobrazit sekce "📚 Doporučené materiály k prostudování"
   - Seznam materiálů s `show_after_quiz=True`
   - Odkazy na jednotlivé materiály

### Test 3: Zobrazení samotného materiálu

1. Klikni na odkaz na materiál (z předchozích testů)
2. **Očekávaný výsledek**:
   - Měla by se zobrazit stránka s materiálem
   - Informace o typu materiálu
   - Obsah materiálu (formátovaný text)
   - Odkaz na související kvíz (pokud existuje)
   - Externí URL (pokud je zadán)

## Krok 5: Testování různých typů materiálů

Vytvoř několik materiálů s různými typy:
- **Textový materiál**: Použij RichTextField pro formátovaný text
- **Video**: Zadej externí URL na YouTube video
- **Externí odkaz**: Zadej URL na externí stránku
- **Dokument**: Zadej URL na PDF nebo dokument

## Krok 6: Testování validace

1. Zkus vytvořit materiál s neexistujícím ID kvízu (např. 99999)
2. **Očekávaný výsledek**: Měla by se zobrazit chyba validace

## Řešení problémů

### Migrace nefunguje
```bash
# Zkontroluj, jestli kontejner běží
docker-compose ps

# Pokud neběží, spusť ho
docker-compose up -d

# Zkontroluj logy
docker-compose logs web
```

### Materiály se nezobrazují
1. Zkontroluj, že materiál je **publikovaný** (live=True)
2. Zkontroluj, že `related_quiz_id` odpovídá ID kvízu
3. Zkontroluj, že máš správně nastavené `show_before_quiz` nebo `show_after_quiz`
4. Zkontroluj logy: `docker-compose logs web`

### Chyby v šabloně
- Zkontroluj, že máš `{% load wagtailcore_tags %}` v šabloně
- Zkontroluj, že šablona existuje: `home/templates/home/educational_material_page.html`

## Užitečné příkazy

```bash
# Zobrazení všech stránek v databázi
docker-compose exec web python manage.py shell
>>> from home.models import EducationalMaterial
>>> EducationalMaterial.objects.all()

# Vytvoření superuser (pokud nemáš)
docker-compose exec web python manage.py createsuperuser
```

