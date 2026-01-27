"""
Kinetic Medische Expertises - Pseudonimiseringstool
Web-interface voor Privacy-by-Design verwerking van medische dossiers.

Deploy op Streamlit Cloud: https://streamlit.io/cloud
"""

import streamlit as st
import re
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import io


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Kinetic Pseudonimisering",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# STYLING
# =============================================================================

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A5F;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-top: 0;
    }
    .stat-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
    }
    .stat-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #28a745;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# CONFIGURATIE & DATA
# =============================================================================

VOORNAMEN = {
    "jan", "piet", "klaas", "hendrik", "johannes", "willem", "cornelis", "peter",
    "johan", "gerrit", "thomas", "dennis", "mark", "michael", "robert", "richard",
    "marcel", "erik", "jeroen", "bas", "tom", "tim", "kevin", "stefan", "marco",
    "frank", "martin", "patrick", "ronald", "raymond", "henk", "dirk", "bert",
    "hans", "fred", "paul", "leon", "sander", "rick", "nick", "max", "lucas",
    "daan", "sem", "finn", "liam", "noah", "jesse", "jayden", "ruben", "lars",
    "maria", "anna", "johanna", "elisabeth", "cornelia", "wilhelmina", "petronella",
    "linda", "sandra", "monique", "diana", "wendy", "patricia", "jessica", "melissa",
    "angela", "nicole", "mandy", "kim", "anouk", "lisa", "eva", "julia", "emma",
    "sophie", "lotte", "fleur", "iris", "anne", "maud", "sanne", "laura", "sarah",
    "marloes", "marieke", "esther", "ingrid", "annemarie", "els", "greet", "truus",
}

ACHTERNAMEN = {
    "de jong", "jansen", "de vries", "van den berg", "van dijk", "bakker", "janssen",
    "visser", "smit", "meijer", "de boer", "mulder", "de groot", "bos", "vos",
    "peters", "hendriks", "van leeuwen", "dekker", "brouwer", "de wit", "dijkstra",
    "smits", "de graaf", "van der meer", "van der linden", "kok", "jacobs", "de haan",
    "vermeer", "van den heuvel", "van der heijden", "dijkman", "schouten", "van dam",
    "van der wal", "prins", "zwart", "postma", "van der veen", "jansma", "kuiper",
    "peeters", "claes", "wouters", "goossens", "maes", "willems",
}

ZIEKENHUIZEN = {
    "amsterdam umc", "erasmus mc", "lumc", "radboudumc", "umcg", "umcu", "mumc+",
    "vumc", "amc", "academisch medisch centrum", "antonius ziekenhuis", "bernhoven",
    "bravis ziekenhuis", "catharina ziekenhuis", "deventer ziekenhuis", "diakonessenhuis",
    "elkerliek ziekenhuis", "flevoziekenhuis", "gelre ziekenhuizen", "groene hart ziekenhuis",
    "haga ziekenhuis", "ikazia ziekenhuis", "isala", "jeroen bosch ziekenhuis",
    "maasstad ziekenhuis", "martini ziekenhuis", "maxima medisch centrum",
    "meander medisch centrum", "medisch centrum leeuwarden", "olvg", "reinier de graaf",
    "rijnstate", "tergooi", "viecuri", "zaans medisch centrum", "zuyderland",
    "amphia ziekenhuis", "albert schweitzer ziekenhuis", "reade", "roessingh",
    "sint maartenskliniek", "de hoogstraat", "heliomare", "klimmendaal",
}

STEDEN = {
    "amsterdam", "rotterdam", "den haag", "'s-gravenhage", "utrecht", "eindhoven",
    "groningen", "tilburg", "almere", "breda", "nijmegen", "enschede", "haarlem",
    "arnhem", "zaanstad", "amersfoort", "apeldoorn", "hoofddorp", "maastricht",
    "leiden", "dordrecht", "zoetermeer", "zwolle", "deventer", "delft", "alkmaar",
    "heerlen", "venlo", "leeuwarden", "hilversum", "oss", "bonaire", "curaçao",
    "aruba", "sint maarten", "kralendijk", "willemstad", "oranjestad",
}


# =============================================================================
# PII PATTERNS
# =============================================================================

class PIIPatterns:
    BSN = re.compile(r'\b(\d{9})\b')
    IBAN = re.compile(r'\b(NL\d{2}[A-Z]{4}\d{10})\b', re.IGNORECASE)
    TELEFOON = re.compile(r'\b((?:0|\+31|0031)[\s.-]?(?:[1-9]\d{1,2})[\s.-]?(?:\d{2,3}[\s.-]?){2,3}\d{2})\b')
    MOBIEL = re.compile(r'\b((?:0|\+31|0031)[\s.-]?6[\s.-]?(?:\d{2}[\s.-]?){3}\d{2})\b')
    EMAIL = re.compile(r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b')
    POSTCODE = re.compile(r'\b(\d{4}\s?[A-Z]{2})\b')
    
    DATUM_TEKST = re.compile(
        r'\b(\d{1,2})\s+(januari|februari|maart|april|mei|juni|juli|augustus|'
        r'september|oktober|november|december)\s+(\d{4})\b',
        re.IGNORECASE
    )
    
    DATUM_DMY = re.compile(
        r'\b(\d{1,2})[-/.\s](\d{1,2}|'
        r'januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|november|december|'
        r'jan|feb|mrt|apr|jun|jul|aug|sep|okt|nov|dec)[-/.\s](\d{2,4})\b',
        re.IGNORECASE
    )
    
    PATIENTNUMMER = re.compile(
        r'\b(?:pati[eë]nt(?:nummer|nr|id)?|dossier(?:nummer|nr)?|'
        r'zaaknummer|casusnummer)[-:\s]?([A-Z0-9-]{4,15})\b',
        re.IGNORECASE
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def valideer_bsn(bsn: str) -> bool:
    """Valideert een BSN met de 11-proef."""
    if not bsn.isdigit() or len(bsn) != 9:
        return False
    gewichten = [9, 8, 7, 6, 5, 4, 3, 2, -1]
    som = sum(int(c) * w for c, w in zip(bsn, gewichten))
    return som % 11 == 0 and som != 0


def parse_datum(match: re.Match) -> Optional[datetime]:
    """Parseert een datum match naar datetime object."""
    maanden = {
        'januari': 1, 'februari': 2, 'maart': 3, 'april': 4,
        'mei': 5, 'juni': 6, 'juli': 7, 'augustus': 8,
        'september': 9, 'oktober': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mrt': 3, 'apr': 4, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'nov': 11, 'dec': 12
    }
    
    try:
        groups = match.groups()
        dag = int(groups[0])
        maand_str = groups[1].lower()
        maand = maanden.get(maand_str, int(maand_str) if maand_str.isdigit() else None)
        if maand is None:
            return None
        jaar = int(groups[2])
        if jaar < 100:
            jaar += 2000 if jaar < 50 else 1900
        return datetime(jaar, maand, dag)
    except (ValueError, IndexError, TypeError):
        return None


# =============================================================================
# MAIN PSEUDONIMISERING CLASS
# =============================================================================

class Pseudonimiseerder:
    def __init__(self, gebruik_relatieve_datums: bool = True, referentie_datum: datetime = None):
        self.gebruik_relatieve_datums = gebruik_relatieve_datums
        self.referentie_datum = referentie_datum
        self._naam_mapping: Dict[str, str] = {}
        self._adres_mapping: Dict[str, str] = {}
        self._locatie_mapping: Dict[str, str] = {}
        self._tellers: Dict[str, int] = defaultdict(int)
        self._gevonden_datums: List[datetime] = []
        self.statistieken: Dict[str, int] = defaultdict(int)
        self.waarschuwingen: List[str] = []
    
    def _get_label(self, categorie: str, origineel: str, mapping: Dict[str, str]) -> str:
        key = origineel.lower().strip()
        if key not in mapping:
            self._tellers[categorie] += 1
            mapping[key] = f"[{categorie.upper()}_{self._tellers[categorie]}]"
        return mapping[key]
    
    def _datum_naar_relatief(self, datum: datetime) -> str:
        """
        Converteert een datum naar een leesbare relatieve notatie t.o.v. het ongeval/incident.
        
        Voorbeelden:
        - Dag van ongeval: [ONGEVAL]
        - 3 dagen erna: [+3 dagen]
        - 2 weken ervoor: [-2 weken]
        - 6 maanden erna: [+6 maanden]
        - 2 jaar ervoor: [-2 jaar]
        """
        if not self.referentie_datum:
            if self._gevonden_datums:
                self.referentie_datum = min(self._gevonden_datums)
            else:
                return "[DATUM]"
        
        delta = (datum - self.referentie_datum).days
        
        # Exact de ongevalsdatum
        if delta == 0:
            return "[ONGEVAL]"
        
        # Bepaal de beste eenheid
        abs_delta = abs(delta)
        teken = "+" if delta > 0 else "-"
        
        if abs_delta == 1:
            eenheid = "dag"
            waarde = 1
        elif abs_delta < 7:
            # Dagen (2-6 dagen)
            eenheid = "dagen"
            waarde = abs_delta
        elif abs_delta < 14:
            # 1 week
            eenheid = "week"
            waarde = 1
        elif abs_delta < 28:
            # Weken (2-4 weken)
            weken = round(abs_delta / 7)
            eenheid = "weken" if weken > 1 else "week"
            waarde = weken
        elif abs_delta < 60:
            # 1-2 maanden
            maanden = round(abs_delta / 30)
            eenheid = "maand" if maanden == 1 else "maanden"
            waarde = maanden
        elif abs_delta < 365:
            # Maanden (2-11 maanden)
            maanden = round(abs_delta / 30)
            eenheid = "maanden"
            waarde = maanden
        elif abs_delta < 730:
            # 1 jaar of jaar + maanden
            jaren = abs_delta // 365
            rest_maanden = round((abs_delta % 365) / 30)
            if rest_maanden == 0:
                eenheid = "jaar"
                waarde = jaren
            elif rest_maanden < 2:
                eenheid = "jaar"
                waarde = jaren
            else:
                return f"[{teken}{jaren} jaar, {rest_maanden} mnd]"
        else:
            # Meerdere jaren
            jaren = round(abs_delta / 365, 1)
            if jaren == int(jaren):
                jaren = int(jaren)
            eenheid = "jaar"
            waarde = jaren
        
        return f"[{teken}{waarde} {eenheid}]"
    
    def _detecteer_namen(self, tekst: str, email_posities: List[Tuple[int, int]]) -> List[Tuple[int, int, str, str]]:
        gevonden = []
        
        def in_email(start: int, eind: int) -> bool:
            for e_start, e_eind in email_posities:
                if e_start <= start < e_eind or e_start < eind <= e_eind:
                    return True
            return False
        
        tv_pattern = r'(?:van\s+de|van\s+den|van\s+der|van\s+het|van\s+\'t|van|de|het|ter|ten)'
        
        # Voornamen met achternaam
        for voornaam in VOORNAMEN:
            pattern = re.compile(
                rf'\b({re.escape(voornaam)})\s+((?:{tv_pattern})\s+)?([A-Z][a-zëéèêïíìîöóòôüúùû]+)\b',
                re.IGNORECASE
            )
            for match in pattern.finditer(tekst):
                if not in_email(match.start(), match.end()):
                    label = self._get_label("naam", match.group(0), self._naam_mapping)
                    gevonden.append((match.start(), match.end(), match.group(0), label))
        
        # Titels met naam
        titels_pattern = re.compile(
            rf'\b((?:de\s+)?(?:heer|mevrouw|mevr\.|dhr\.|mr\.|dr\.|prof\.)\s+(?:{tv_pattern}\s+)?[A-Z][a-zëéèêïíìîöóòôüúùû]+)\b',
            re.IGNORECASE
        )
        for match in titels_pattern.finditer(tekst):
            if not in_email(match.start(), match.end()):
                al_gevonden = any(s <= match.start() < e for s, e, _, _ in gevonden)
                if not al_gevonden:
                    label = self._get_label("naam", match.group(0), self._naam_mapping)
                    gevonden.append((match.start(), match.end(), match.group(0), label))
        
        # Bekende achternamen
        for achternaam in ACHTERNAMEN:
            pattern = re.compile(rf'\b((?:{tv_pattern}\s+)?{re.escape(achternaam)})\b', re.IGNORECASE)
            for match in pattern.finditer(tekst):
                if not in_email(match.start(), match.end()):
                    al_gevonden = any(s <= match.start() < e or s < match.end() <= e for s, e, _, _ in gevonden)
                    if not al_gevonden:
                        label = self._get_label("naam", match.group(0), self._naam_mapping)
                        gevonden.append((match.start(), match.end(), match.group(0), label))
        
        return gevonden
    
    def _detecteer_locaties(self, tekst: str) -> List[Tuple[int, int, str, str]]:
        gevonden = []
        
        for ziekenhuis in ZIEKENHUIZEN:
            pattern = re.compile(rf'\b{re.escape(ziekenhuis)}\b', re.IGNORECASE)
            for match in pattern.finditer(tekst):
                label = self._get_label("ziekenhuis", match.group(0), self._locatie_mapping)
                gevonden.append((match.start(), match.end(), match.group(0), label))
        
        for stad in STEDEN:
            pattern = re.compile(rf'\b{re.escape(stad)}\b', re.IGNORECASE)
            for match in pattern.finditer(tekst):
                al_gevonden = any(s <= match.start() < e for s, e, _, _ in gevonden)
                if not al_gevonden:
                    label = self._get_label("plaats", match.group(0), self._locatie_mapping)
                    gevonden.append((match.start(), match.end(), match.group(0), label))
        
        return gevonden
    
    def _detecteer_adressen(self, tekst: str) -> List[Tuple[int, int, str, str]]:
        gevonden = []
        
        for match in PIIPatterns.POSTCODE.finditer(tekst):
            label = self._get_label("postcode", match.group(0), self._adres_mapping)
            gevonden.append((match.start(), match.end(), match.group(0), label))
        
        straat_pattern = re.compile(
            r'\b([A-Z][a-zëéèêïíìîöóòôüúùû]+(?:straat|laan|weg|plein|gracht|kade|singel|dreef|hof))\s*'
            r'(\d{1,5}[a-zA-Z]?(?:\s*[-/]\s*\d+)?)\b',
            re.IGNORECASE
        )
        for match in straat_pattern.finditer(tekst):
            label = self._get_label("adres", match.group(0), self._adres_mapping)
            gevonden.append((match.start(), match.end(), match.group(0), label))
        
        return gevonden
    
    def _detecteer_datums(self, tekst: str) -> List[Tuple[int, int, str, str]]:
        gevonden = []
        alle_matches = []
        
        for match in PIIPatterns.DATUM_TEKST.finditer(tekst):
            datum = parse_datum(match)
            if datum:
                alle_matches.append((match.start(), match.end(), match.group(0), datum))
        
        for match in PIIPatterns.DATUM_DMY.finditer(tekst):
            al_gevonden = any(s <= match.start() < e for s, e, _, _ in alle_matches)
            if not al_gevonden:
                datum = parse_datum(match)
                if datum:
                    alle_matches.append((match.start(), match.end(), match.group(0), datum))
        
        self._gevonden_datums.extend([d for _, _, _, d in alle_matches])
        
        for start, eind, origineel, datum in alle_matches:
            if self.gebruik_relatieve_datums:
                label = self._datum_naar_relatief(datum)
            else:
                label = "[DATUM]"
            gevonden.append((start, eind, origineel, label))
        
        return gevonden
    
    def _detecteer_contact(self, tekst: str) -> List[Tuple[int, int, str, str]]:
        gevonden = []
        
        # BSN
        for match in PIIPatterns.BSN.finditer(tekst):
            if valideer_bsn(match.group(1)):
                gevonden.append((match.start(), match.end(), match.group(0), "[BSN]"))
        
        # IBAN
        for match in PIIPatterns.IBAN.finditer(tekst):
            gevonden.append((match.start(), match.end(), match.group(0), "[IBAN]"))
        
        # Telefoon
        for pattern in [PIIPatterns.MOBIEL, PIIPatterns.TELEFOON]:
            for match in pattern.finditer(tekst):
                al_gevonden = any(s <= match.start() < e for s, e, _, _ in gevonden)
                if not al_gevonden:
                    gevonden.append((match.start(), match.end(), match.group(0), "[TELEFOON]"))
        
        # Patiëntnummer
        for match in PIIPatterns.PATIENTNUMMER.finditer(tekst):
            gevonden.append((match.start(), match.end(), match.group(0), "[PATIENTNUMMER]"))
        
        return gevonden
    
    def pseudonimiseer(self, tekst: str) -> str:
        alle_vervangingen: List[Tuple[int, int, str, str]] = []
        
        # Emails eerst
        email_posities = []
        for match in PIIPatterns.EMAIL.finditer(tekst):
            email_posities.append((match.start(), match.end()))
            alle_vervangingen.append((match.start(), match.end(), match.group(0), "[EMAIL]"))
        
        # Overige categorieën
        alle_vervangingen.extend(self._detecteer_namen(tekst, email_posities))
        alle_vervangingen.extend(self._detecteer_locaties(tekst))
        alle_vervangingen.extend(self._detecteer_adressen(tekst))
        alle_vervangingen.extend(self._detecteer_datums(tekst))
        alle_vervangingen.extend(self._detecteer_contact(tekst))
        
        # Sorteer en filter overlappingen
        alle_vervangingen.sort(key=lambda x: (x[0], -(x[1] - x[0])))
        
        gefilterd = []
        laatste_eind = -1
        for verv in sorted(alle_vervangingen, key=lambda x: x[0]):
            start, eind, _, _ = verv
            if start >= laatste_eind:
                gefilterd.append(verv)
                laatste_eind = eind
        
        # Voer vervangingen uit (van achter naar voor)
        gefilterd.sort(key=lambda x: x[0], reverse=True)
        resultaat = tekst
        
        for start, eind, origineel, label in gefilterd:
            # Categoriseer voor statistieken
            if "NAAM" in label:
                self.statistieken["namen"] += 1
            elif "ZIEKENHUIS" in label:
                self.statistieken["ziekenhuizen"] += 1
            elif "PLAATS" in label:
                self.statistieken["plaatsen"] += 1
            elif "POSTCODE" in label or "ADRES" in label:
                self.statistieken["adressen"] += 1
            elif "T+" in label or "T-" in label or "DATUM" in label:
                self.statistieken["datums"] += 1
            elif "BSN" in label:
                self.statistieken["bsn"] += 1
            elif "TELEFOON" in label:
                self.statistieken["telefoon"] += 1
            elif "EMAIL" in label:
                self.statistieken["emails"] += 1
            elif "IBAN" in label:
                self.statistieken["iban"] += 1
            else:
                self.statistieken["overig"] += 1
            
            resultaat = resultaat[:start] + label + resultaat[eind:]
        
        return resultaat


# =============================================================================
# STREAMLIT APP
# =============================================================================

def main():
    # Header
    st.markdown('<p class="main-header">🔒 Kinetic Pseudonimisering</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Privacy-by-Design verwerking van medische dossiers</p>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Sidebar configuratie
    with st.sidebar:
        st.header("⚙️ Configuratie")
        
        gebruik_relatieve_datums = st.checkbox(
            "Gebruik relatieve tijdlijn",
            value=True,
            help="Converteert datums naar leesbare tijdlijn relatief aan het ongeval"
        )
        
        referentie_datum = None
        if gebruik_relatieve_datums:
            st.markdown("##### 📅 Datum ongeval/incident")
            use_custom_date = st.checkbox(
                "Ongevalsdatum opgeven",
                value=False,
                help="Vink aan om de datum van het ongeval/incident in te voeren"
            )
            if use_custom_date:
                referentie_datum = st.date_input(
                    "Wanneer vond het ongeval plaats?",
                    value=None,
                    help="Alle datums worden relatief aan deze datum weergegeven"
                )
                if referentie_datum:
                    referentie_datum = datetime.combine(referentie_datum, datetime.min.time())
                    st.success(f"✓ Ongevalsdatum: {referentie_datum.strftime('%d-%m-%Y')}")
            else:
                st.info("💡 Zonder ongevalsdatum wordt de eerste datum in het dossier als referentie gebruikt.")
            
            st.markdown("---")
            st.markdown("##### 📖 Voorbeeld tijdlijn")
            st.markdown("""
            ```
            [ONGEVAL]      = dag van incident
            [-2 weken]     = 2 weken vóór ongeval
            [+3 dagen]     = 3 dagen na ongeval  
            [+6 maanden]   = 6 maanden na ongeval
            [+1 jaar, 3 mnd] = 1 jaar en 3 maanden
            ```
            """)
        
        st.markdown("---")
        
        st.header("ℹ️ Wat wordt gedetecteerd?")
        st.markdown("""
        - 👤 **Namen** (voor- en achternamen)
        - 🏥 **Ziekenhuizen** (50+ NL ziekenhuizen)
        - 📍 **Plaatsnamen**
        - 📮 **Postcodes & adressen**
        - 📅 **Datums** (diverse formaten)
        - 🔢 **BSN** (met 11-proef validatie)
        - 📱 **Telefoonnummers**
        - 📧 **Email adressen**
        - 💳 **IBAN nummers**
        """)
        
        st.markdown("---")
        
        st.caption("© 2024 Kinetic Medische Expertises")
        st.caption("Alle verwerking gebeurt lokaal in je browser.")
    
    # Main content
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 Invoer")
        
        # File upload of tekst input
        upload_tab, text_tab = st.tabs(["📁 Bestand uploaden", "✏️ Tekst invoeren"])
        
        with upload_tab:
            uploaded_file = st.file_uploader(
                "Upload een tekstbestand",
                type=["txt", "md", "csv"],
                help="Sleep een bestand hierheen of klik om te selecteren"
            )
            
            if uploaded_file:
                input_tekst = uploaded_file.read().decode("utf-8")
                st.text_area("Inhoud bestand:", input_tekst, height=300, disabled=True)
        
        with text_tab:
            input_tekst_manual = st.text_area(
                "Plak hier je tekst:",
                height=300,
                placeholder="Plak hier de tekst die je wilt pseudonimiseren...\n\nBijvoorbeeld:\nDe heer Jan van der Berg (BSN: 123456782) woont op Hoofdstraat 42, 3512 AB Utrecht."
            )
    
    # Bepaal welke tekst te gebruiken
    tekst_to_process = None
    if 'uploaded_file' in dir() and uploaded_file:
        tekst_to_process = input_tekst
    elif input_tekst_manual:
        tekst_to_process = input_tekst_manual
    
    # Process button
    if st.button("🔒 Pseudonimiseer", type="primary", use_container_width=True):
        if tekst_to_process:
            with st.spinner("Bezig met pseudonimiseren..."):
                # Process
                pseudo = Pseudonimiseerder(
                    gebruik_relatieve_datums=gebruik_relatieve_datums,
                    referentie_datum=referentie_datum
                )
                resultaat = pseudo.pseudonimiseer(tekst_to_process)
                
                # Store in session state
                st.session_state['resultaat'] = resultaat
                st.session_state['statistieken'] = dict(pseudo.statistieken)
                st.session_state['totaal'] = sum(pseudo.statistieken.values())
        else:
            st.warning("⚠️ Voer eerst tekst in of upload een bestand.")
    
    # Output
    with col2:
        st.subheader("🔐 Resultaat")
        
        if 'resultaat' in st.session_state:
            # Statistieken
            stats = st.session_state['statistieken']
            totaal = st.session_state['totaal']
            
            st.markdown(f"""
            <div class="success-box">
                <strong>✅ Pseudonimisering voltooid!</strong><br>
                <span style="font-size: 1.5rem; font-weight: bold;">{totaal}</span> items vervangen
            </div>
            """, unsafe_allow_html=True)
            
            # Stats grid
            if stats:
                cols = st.columns(4)
                stat_items = list(stats.items())
                for i, (cat, count) in enumerate(stat_items[:8]):
                    with cols[i % 4]:
                        st.metric(cat.capitalize(), count)
            
            # Resultaat tekst
            st.text_area("Gepseudonimiseerde tekst:", st.session_state['resultaat'], height=300)
            
            # Download button
            st.download_button(
                label="⬇️ Download resultaat",
                data=st.session_state['resultaat'],
                file_name="gepseudonimiseerd.txt",
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.info("👆 Voer tekst in en klik op 'Pseudonimiseer' om te beginnen.")
    
    # Footer met uitleg
    st.markdown("---")
    
    with st.expander("ℹ️ Over deze tool"):
        st.markdown("""
        ### Privacy-by-Design
        
        Deze tool is ontwikkeld voor **Kinetic Medische Expertises** om medische dossiers 
        te pseudonimiseren vóór AI-verwerking. Dit is een essentiële stap in het 
        privacy-by-design proces.
        
        ### Hoe het werkt
        
        1. **Lokale verwerking**: Alle data wordt verwerkt in je browser - er wordt niets naar een server gestuurd
        2. **Patroonherkenning**: De tool zoekt naar bekende patronen (BSN, postcodes, datums, etc.)
        3. **Nederlandse context**: Speciaal geoptimaliseerd voor Nederlandse namen, ziekenhuizen en adresformaten
        4. **Consistente vervanging**: Dezelfde naam krijgt altijd hetzelfde label (bijv. [NAAM_1])
        
        ### 📅 Relatieve tijdlijn
        
        Datums worden omgezet naar een leesbare tijdlijn relatief aan het ongeval/incident:
        
        | Origineel | Wordt | Betekenis |
        |-----------|-------|-----------|
        | 14 juni 2021 | [ONGEVAL] | De datum van het incident |
        | 10 juni 2021 | [-4 dagen] | 4 dagen vóór het ongeval |
        | 21 juni 2021 | [+1 week] | 1 week na het ongeval |
        | 14 december 2021 | [+6 maanden] | 6 maanden na het ongeval |
        | 14 juni 2023 | [+2 jaar] | 2 jaar na het ongeval |
        
        Dit maakt de medische chronologie veel overzichtelijker!
        
        ### BSN Validatie
        
        BSN-nummers worden gevalideerd met de officiële 11-proef om false positives te voorkomen.
        
        ### ⚠️ Disclaimer
        
        Deze tool is bedoeld als hulpmiddel. Controleer altijd handmatig of alle 
        identificerende gegevens correct zijn vervangen voordat u het document deelt.
        """)


if __name__ == "__main__":
    main()
