"""
Kinetic Dossier Processor - Streamlit App
==========================================
Complete workflow voor medische dossierverwerking:
1. Upload PDF of TXT
2. Tekst extractie (OCR indien nodig)
3. Automatische pseudonimisering
4. Download resultaat

Start met: streamlit run app.py
"""

import streamlit as st
import tempfile
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# Page config
st.set_page_config(
    page_title="Kinetic Dossier Processor",
    page_icon="🏥",
    layout="wide"
)

# Imports met error handling
IMPORTS_OK = True
IMPORT_ERRORS = []

try:
    from pseudonymizer import MedicalPseudonymizer, PseudonymizationResult
except ImportError as e:
    IMPORTS_OK = False
    IMPORT_ERRORS.append(f"pseudonymizer.py: {e}")

try:
    from pdf_processor import PDFProcessor, post_process_medical_text
    PDF_SUPPORT = True
except ImportError as e:
    PDF_SUPPORT = False
    IMPORT_ERRORS.append(f"pdf_processor.py (PDF support disabled): {e}")


def extract_text_from_pdf(file_path: str, method: str, dpi: int, enhance: bool, lang: str) -> tuple:
    """Extraheer tekst uit PDF"""
    if not PDF_SUPPORT:
        return "", 0, ["PDF ondersteuning niet beschikbaar"]
    
    processor = PDFProcessor(
        tesseract_lang=lang,
        dpi=dpi,
        enhance_images=enhance
    )
    
    force_method = None if method == "auto" else method
    result = processor.process(file_path, force_method=force_method)
    
    # Post-process voor medische tekst
    text = post_process_medical_text(result.combined_text)
    
    return text, result.overall_confidence, result.errors


def fix_ocr_encoding(text: str) -> str:
    """Fix veelvoorkomende OCR encoding fouten waar - als n wordt gelezen"""
    import re
    result = text
    
    # Fix datum patronen: 05n03n2025 -> 05-03-2025
    result = re.sub(r'(\d{2})n(\d{2})n(\d{4})', r'\1-\2-\3', result)
    result = re.sub(r'(\d{2})n(\d{2})n(\d{2})\b', r'\1-\2-\3', result)
    
    # Fix telefoon patronen
    result = re.sub(r'\b(06)n(\d{8})\b', r'\1-\2', result)
    result = re.sub(r'\b(06)n(\d{4})n(\d{4})\b', r'\1-\2-\3', result)
    result = re.sub(r'\b(06)n(\d{4})(\d{4})\b', r'\1-\2\3', result)
    
    # Fix polis/schade nummers
    result = re.sub(r'\b([A-Z]{2,4})n(\d{4})n(\d{2})n(\d+)\b', r'\1-\2-\3-\4', result)
    result = re.sub(r'\b([A-Z]{2,4})n(\d{4})n(\d+)\b', r'\1-\2-\3', result)
    
    # Fix case IDs: TLnCASEn0192 -> TL-CASE-0192
    result = re.sub(r'\b([A-Z]{2,4})n([A-Z]+)n(\d+)\b', r'\1-\2-\3', result)
    
    return result


def extract_text_from_txt(file_content: bytes) -> str:
    """Extraheer tekst uit TXT bestand"""
    # Probeer verschillende encodings
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            return file_content.decode(encoding)
        except UnicodeDecodeError:
            continue
    
    # Fallback met error handling
    return file_content.decode('utf-8', errors='replace')


def parse_date_input(date_str: str) -> Optional[datetime]:
    """Parse datum input van gebruiker"""
    if not date_str:
        return None
        
    formats = ['%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%y']
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    return None


def main():
    # Header
    st.title("🏥 Kinetic Dossier Processor")
    st.markdown("*Upload → Extractie → Pseudonimisering*")
    
    # Check imports
    if not IMPORTS_OK:
        st.error("❌ Kritieke imports ontbreken:")
        for err in IMPORT_ERRORS:
            st.code(err)
        st.info("Zorg dat `pseudonymizer.py` en `pdf_processor.py` in dezelfde map staan als `app.py`")
        st.stop()
    
    if not PDF_SUPPORT:
        st.warning("⚠️ PDF ondersteuning uitgeschakeld (dependencies missen). Alleen TXT bestanden werken.")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Instellingen")
        
        st.subheader("📅 Ongevalsdatum")
        incident_date_str = st.text_input(
            "Datum (dd-mm-jjjj)",
            placeholder="bijv. 02-08-2012",
            help="Alle datums worden relatief t.o.v. deze datum weergegeven (T-30, T+0, T+90)"
        )
        incident_date = parse_date_input(incident_date_str)
        
        if incident_date_str and not incident_date:
            st.error("Ongeldig datumformaat")
        elif incident_date:
            st.success(f"✓ {incident_date.strftime('%d-%m-%Y')}")
        
        st.divider()
        
        if PDF_SUPPORT:
            st.subheader("📄 PDF Instellingen")
            
            pdf_method = st.selectbox(
                "OCR Methode",
                options=["auto", "digital", "ocr", "handwriting"],
                index=0,
                help="Auto detecteert automatisch"
            )
            
            pdf_dpi = st.slider(
                "DPI",
                min_value=150,
                max_value=600,
                value=300,
                step=50,
                help="Hoger = beter voor handschrift"
            )
            
            pdf_enhance = st.checkbox(
                "Beeldverbetering",
                value=True
            )
            
            pdf_lang = st.selectbox(
                "OCR Taal",
                options=["nld+eng", "nld", "eng"],
                index=0
            )
        
        st.divider()
        
        st.subheader("📊 Legenda")
        st.markdown("""
        **Pseudoniemen:**
        - `[PERSOON_1]` = Naam
        - `[BSN]` = Burgerservicenummer
        - `[ADRES_1]` = Adres
        - `[TELEFOON]` = Telefoonnummer
        - `[GEBOORTEDATUM]` = Geboortedatum
        - `[T+30]` = 30 dagen na ongeval
        - `[T-10]` = 10 dagen vóór ongeval
        """)
    
    # Main content
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📤 Upload Bestand")
        
        # File types bepalen
        allowed_types = ["txt"]
        if PDF_SUPPORT:
            allowed_types.append("pdf")
        
        uploaded_file = st.file_uploader(
            f"Sleep een bestand hierheen ({', '.join(allowed_types).upper()})",
            type=allowed_types,
            help="PDF bestanden worden automatisch verwerkt met OCR indien nodig"
        )
        
        if uploaded_file:
            file_ext = Path(uploaded_file.name).suffix.lower()
            file_size = uploaded_file.size / 1024  # KB
            
            st.success(f"✅ **{uploaded_file.name}** ({file_size:.1f} KB)")
            
            # Process button
            if st.button("🚀 Verwerk & Pseudonimiseer", type="primary", use_container_width=True):
                
                extracted_text = ""
                confidence = 1.0
                extraction_errors = []
                
                # === STAP 1: TEKST EXTRACTIE ===
                with st.status("Bezig met verwerken...", expanded=True) as status:
                    
                    if file_ext == ".pdf":
                        st.write("📄 PDF wordt verwerkt met OCR...")
                        
                        # Save temp file
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            tmp.write(uploaded_file.getbuffer())
                            tmp_path = tmp.name
                        
                        try:
                            extracted_text, confidence, extraction_errors = extract_text_from_pdf(
                                tmp_path, 
                                pdf_method, 
                                pdf_dpi, 
                                pdf_enhance, 
                                pdf_lang
                            )
                        finally:
                            if os.path.exists(tmp_path):
                                os.unlink(tmp_path)
                                
                        st.write(f"✓ Tekst geëxtraheerd (confidence: {confidence:.0%})")
                        
                    else:  # TXT
                        st.write("📝 Tekstbestand wordt gelezen...")
                        extracted_text = extract_text_from_txt(uploaded_file.getvalue())
                        # Fix encoding problemen
                        extracted_text = fix_ocr_encoding(extracted_text)
                        st.write("✓ Tekst geladen")
                    
                    # === STAP 2: PSEUDONIMISERING ===
                    st.write("🔒 Pseudonimisering wordt uitgevoerd...")
                    
                    pseudonymizer = MedicalPseudonymizer(incident_date=incident_date)
                    result = pseudonymizer.pseudonymize(extracted_text)
                    
                    st.write(f"✓ {sum(result.statistics.values())} items gepseudonimiseerd")
                    
                    status.update(label="✅ Verwerking voltooid!", state="complete")
                
                # Store results in session
                st.session_state['result'] = result
                st.session_state['confidence'] = confidence
                st.session_state['extraction_errors'] = extraction_errors
                st.session_state['filename'] = uploaded_file.name
                st.session_state['original_text'] = extracted_text
    
    with col2:
        st.header("📋 Resultaat")
        
        if 'result' in st.session_state:
            result: PseudonymizationResult = st.session_state['result']
            confidence = st.session_state['confidence']
            extraction_errors = st.session_state['extraction_errors']
            
            # Metrics
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                total_replacements = sum(result.statistics.values())
                st.metric("Vervangingen", total_replacements)
            
            with col_b:
                if confidence >= 0.8:
                    emoji = "🟢"
                elif confidence >= 0.6:
                    emoji = "🟡"
                else:
                    emoji = "🔴"
                st.metric("OCR Confidence", f"{emoji} {confidence:.0%}")
            
            with col_c:
                persons = result.statistics.get('names', 0)
                st.metric("Personen", persons)
            
            # Errors/warnings
            if extraction_errors:
                for err in extraction_errors:
                    st.error(f"⚠️ {err}")
            
            if result.warnings:
                for w in result.warnings:
                    st.warning(f"⚠️ {w}")
            
            # Incident date info
            if result.incident_date:
                st.info(f"📅 Ongevalsdatum: {result.incident_date.strftime('%d-%m-%Y')} (T+0)")
            
            # Statistics expander
            with st.expander("📊 Statistieken per categorie"):
                if result.statistics:
                    for category, count in sorted(result.statistics.items()):
                        label = {
                            'names': '👤 Namen',
                            'dates': '📅 Datums',
                            'bsn': '🔢 BSN',
                            'addresses': '🏠 Adressen',
                            'postal_codes': '📮 Postcodes',
                            'phone': '📞 Telefoon',
                            'email': '📧 Email',
                            'birth_dates': '🎂 Geboortedatums',
                            'case_numbers': '📁 Zaaknummers'
                        }.get(category, category)
                        st.write(f"{label}: **{count}**")
                else:
                    st.write("Geen PII gedetecteerd")
            
            # Name mapping expander
            with st.expander("🔄 Naam mapping (voor audit)"):
                if result.replacements:
                    for original, pseudo in result.replacements.items():
                        st.code(f"{original} → {pseudo}")
                else:
                    st.write("Geen namen vervangen")
            
            # Tabs voor original vs pseudonymized
            tab1, tab2 = st.tabs(["🔒 Gepseudonimiseerd", "📝 Origineel (alleen voor controle)"])
            
            with tab1:
                st.text_area(
                    "Gepseudonimiseerde tekst",
                    result.pseudonymized_text,
                    height=400,
                    key="output_pseudo"
                )
                
                # Download button
                st.download_button(
                    label="⬇️ Download Gepseudonimiseerd",
                    data=result.pseudonymized_text,
                    file_name=f"{Path(st.session_state['filename']).stem}_pseudoniem.txt",
                    mime="text/plain",
                    use_container_width=True,
                    type="primary"
                )
            
            with tab2:
                st.warning("⚠️ Dit bevat nog originele persoonsgegevens!")
                st.text_area(
                    "Originele tekst",
                    st.session_state['original_text'],
                    height=400,
                    key="output_original"
                )
        else:
            st.info("👈 Upload een bestand om te beginnen")
    
    # Footer
    st.divider()
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.caption("Kinetic Medische Expertises")
    with col_f2:
        st.caption("⚠️ Verwerk géén echte patiëntdata zonder verwerkersovereenkomst")


if __name__ == "__main__":
    main()
