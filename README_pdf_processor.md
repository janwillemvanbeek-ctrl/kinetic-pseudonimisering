# Kinetic PDF Processor v2.0

Verbeterde PDF-verwerking voor medische dossiers, met speciale ondersteuning voor **handgeschreven tekst**.

## Waarom deze versie?

Medische dossiers bevatten vaak:
- Handgeschreven aantekeningen van artsen
- Gescande formulieren met handtekeningen
- Gemengde documenten (geprint + handgeschreven)

Standaard OCR (Tesseract) presteert slecht op handschrift. Deze versie lost dat op met:

1. **Beeldverbetering** - OpenCV preprocessing voor scherpere tekst
2. **Handschrift-detectie** - Automatisch detecteren waar handschrift staat
3. **Aangepaste OCR config** - Speciale Tesseract instellingen voor handschrift
4. **Cloud OCR optie** - Google Vision/Azure voor beste handschrift-herkenning

## Installatie

```bash
# Basis
pip install pdfplumber pytesseract pdf2image Pillow

# Beeldverbetering (sterk aanbevolen)
pip install opencv-python numpy

# Tesseract installeren
# macOS:
brew install tesseract tesseract-lang

# Ubuntu:
sudo apt-get install tesseract-ocr tesseract-ocr-nld

# Poppler (voor PDF naar image)
# macOS:
brew install poppler

# Ubuntu:
sudo apt-get install poppler-utils
```

## Gebruik

### Command line

```bash
# Automatische detectie (aanbevolen)
python pdf_processor.py dossier.pdf -o output.txt

# Forceer handschrift-modus
python pdf_processor.py dossier.pdf --method handwriting -o output.txt

# Hogere kwaliteit (langzamer)
python pdf_processor.py dossier.pdf --dpi 400 -o output.txt
```

### In Python code

```python
from pdf_processor import PDFProcessor

# Standaard gebruik
processor = PDFProcessor()
result = processor.process("dossier.pdf")
print(result.combined_text)

# Voor dossiers met veel handschrift
processor = PDFProcessor(
    tesseract_lang="nld+eng",
    dpi=400,              # Hogere DPI = beter handschrift
    enhance_images=True   # Beeldverbetering aan
)
result = processor.process("dossier.pdf", force_method="handwriting")

# Check confidence per pagina
for page in result.pages:
    if page.has_handwriting:
        print(f"Pagina {page.page_number}: handschrift (conf: {page.confidence:.0%})")
```

## Cloud OCR (beste resultaat voor handschrift)

Voor échte handgeschreven tekst is cloud OCR veel beter dan Tesseract.

### Google Cloud Vision
```python
from pdf_processor import CloudOCRHandler

text = CloudOCRHandler.extract_with_google_vision(
    "pagina.png",
    credentials_path="service-account.json"
)
```

### Azure Document Intelligence
```python
text = CloudOCRHandler.extract_with_azure_document_intelligence(
    "pagina.png",
    endpoint="https://westeurope.api.cognitive.microsoft.com/",
    api_key="jouw-key"
)
```

⚠️ **LET OP**: Voor medische data alleen enterprise accounts met:
- Verwerkersovereenkomst
- EU hosting (westeurope endpoint)
- Zero data retention

## Tips voor beste resultaten

| Probleem | Oplossing |
|----------|-----------|
| Slechte handschrift-herkenning | Gebruik `--method handwriting` |
| Vage scans | Verhoog DPI: `--dpi 400` |
| Scheve pagina's | Beeldverbetering lost dit meestal op |
| Artsenhandschrift | Cloud OCR (Google/Azure) aanbevolen |
| Lage confidence (<70%) | Overweeg cloud OCR voor die pagina's |

## Output structuur

```python
result.combined_text      # Alle tekst samengevoegd
result.overall_confidence # Gemiddelde confidence (0-1)
result.pages              # Lijst met PageResult per pagina:
  - page_number
  - text
  - confidence  
  - has_handwriting
  - warnings
```

## Compliance checklist

- [ ] Anonimiseer VÓÓR cloud-verwerking
- [ ] Gebruik alleen EU-hosted cloud services
- [ ] Zorg voor verwerkersovereenkomst
- [ ] Log alle verwerkingsstappen (audit trail)
