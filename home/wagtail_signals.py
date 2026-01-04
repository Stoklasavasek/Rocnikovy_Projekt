"""
Signály pro Wagtail - zakázání automatického indexování dokumentů.

PROBLÉM:
Wagtail má bug v postgres search backendu - při nahrávání dokumentů (videa, PDF)
se objevuje chyba "UnboundLocalError: cannot access local variable 'weight'".
Kvůli tomu se dokumenty nemohly nahrát ani zobrazit v chooseru.

ŘEŠENÍ:
1. Přepíšeme search_index.insert_or_update_object() - ignoruje chyby
2. Přepíšeme DocumentForm.save() - použije ModelForm.save() bez indexování
3. Přepíšeme DocumentChooserViewSet - použije jednoduchý filtr místo search backendu

Výsledek: Dokumenty se nahrávají a zobrazují bez chyb.
"""
try:
    from wagtail.documents.models import Document
    from wagtail.documents.forms import BaseDocumentForm
    from wagtail.documents.views.chooser import DocumentChooserViewSet
    from wagtail.search import index
    WAGTAIL_AVAILABLE = True
except ImportError:
    WAGTAIL_AVAILABLE = False
    BaseDocumentForm = None
    DocumentChooserViewSet = None


if WAGTAIL_AVAILABLE:
    # 1. Monkey patching search_index.insert_or_update_object - ignoruje chyby
    _original_insert_or_update = index.insert_or_update_object
    
    def insert_or_update_object_safe(obj):
        """Bezpečné přidání objektu do indexu - ignoruje chyby z postgres backendu."""
        try:
            return _original_insert_or_update(obj)
        except Exception:
            pass
    
    index.insert_or_update_object = insert_or_update_object_safe
    
    # Přepíšeme search_index v wagtail.documents.forms modulu
    try:
        import sys
        if 'wagtail.documents.forms' not in sys.modules:
            import wagtail.documents.forms
        forms_module = sys.modules['wagtail.documents.forms']
        if hasattr(forms_module, 'search_index'):
            forms_module.search_index.insert_or_update_object = insert_or_update_object_safe
    except Exception:
        pass
    
    # 2. Přepíšeme DocumentForm.save() - použije ModelForm.save() místo původní metody
    # Tím se úplně vyhneme volání search_index.insert_or_update_object()
    from django.forms import ModelForm
    import functools
    
    # Získání správné form třídy z chooseru
    DocumentForm = None
    try:
        if DocumentChooserViewSet and hasattr(DocumentChooserViewSet, 'creation_form_class'):
            DocumentForm = DocumentChooserViewSet.creation_form_class
        elif BaseDocumentForm:
            DocumentForm = BaseDocumentForm
    except:
        DocumentForm = BaseDocumentForm if BaseDocumentForm else None
    
    if DocumentForm:
        _original_save = DocumentForm.save
        
        @functools.wraps(_original_save)
        def save_without_indexing(self, commit=True):
            """Uloží dokument bez indexování do search indexu."""
            if commit:
                return ModelForm.save(self, commit=True)
            return ModelForm.save(self, commit=False)
        
        DocumentForm.save = save_without_indexing
        
        # Přepíšeme i v modulu wagtail.documents.forms
        try:
            import sys
            if 'wagtail.documents.forms' in sys.modules:
                forms_module = sys.modules['wagtail.documents.forms']
                if hasattr(forms_module, 'BaseDocumentForm'):
                    forms_module.BaseDocumentForm.save = save_without_indexing
        except Exception:
            pass
    
    # 3. Monkey patching DocumentChooserViewSet - použije jednoduchý filtr místo search backendu
    # Tím se vyhneme chybám při zobrazování dokumentů v chooseru
    try:
        def get_queryset_without_search(self, request):
            """Vrátí queryset bez search - používá jednoduchý filtr místo search backendu."""
            queryset = Document.objects.all()
            
            # Filtrování podle search query
            search_query = request.GET.get('q', '').strip()
            if search_query:
                queryset = queryset.filter(title__icontains=search_query)
            
            # Filtrování podle kolekce
            collection_id = request.GET.get('collection_id')
            if collection_id:
                queryset = queryset.filter(collection_id=collection_id)
            
            return queryset.order_by('-created_at')
        
        def get_results_page_without_search(self, request):
            """Vrátí stránku výsledků bez search backendu - používá Django Paginator."""
            from django.core.paginator import Paginator
            queryset = self.get_queryset(request)
            paginator = Paginator(queryset, per_page=self.per_page)
            
            try:
                page_number = int(request.GET.get("p", 1))
            except (ValueError, TypeError):
                page_number = 1
            
            try:
                return paginator.page(page_number)
            except Exception:
                return paginator.page(1)
        
        DocumentChooserViewSet.get_queryset = get_queryset_without_search
        DocumentChooserViewSet.get_results_page = get_results_page_without_search
        
        # Přepíšeme results endpoint pro zobrazení dokumentů v chooseru
        if hasattr(DocumentChooserViewSet, 'results'):
            def results_without_search(self, request):
                """Vrátí výsledky bez search backendu."""
                try:
                    page = self.get_results_page(request)
                    return self.render_to_response({
                        'items': page,
                        'is_search': bool(request.GET.get('q')),
                    })
                except Exception:
                    # Fallback - vrátíme prázdnou stránku místo chyby
                    from django.core.paginator import Paginator
                    queryset = Document.objects.all()
                    paginator = Paginator(queryset, per_page=self.per_page)
                    return self.render_to_response({
                        'items': paginator.page(1),
                        'is_search': False,
                    })
            
            DocumentChooserViewSet.results = results_without_search
    except Exception:
        pass
