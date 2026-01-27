#!/usr/bin/env python3
"""
Kinetic PDF Processor - Medische Dossierverwerking
===================================================
Verbeterde PDF-verwerking met ondersteuning voor:
- Digitale PDFs (direct tekst extractie)
- Gescande documenten (OCR)
- Handgeschreven tekst (geoptimaliseerde OCR + cloud opties)

Auteur: Kinetic Medische Expertises
Versie: 2.0
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Tuple
from enum import Enum
import json
import re


class DocumentType(Enum):
    """Type document detectie"""
    DIGITAL = "digitaal"           # Tekst direct extraheerbaar
    SCANNED = "gescand"            # OCR nodig
    HANDWRITTEN = "handgeschreven" # Speciale OCR configuratie nodig
    MIXED = "gemengd"              # Combinatie


@dataclass
class PageResult:
    """Resultaat per pagina"""
    page_number: int
    text: str
    document_type: DocumentType
    confidence: float
    has_handwriting: bool
    warnings: List[str]


@dataclass
class ProcessingResult:
    """Totaal resultaat van verwerking"""
    filepath: str
    total_pages: int
    pages: List[PageResult]
    combined_text: str
    overall_confidence: float
    processing_method: str
    errors: List[str]


class PDFProcessor:
    """
    Hoofdklasse voor PDF-verwerking met handgeschreven tekst ondersteuning.
    
    Workflow:
    1. Detecteer document type (digitaal/gescand/handgeschreven)
    2. Kies optimale extractiemethode
    3. Pre-process afbeeldingen voor betere OCR
    4. Extraheer tekst met aangepaste configuratie
    5. Post-process en kwaliteitscontrole
    """
    
    def __init__(
        self,
        tesseract_lang: str = "nld+eng",
        use_cloud_ocr: bool = False,
        cloud_provider: Optional[str] = None,
        dpi: int = 300,
        enhance_images: bool = True
    ):
        """
        Args:
            tesseract_lang: Talen voor Tesseract OCR (default: Nederlands + Engels)
            use_cloud_ocr: Gebruik cloud OCR voor handgeschreven tekst
            cloud_provider: 'google' of 'azure' (alleen als use_cloud_ocr=True)
            dpi: DPI voor PDF naar image conversie
            enhance_images: Pas beeldverbetering toe voor betere OCR
        """
        self.tesseract_lang = tesseract_lang
        self.use_cloud_ocr = use_cloud_ocr
        self.cloud_provider = cloud_provider
        self.dpi = dpi
        self.enhance_images = enhance_images
        
        # Lazy imports - alleen laden wat nodig is
        self._pdfplumber = None
        self._pytesseract = None
        self._cv2 = None
        self._Image = None
        self._convert_from_path = None
        
    def _import_dependencies(self):
        """Import benodigde libraries on-demand"""
        global pdfplumber, pytesseract, cv2, Image, convert_from_path, np
        
        try:
            import pdfplumber
            self._pdfplumber = pdfplumber
        except ImportError:
            raise ImportError("Installeer pdfplumber: pip install pdfplumber")
            
        try:
            import pytesseract
            self._pytesseract = pytesseract
        except ImportError:
            raise ImportError("Installeer pytesseract: pip install pytesseract")
            
        try:
            from pdf2image import convert_from_path
            self._convert_from_path = convert_from_path
        except ImportError:
            raise ImportError("Installeer pdf2image: pip install pdf2image")
            
        try:
            from PIL import Image
            self._Image = Image
        except ImportError:
            raise ImportError("Installeer Pillow: pip install Pillow")
            
        try:
            import cv2
            import numpy as np
            self._cv2 = cv2
        except ImportError:
            print("Waarschuwing: OpenCV niet geïnstalleerd. Beeldverbetering uitgeschakeld.")
            print("Installeer met: pip install opencv-python")
            self.enhance_images = False
            
    def detect_document_type(self, pdf_path: str) -> Tuple[DocumentType, float]:
        """
        Detecteer of document digitaal, gescand, of handgeschreven is.
        
        Returns:
            Tuple van (DocumentType, confidence score)
        """
        self._import_dependencies()
        
        text_density_scores = []
        
        with self._pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:min(3, len(pdf.pages))]:  # Check eerste 3 pagina's
                text = page.extract_text() or ""
                chars = page.chars if hasattr(page, 'chars') else []
                
                # Heuristics voor detectie
                has_text_layer = len(text.strip()) > 50
                has_char_objects = len(chars) > 20
                
                if has_text_layer and has_char_objects:
                    text_density_scores.append(1.0)  # Digitaal
                elif has_text_layer:
                    text_density_scores.append(0.7)  # Mogelijk OCR-laag aanwezig
                else:
                    text_density_scores.append(0.0)  # Gescand zonder OCR
                    
        avg_score = sum(text_density_scores) / len(text_density_scores) if text_density_scores else 0
        
        if avg_score >= 0.8:
            return DocumentType.DIGITAL, avg_score
        elif avg_score >= 0.3:
            return DocumentType.MIXED, avg_score
        else:
            return DocumentType.SCANNED, 1 - avg_score
            
    def preprocess_image_for_ocr(self, image) -> 'Image':
        """
        Verbeter afbeelding voor betere OCR resultaten.
        Essentieel voor handgeschreven tekst.
        """
        if not self.enhance_images or self._cv2 is None:
            return image
            
        import numpy as np
        
        # Convert PIL Image naar OpenCV formaat
        img_array = np.array(image)
        
        # Converteer naar grayscale
        if len(img_array.shape) == 3:
            gray = self._cv2.cvtColor(img_array, self._cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
            
        # 1. Denoise - verwijder ruis
        denoised = self._cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # 2. Contrast verbetering met CLAHE
        clahe = self._cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast_enhanced = clahe.apply(denoised)
        
        # 3. Adaptive thresholding - beter voor handgeschreven tekst
        # Gebruik Gaussian voor vloeiendere resultaten bij handschrift
        binary = self._cv2.adaptiveThreshold(
            contrast_enhanced,
            255,
            self._cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            self._cv2.THRESH_BINARY,
            15,  # Block size - groter voor handschrift
            8    # C constant
        )
        
        # 4. Morphological operations - verbind gebroken lijnen in handschrift
        kernel = np.ones((2, 2), np.uint8)
        processed = self._cv2.morphologyEx(binary, self._cv2.MORPH_CLOSE, kernel)
        
        # 5. Deskew - corrigeer scheve scans
        processed = self._deskew_image(processed)
        
        # Convert terug naar PIL Image
        return self._Image.fromarray(processed)
        
    def _deskew_image(self, image) -> 'np.ndarray':
        """Corrigeer scheefstand van gescande documenten"""
        import numpy as np
        
        # Vind hoek van tekst
        coords = np.column_stack(np.where(image < 128))  # Donkere pixels
        
        if len(coords) < 100:
            return image
            
        try:
            # Gebruik minAreaRect voor hoekdetectie
            rect = self._cv2.minAreaRect(coords)
            angle = rect[-1]
            
            # Normaliseer hoek
            if angle < -45:
                angle = 90 + angle
            elif angle > 45:
                angle = angle - 90
                
            # Alleen corrigeren als hoek significant is
            if abs(angle) > 0.5:
                (h, w) = image.shape[:2]
                center = (w // 2, h // 2)
                M = self._cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = self._cv2.warpAffine(
                    image, M, (w, h),
                    flags=self._cv2.INTER_CUBIC,
                    borderMode=self._cv2.BORDER_REPLICATE
                )
                return rotated
        except:
            pass
            
        return image
        
    def get_tesseract_config(self, for_handwriting: bool = False) -> str:
        """
        Genereer optimale Tesseract configuratie.
        
        Args:
            for_handwriting: True voor handgeschreven tekst configuratie
        """
        config_parts = []
        
        if for_handwriting:
            # Configuratie geoptimaliseerd voor handschrift
            config_parts.extend([
                "--psm 6",           # Assume uniform block of text
                "--oem 1",           # LSTM only - beter voor variabel handschrift
                "-c preserve_interword_spaces=1",
                "-c textord_heavy_nr=1",  # Meer tolerant voor noise
                "-c edges_max_children_per_outline=40",  # Handschrift heeft complexere contouren
            ])
        else:
            # Standaard configuratie voor geprinte tekst
            config_parts.extend([
                "--psm 3",           # Fully automatic page segmentation
                "--oem 3",           # Default OCR Engine mode
            ])
            
        return " ".join(config_parts)
        
    def detect_handwriting_regions(self, image) -> List[dict]:
        """
        Detecteer regio's met handgeschreven tekst.
        Nuttig voor gemengde documenten.
        
        Returns:
            Lijst met bounding boxes van handgeschreven regio's
        """
        if self._cv2 is None:
            return []
            
        import numpy as np
        
        img_array = np.array(image)
        if len(img_array.shape) == 3:
            gray = self._cv2.cvtColor(img_array, self._cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
            
        # Detecteer variatie in lijndikte (handschrift heeft meer variatie)
        edges = self._cv2.Canny(gray, 50, 150)
        
        # Find contours
        contours, _ = self._cv2.findContours(
            edges, self._cv2.RETR_EXTERNAL, self._cv2.CHAIN_APPROX_SIMPLE
        )
        
        handwriting_regions = []
        for contour in contours:
            area = self._cv2.contourArea(contour)
            if area > 1000:  # Filter kleine ruis
                x, y, w, h = self._cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                
                # Handschrift heeft vaak meer variatie in aspect ratio
                if 0.1 < aspect_ratio < 10:
                    handwriting_regions.append({
                        'x': x, 'y': y, 'w': w, 'h': h,
                        'area': area
                    })
                    
        return handwriting_regions
        
    def extract_text_from_page(
        self,
        page_image,
        page_number: int,
        force_handwriting_mode: bool = False
    ) -> PageResult:
        """
        Extraheer tekst van een enkele pagina met optimale methode.
        """
        warnings = []
        
        # Preprocess voor betere OCR
        if self.enhance_images:
            processed_image = self.preprocess_image_for_ocr(page_image)
        else:
            processed_image = page_image
            
        # Detecteer handgeschreven regio's
        handwriting_regions = self.detect_handwriting_regions(page_image)
        has_handwriting = len(handwriting_regions) > 0 or force_handwriting_mode
        
        if has_handwriting:
            warnings.append("Handgeschreven tekst gedetecteerd - resultaat kan minder nauwkeurig zijn")
            
        # Kies configuratie
        config = self.get_tesseract_config(for_handwriting=has_handwriting)
        
        # OCR uitvoeren
        try:
            # Haal ook confidence data op
            data = self._pytesseract.image_to_data(
                processed_image,
                lang=self.tesseract_lang,
                config=config,
                output_type=self._pytesseract.Output.DICT
            )
            
            # Bereken gemiddelde confidence
            confidences = [
                int(c) for c in data['conf'] 
                if str(c).isdigit() and int(c) > 0
            ]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Extraheer tekst
            text = self._pytesseract.image_to_string(
                processed_image,
                lang=self.tesseract_lang,
                config=config
            )
            
            # Waarschuwing bij lage confidence
            if avg_confidence < 60:
                warnings.append(f"Lage OCR confidence: {avg_confidence:.0f}%")
                
        except Exception as e:
            text = ""
            avg_confidence = 0
            warnings.append(f"OCR fout: {str(e)}")
            
        return PageResult(
            page_number=page_number,
            text=text.strip(),
            document_type=DocumentType.HANDWRITTEN if has_handwriting else DocumentType.SCANNED,
            confidence=avg_confidence / 100,
            has_handwriting=has_handwriting,
            warnings=warnings
        )
        
    def extract_text_digital(self, pdf_path: str) -> ProcessingResult:
        """Extract tekst van digitale PDF (geen OCR nodig)"""
        self._import_dependencies()
        
        pages = []
        all_text = []
        
        with self._pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                
                page_result = PageResult(
                    page_number=i + 1,
                    text=text,
                    document_type=DocumentType.DIGITAL,
                    confidence=1.0,  # Digitale tekst is 100% accuraat
                    has_handwriting=False,
                    warnings=[]
                )
                pages.append(page_result)
                all_text.append(text)
                
        return ProcessingResult(
            filepath=pdf_path,
            total_pages=len(pages),
            pages=pages,
            combined_text="\n\n".join(all_text),
            overall_confidence=1.0,
            processing_method="digital_extraction",
            errors=[]
        )
        
    def extract_text_ocr(
        self,
        pdf_path: str,
        force_handwriting_mode: bool = False
    ) -> ProcessingResult:
        """Extract tekst met OCR (voor gescande documenten)"""
        self._import_dependencies()
        
        pages = []
        all_text = []
        errors = []
        
        try:
            # Converteer PDF naar afbeeldingen
            print(f"Converteren PDF naar afbeeldingen ({self.dpi} DPI)...")
            images = self._convert_from_path(pdf_path, dpi=self.dpi)
            
            for i, image in enumerate(images):
                print(f"  Verwerken pagina {i+1}/{len(images)}...", end=" ")
                
                page_result = self.extract_text_from_page(
                    image, 
                    i + 1,
                    force_handwriting_mode=force_handwriting_mode
                )
                pages.append(page_result)
                all_text.append(page_result.text)
                
                status = "✓" if page_result.confidence > 0.7 else "⚠"
                print(f"{status} (confidence: {page_result.confidence:.0%})")
                
        except Exception as e:
            errors.append(f"PDF conversie fout: {str(e)}")
            
        # Bereken overall confidence
        confidences = [p.confidence for p in pages if p.confidence > 0]
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return ProcessingResult(
            filepath=pdf_path,
            total_pages=len(pages),
            pages=pages,
            combined_text="\n\n".join(all_text),
            overall_confidence=overall_confidence,
            processing_method="ocr_handwriting" if force_handwriting_mode else "ocr_standard",
            errors=errors
        )
        
    def process(
        self,
        pdf_path: str,
        force_method: Optional[str] = None
    ) -> ProcessingResult:
        """
        Hoofdmethode: verwerk een PDF met automatische detectie.
        
        Args:
            pdf_path: Pad naar PDF bestand
            force_method: 'digital', 'ocr', of 'handwriting' (optioneel)
            
        Returns:
            ProcessingResult met alle geëxtraheerde tekst
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF niet gevonden: {pdf_path}")
            
        self._import_dependencies()
        
        print(f"\n{'='*60}")
        print(f"Kinetic PDF Processor")
        print(f"{'='*60}")
        print(f"Bestand: {pdf_path}")
        
        # Detecteer document type
        if force_method:
            print(f"Methode: {force_method} (geforceerd)")
        else:
            doc_type, confidence = self.detect_document_type(pdf_path)
            print(f"Gedetecteerd type: {doc_type.value} (confidence: {confidence:.0%})")
            
            if doc_type == DocumentType.DIGITAL:
                force_method = "digital"
            elif doc_type == DocumentType.HANDWRITTEN:
                force_method = "handwriting"
            else:
                force_method = "ocr"
                
        print(f"{'='*60}\n")
        
        # Verwerk met juiste methode
        if force_method == "digital":
            return self.extract_text_digital(pdf_path)
        elif force_method == "handwriting":
            return self.extract_text_ocr(pdf_path, force_handwriting_mode=True)
        else:
            return self.extract_text_ocr(pdf_path, force_handwriting_mode=False)
            
    def process_batch(
        self,
        pdf_paths: List[str],
        output_dir: str
    ) -> List[ProcessingResult]:
        """Verwerk meerdere PDFs in batch"""
        results = []
        os.makedirs(output_dir, exist_ok=True)
        
        for i, pdf_path in enumerate(pdf_paths):
            print(f"\n[{i+1}/{len(pdf_paths)}] ", end="")
            
            try:
                result = self.process(pdf_path)
                results.append(result)
                
                # Sla resultaat op
                output_file = os.path.join(
                    output_dir,
                    Path(pdf_path).stem + "_extracted.txt"
                )
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result.combined_text)
                    
            except Exception as e:
                print(f"FOUT: {e}")
                results.append(ProcessingResult(
                    filepath=pdf_path,
                    total_pages=0,
                    pages=[],
                    combined_text="",
                    overall_confidence=0,
                    processing_method="error",
                    errors=[str(e)]
                ))
                
        return results


class CloudOCRHandler:
    """
    Handler voor cloud-gebaseerde OCR services.
    Aanbevolen voor handgeschreven tekst - significant betere resultaten.
    
    Let op: Vereist enterprise accounts met DPA voor medische data!
    """
    
    @staticmethod
    def extract_with_google_vision(image_path: str, credentials_path: str) -> str:
        """
        Google Cloud Vision API - uitstekend voor handschrift.
        
        Vereist:
        - Google Cloud account met Vision API enabled
        - Service account credentials JSON
        - Verwerkersovereenkomst voor medische data
        """
        try:
            from google.cloud import vision
            import io
            
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
            client = vision.ImageAnnotatorClient()
            
            with io.open(image_path, 'rb') as image_file:
                content = image_file.read()
                
            image = vision.Image(content=content)
            
            # DOCUMENT_TEXT_DETECTION is beter voor handschrift dan TEXT_DETECTION
            response = client.document_text_detection(image=image)
            
            if response.error.message:
                raise Exception(response.error.message)
                
            return response.full_text_annotation.text
            
        except ImportError:
            raise ImportError(
                "Google Cloud Vision niet geïnstalleerd.\n"
                "Installeer met: pip install google-cloud-vision"
            )
            
    @staticmethod
    def extract_with_azure_document_intelligence(
        image_path: str,
        endpoint: str,
        api_key: str
    ) -> str:
        """
        Azure Document Intelligence (Form Recognizer).
        Zeer geschikt voor medische documenten en handschrift.
        
        Vereist:
        - Azure account met Document Intelligence resource
        - EU regio voor AVG compliance (bv. westeurope)
        """
        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
            
            client = DocumentIntelligenceClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(api_key)
            )
            
            with open(image_path, "rb") as f:
                poller = client.begin_analyze_document(
                    "prebuilt-read",  # Beste model voor handschrift
                    f
                )
                
            result = poller.result()
            
            text_parts = []
            for page in result.pages:
                for line in page.lines:
                    text_parts.append(line.content)
                    
            return "\n".join(text_parts)
            
        except ImportError:
            raise ImportError(
                "Azure Document Intelligence niet geïnstalleerd.\n"
                "Installeer met: pip install azure-ai-documentintelligence"
            )


def post_process_medical_text(text: str) -> str:
    """
    Post-processing specifiek voor medische teksten.
    Corrigeert veelvoorkomende OCR fouten in medische terminologie.
    """
    corrections = {
        # Veelvoorkomende OCR fouten in medisch Nederlands
        r'\bpatient\b': 'patiënt',
        r'\bmedlcatie\b': 'medicatie',
        r'\bdiagnos[e|t]iek\b': 'diagnostiek',
        r'\borthoped\b': 'orthopeed',
        r'\bneurolog\b': 'neuroloog',
        r'\bfysiotherap\b': 'fysiotherap',
        r'\bchronlsch\b': 'chronisch',
        r'\bklachlen\b': 'klachten',
        r'\bbehandel1ng\b': 'behandeling',
        r'\bonderzoek\b': 'onderzoek',
        r'\brapportage\b': 'rapportage',
        
        # Afkortingen normalisatie
        r'\bp\.?o\b': 'p.o.',   # per os
        r'\bi\.?v\b': 'i.v.',   # intraveneus
        r'\bs\.?c\b': 's.c.',   # subcutaan
        
        # Datumformaat normalisatie
        r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})': r'\1-\2-\3',
    }
    
    processed = text
    for pattern, replacement in corrections.items():
        processed = re.sub(pattern, replacement, processed, flags=re.IGNORECASE)
        
    return processed


# ============================================================
# INSTALLATIE INSTRUCTIES
# ============================================================
INSTALL_INSTRUCTIONS = """
=== INSTALLATIE INSTRUCTIES ===

1. Basis dependencies:
   pip install pdfplumber pytesseract pdf2image Pillow

2. Voor beeldverbetering (aanbevolen):
   pip install opencv-python numpy

3. Tesseract OCR engine installeren:
   
   macOS:
   brew install tesseract tesseract-lang
   
   Ubuntu/Debian:
   sudo apt-get install tesseract-ocr tesseract-ocr-nld
   
   Windows:
   Download van: https://github.com/UB-Mannheim/tesseract/wiki

4. Poppler (voor pdf2image):
   
   macOS:
   brew install poppler
   
   Ubuntu/Debian:
   sudo apt-get install poppler-utils
   
   Windows:
   Download van: https://github.com/osber/poppler-windows

5. (Optioneel) Cloud OCR voor handschrift:
   
   Google Cloud Vision:
   pip install google-cloud-vision
   
   Azure Document Intelligence:
   pip install azure-ai-documentintelligence

=== LET OP VOOR MEDISCHE DATA ===
- Gebruik ALLEEN enterprise cloud services met verwerkersovereenkomst
- Anonimiseer data VOOR cloud-verwerking
- Gebruik EU-hosted endpoints
"""


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Kinetic PDF Processor - Medische dossierverwerking met OCR"
    )
    parser.add_argument("pdf_path", help="Pad naar PDF bestand")
    parser.add_argument(
        "--method", 
        choices=["auto", "digital", "ocr", "handwriting"],
        default="auto",
        help="Verwerkingsmethode (default: auto)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output bestand voor geëxtraheerde tekst"
    )
    parser.add_argument(
        "--lang",
        default="nld+eng",
        help="OCR talen (default: nld+eng)"
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="DPI voor PDF conversie (default: 300)"
    )
    parser.add_argument(
        "--no-enhance",
        action="store_true",
        help="Schakel beeldverbetering uit"
    )
    parser.add_argument(
        "--install-help",
        action="store_true",
        help="Toon installatie instructies"
    )
    
    args = parser.parse_args()
    
    if args.install_help:
        print(INSTALL_INSTRUCTIONS)
        sys.exit(0)
        
    # Initialiseer processor
    processor = PDFProcessor(
        tesseract_lang=args.lang,
        dpi=args.dpi,
        enhance_images=not args.no_enhance
    )
    
    # Verwerk PDF
    method = None if args.method == "auto" else args.method
    result = processor.process(args.pdf_path, force_method=method)
    
    # Toon resultaat
    print(f"\n{'='*60}")
    print("RESULTAAT")
    print(f"{'='*60}")
    print(f"Totaal pagina's: {result.total_pages}")
    print(f"Overall confidence: {result.overall_confidence:.0%}")
    print(f"Methode: {result.processing_method}")
    
    if result.errors:
        print(f"\nFouten:")
        for error in result.errors:
            print(f"  - {error}")
            
    # Sla op indien gewenst
    if args.output:
        # Post-process voor medische tekst
        processed_text = post_process_medical_text(result.combined_text)
        
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(processed_text)
        print(f"\nOpgeslagen naar: {args.output}")
    else:
        print(f"\n--- Geëxtraheerde tekst (eerste 2000 tekens) ---\n")
        print(result.combined_text[:2000])
        if len(result.combined_text) > 2000:
            print(f"\n... ({len(result.combined_text) - 2000} tekens weggelaten)")
