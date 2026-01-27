"""
Kinetic PDF Processor - Streamlit App
======================================
Web interface voor medische dossierverwerking met OCR.

Start met: streamlit run app.py
"""

import streamlit as st
import tempfile
import os
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Kinetic PDF Processor",
    page_icon="📄",
    layout="wide"
)

# Import processor (met error handling)
try:
    from pdf_processor import PDFProcessor, post_process_medical_text
    PROCESSOR_AVAILABLE = True
except ImportError as e:
    PROCESSOR_AVAILABLE = False
    IMPORT_ERROR = str(e)


def check_dependencies():
    """Check of alle dependencies geïnstalleerd zijn"""
    missing = []
    
    try:
        import pdfplumber
    except ImportError:
        missing.append("pdfplumber")
    
    try:
        import pytesseract
    except ImportError:
        missing.append("pytesseract")
    
    try:
        from pdf2image import convert_from_path
    except ImportError:
        missing.append("pdf2image")
    
    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow")
    
    try:
        import cv2
    except ImportError:
        missing.append("opencv-python (optioneel)")
    
    return missing


def main():
    # Header
    st.title("📄 Kinetic PDF Processor")
    st.markdown("*Medische dossierverwerking met OCR en handschrift-herkenning*")
    
    # Check dependencies
    if not PROCESSOR_AVAILABLE:
        st.error(f"❌ PDF Processor kon niet geladen worden: {IMPORT_ERROR}")
        st.stop()
    
    missing_deps = check_dependencies()
    if missing_deps and "opencv-python" not in str(missing_deps):
        st.error(f"❌ Missende packages: {', '.join(missing_deps)}")
        st.code(f"pip install {' '.join(missing_deps)}", language="bash")
        st.stop()
    
    # Sidebar settings
    with st.sidebar:
        st.header("⚙️ Instellingen")
        
        method = st.selectbox(
            "Verwerkingsmethode",
            options=["auto", "digital", "ocr", "handwriting"],
            index=0,
            help="Auto detecteert automatisch het beste type"
        )
        
        dpi = st.slider(
            "DPI (kwaliteit)",
            min_value=150,
            max_value=600,
            value=300,
            step=50,
            help="Hoger = betere kwaliteit, maar langzamer"
        )
        
        enhance = st.checkbox(
            "Beeldverbetering",
            value=True,
            help="Verbetert OCR voor handgeschreven tekst"
        )
        
        lang = st.selectbox(
            "OCR Taal",
            options=["nld+eng", "nld", "eng", "deu+nld"],
            index=0
        )
        
        medical_postprocess = st.checkbox(
            "Medische post-processing",
            value=True,
            help="Corrigeert veelvoorkomende OCR-fouten in medische termen"
        )
        
        st.divider()
        st.markdown("### 📊 Legenda confidence")
        st.markdown("""
        - 🟢 **>80%** Uitstekend
        - 🟡 **60-80%** Acceptabel  
        - 🔴 **<60%** Controleer handmatig
        """)
    
    # Main content
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📤 Upload")
        
        uploaded_file = st.file_uploader(
            "Sleep een PDF hierheen of klik om te selecteren",
            type=["pdf"],
            help="Alleen PDF bestanden worden geaccepteerd"
        )
        
        if uploaded_file:
            st.success(f"✅ **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")
            
            # Process button
            if st.button("🚀 Verwerk PDF", type="primary", use_container_width=True):
                
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.getbuffer())
                    tmp_path = tmp.name
                
                try:
                    # Initialize processor
                    processor = PDFProcessor(
                        tesseract_lang=lang,
                        dpi=dpi,
                        enhance_images=enhance
                    )
                    
                    # Process with progress
                    with st.spinner("PDF wordt verwerkt..."):
                        force_method = None if method == "auto" else method
                        result = processor.process(tmp_path, force_method=force_method)
                    
                    # Store result in session state
                    st.session_state['result'] = result
                    st.session_state['filename'] = uploaded_file.name
                    
                    if medical_postprocess:
                        st.session_state['processed_text'] = post_process_medical_text(result.combined_text)
                    else:
                        st.session_state['processed_text'] = result.combined_text
                    
                finally:
                    # Cleanup temp file
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
    
    with col2:
        st.header("📋 Resultaat")
        
        if 'result' in st.session_state:
            result = st.session_state['result']
            processed_text = st.session_state['processed_text']
            
            # Metrics
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                st.metric("Pagina's", result.total_pages)
            
            with col_b:
                conf = result.overall_confidence
                if conf >= 0.8:
                    emoji = "🟢"
                elif conf >= 0.6:
                    emoji = "🟡"
                else:
                    emoji = "🔴"
                st.metric("Confidence", f"{emoji} {conf:.0%}")
            
            with col_c:
                st.metric("Methode", result.processing_method)
            
            # Errors/warnings
            if result.errors:
                for error in result.errors:
                    st.error(f"⚠️ {error}")
            
            # Page details (expandable)
            with st.expander("📄 Details per pagina"):
                for page in result.pages:
                    conf = page.confidence
                    emoji = "🟢" if conf >= 0.8 else "🟡" if conf >= 0.6 else "🔴"
                    hw = "✍️" if page.has_handwriting else ""
                    
                    st.markdown(f"**Pagina {page.page_number}:** {emoji} {conf:.0%} {hw}")
                    
                    if page.warnings:
                        for w in page.warnings:
                            st.caption(f"⚠️ {w}")
            
            # Text output
            st.text_area(
                "Geëxtraheerde tekst",
                processed_text,
                height=400,
                key="output_text"
            )
            
            # Download button
            st.download_button(
                label="⬇️ Download als TXT",
                data=processed_text,
                file_name=f"{Path(st.session_state['filename']).stem}_extracted.txt",
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.info("👈 Upload een PDF om te beginnen")
    
    # Footer
    st.divider()
    st.caption("Kinetic Medische Expertises | ⚠️ Gebruik alleen voor geanonimiseerde testdata")


if __name__ == "__main__":
    main()
