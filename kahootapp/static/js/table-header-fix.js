// JavaScript fallback pro opravu barev nadpisů tabulek
// Spustí se po načtení stránky a přidá inline styly - AGGRESIVNÍ PŘÍSTUP

(function() {
  function fixTableHeaders() {
    // Najdi všechny th elementy v thead - všechny možné selektory
    const allThs = document.querySelectorAll('thead th, table thead th, .min-w-full thead th, table.min-w-full thead th');
    
    allThs.forEach(th => {
      // Zkontroluj, jestli je v tmavém režimu
      const isDark = document.documentElement.classList.contains('dark');
      
      // Nastav barvu - VŽDY černé pozadí a bílý text
      th.style.setProperty('background', '#000000', 'important');
      th.style.setProperty('color', '#ffffff', 'important');
      th.style.setProperty('font-weight', '700', 'important');
      
      // Odstraň všechny Tailwind třídy, které mohou způsobovat problémy
      th.classList.remove('text-gray-500', 'text-gray-300', 'text-gray-200', 'text-white');
    });
  }
  
  // Spusť okamžitě
  fixTableHeaders();
  
  // Spusť po načtení DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fixTableHeaders);
  } else {
    // Pokud je DOM už načtený, spusť hned
    setTimeout(fixTableHeaders, 0);
  }
  
  // Spusť při změně tmavého režimu
  const observer = new MutationObserver(() => {
    setTimeout(fixTableHeaders, 10);
  });
  
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class']
  });
  
  // Spusť také při změně stránky (pro SPA)
  window.addEventListener('load', fixTableHeaders);
  window.addEventListener('pageshow', fixTableHeaders);
})();

