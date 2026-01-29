"""
Kinetic Pseudonymizer v2.1 - Verbeterde PII detectie
=====================================================
Detecteert en vervangt persoonsgegevens:
- Namen → [PERSOON_1], [PERSOON_2], etc.
- BSN → [BSN]
- Adressen → [ADRES]
- Telefoonnummers → [TELEFOON]
- Geboortedatums → [GEBOORTEDATUM]
- Emails → [EMAIL]
- IBAN → [IBAN]
- Datums → relatief t.o.v. ongevalsdatum (T-30, T+0, T+90, etc.)

Auteur: Kinetic Medische Expertises
Versie: 2.1
"""

import re
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class PseudonymizationResult:
    """Resultaat van pseudonimisering"""
    original_text: str
    pseudonymized_text: str
    replacements: Dict[str, str]
    statistics: Dict[str, int]
    incident_date: Optional[datetime]
    warnings: List[str]


class MedicalPseudonymizer:
    """
    Pseudonimiseert medische teksten met consistente vervanging.
    """
    
    def __init__(self, incident_date: Optional[datetime] = None):
        self.incident_date = incident_date
        self.name_mapping: Dict[str, str] = {}
        self.name_counter = 0
        self.address_counter = 0
        self.statistics = defaultdict(int)
        self.warnings: List[str] = []
        
    def _normalize_name(self, name: str) -> str:
        """Normaliseer naam voor consistente matching"""
        return ' '.join(name.lower().split())
        
    def _get_person_pseudonym(self, name: str) -> str:
        """Geef consistente pseudoniem voor een naam"""
        normalized = self._normalize_name(name)
        
        if normalized not in self.name_mapping:
            self.name_counter += 1
            self.name_mapping[normalized] = f"[PERSOON_{self.name_counter}]"
            
        return self.name_mapping[normalized]

    def _detect_incident_date(self, text: str) -> Optional[datetime]:
        """Probeer ongevalsdatum uit tekst te detecteren"""
        patterns = [
            r'(?:datum\s*)?(?:schade|ongeval|incident|trauma)\s*[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(?:schade|ongeval|incident)\s*(?:op|d\.?d\.?|van)\s*[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'na\s+(?:val|ongeval|trauma)\s+(?:op\s+)?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'trauma\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parsed = self._parse_date(match.group(1))
                if parsed:
                    return parsed
        return None
        
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse datum string"""
        formats = ['%d-%m-%Y', '%d/%m/%Y', '%d-%m-%y', '%d/%m/%y']
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None
        
    def _date_to_relative(self, date: datetime) -> str:
        """Converteer datum naar relatieve notatie"""
        if not self.incident_date:
            return "[DATUM]"
            
        delta = (date - self.incident_date).days
        
        if delta == 0:
            return "[T+0]"
        elif delta > 0:
            return f"[T+{delta}]"
        else:
            return f"[T{delta}]"

    def _replace_bsn(self, text: str) -> str:
        """Vervang BSN nummers - diverse formaten"""
        patterns = [
            r'\b(\d{4}[.\s]\d{2}[.\s]\d{3})\b',  # 1234.56.782 of 1234 56 782
            r'(?<!\d)(\d{9})(?!\d)',  # 123456782 (niet deel van langer nummer)
            r'\b(\d{3}[.\-]\d{3}[.\-]\d{3})\b',  # 123.456.789
        ]
        
        result = text
        for pattern in patterns:
            def replace(match):
                self.statistics['bsn'] += 1
                return '[BSN]'
            result = re.sub(pattern, replace, result)
            
        return result

    def _replace_iban(self, text: str) -> str:
        """Vervang IBAN nummers"""
        pattern = r'\b([A-Z]{2}\d{2}[A-Z]{4}\d{10})\b'
        
        def replace(match):
            self.statistics['iban'] += 1
            return '[IBAN]'
            
        return re.sub(pattern, replace, text)

    def _replace_phone_numbers(self, text: str) -> str:
        """Vervang telefoonnummers - verbeterde patterns"""
        patterns = [
            # +31 6 1234 5678 of +31 6 12345678 (met of zonder spaties)
            r'\+31\s*6[\s\-]?\d{4}[\s\-]?\d{4}',
            r'\+31\s*6[\s\-]?\d{8}',
            # +31 met andere netnummers
            r'\+31\s*\d{2,3}[\s\-]?\d{6,7}',
            # 06-12345678, 06 1234 5678
            r'\b06[\s\-]?\d{4}[\s\-]?\d{4}\b',
            r'\b06[\s\-]?\d{8}\b',
            # 020-1234567
            r'\b0\d{2,3}[\s\-]?\d{6,7}\b',
        ]
        
        result = text
        for pattern in patterns:
            def replace(match):
                self.statistics['phone'] += 1
                return '[TELEFOON]'
            result = re.sub(pattern, replace, result)
            
        return result

    def _replace_email(self, text: str) -> str:
        """Vervang email adressen"""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        def replace(match):
            self.statistics['email'] += 1
            return '[EMAIL]'
            
        return re.sub(pattern, replace, text)

    def _replace_postal_codes(self, text: str) -> str:
        """Vervang postcodes"""
        pattern = r'\b(\d{4}\s?[A-Z]{2})\b'
        
        def replace(match):
            self.statistics['postal_codes'] += 1
            return '[POSTCODE]'
            
        return re.sub(pattern, replace, text)

    def _replace_addresses(self, text: str) -> str:
        """Vervang straatnamen met huisnummers"""
        # Straatnaam + huisnummer (+ toevoeging)
        pattern = r'([A-Z][a-zéëïöüA-Z\s]+(?:straat|laan|weg|plein|singel|gracht|kade|dreef|hof|park|baan|dijk)\s+\d+(?:[-/]?\d*|[a-zA-Z\-]*)?)'
        
        def replace(match):
            self.statistics['addresses'] += 1
            self.address_counter += 1
            return f'[ADRES_{self.address_counter}]'
            
        return re.sub(pattern, replace, text, flags=re.IGNORECASE)

    def _replace_birth_dates(self, text: str) -> str:
        """Vervang geboortedatums"""
        patterns = [
            r'(geb(?:oortedatum|\.)?)\s*[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(geboren\s+(?:op\s+)?)\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(DOB)\s*[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        ]
        
        result = text
        for pattern in patterns:
            def replace(match):
                self.statistics['birth_dates'] += 1
                return match.group(1) + ' [GEBOORTEDATUM]'
            result = re.sub(pattern, replace, result, flags=re.IGNORECASE)
            
        return result

    def _replace_dates(self, text: str) -> str:
        """Vervang overige datums"""
        pattern = r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})\b'
        
        def replace(match):
            try:
                day = int(match.group(1))
                month = int(match.group(2))
                year = int(match.group(3))
                
                if year < 100:
                    year = 2000 + year if year < 50 else 1900 + year
                
                if 1 <= day <= 31 and 1 <= month <= 12:
                    date = datetime(year, month, day)
                    self.statistics['dates'] += 1
                    return self._date_to_relative(date)
            except (ValueError, IndexError):
                pass
            return match.group(0)
            
        return re.sub(pattern, replace, text)

    def _replace_names(self, text: str) -> str:
        """Vervang persoonsnamen - uitgebreide detectie"""
        result = text
        
        # 0. Internationale namen: Fatima El Amrani, Mohammed Al Hassan, Ahmed Ben Ali
        intl_pattern = r'\b([A-Z][a-zéëïöü]+)\s+(El|Al|Ben|Ibn|Abu|Bin)\s+([A-Z][a-zéëïöüA-Z]+)\b'
        
        def replace_intl(match):
            full_name = match.group(0)
            self.statistics['names'] += 1
            return self._get_person_pseudonym(full_name)
        
        result = re.sub(intl_pattern, replace_intl, result)
        
        # 1. Volledige namen met dubbele achternaam: Sanne de Vries-van Dijk
        double_surname = r'\b([A-Z][a-zéëïöü]+)\s+((?:de|van|den|der|het|ter|ten)\s+)?([A-Z][a-zéëïöü]+)(-(?:van|de|den|der)\s+[A-Z][a-zéëïöü]+)\b'
        
        def replace_double(match):
            full_name = match.group(0)
            self.statistics['names'] += 1
            return self._get_person_pseudonym(full_name)
        
        result = re.sub(double_surname, replace_double, result)
        
        # 2. Namen met tussenvoegsel: Jan van den Berg, Piet de Groot
        dutch_pattern = r'\b([A-Z][a-zéëïöü]+)\s+(van|de|den|der|het|ter|ten)(\s+(?:de|den|der|het))?\s+([A-Z][a-zéëïöü]+)\b'
        
        def replace_dutch(match):
            full_name = match.group(0)
            if '[PERSOON_' in full_name:
                return full_name
            self.statistics['names'] += 1
            return self._get_person_pseudonym(full_name)
            
        result = re.sub(dutch_pattern, replace_dutch, result)
        
        # 3. Titels + naam: Dr. M. van Leeuwen, Mevr. Jansen
        title_pattern = r'\b((?:Dr|Drs|Mr|Mw|Mevr|Dhr|Prof|Ir|Ing)\.?\s+)([A-Z]\.?\s*)?([a-z]*\s*)?((?:van|de|den|der|het|ter|ten)\s+(?:de\s+|den\s+|der\s+)?)?([A-Z][a-zéëïöü]+)\b'
        
        def replace_titled(match):
            full = match.group(0)
            if '[PERSOON_' in full:
                return full
            title = match.group(1)
            rest = full[len(title):]
            self.statistics['names'] += 1
            return title + self._get_person_pseudonym(rest)
            
        result = re.sub(title_pattern, replace_titled, result, flags=re.IGNORECASE)
        
        # 4. Initialen + achternaam: S. de Vries, N. Jansen
        initials_pattern = r'\b([A-Z]\.(?:\s?[A-Z]\.)*)\s*((?:van|de|den|der|het|ter|ten)\s+(?:de\s+|den\s+)?)?([A-Z][a-zéëïöü]+)\b'
        
        def replace_initials(match):
            full = match.group(0)
            if '[PERSOON_' in full:
                return full
            self.statistics['names'] += 1
            return self._get_person_pseudonym(full)
            
        result = re.sub(initials_pattern, replace_initials, result)
        
        # 5. "mevrouw/meneer [Naam]"
        honorific_pattern = r'\b((?:mevrouw|meneer|geachte\s+(?:heer|mevrouw))\s+)((?:van|de|den|der)\s+)?([A-Z][a-zéëïöü]+)\b'
        
        def replace_honorific(match):
            full = match.group(0)
            if '[PERSOON_' in full:
                return full
            honorific = match.group(1)
            name_part = full[len(honorific):]
            self.statistics['names'] += 1
            return honorific + self._get_person_pseudonym(name_part)
            
        result = re.sub(honorific_pattern, replace_honorific, result, flags=re.IGNORECASE)
        
        # 6. Voornaam + initial: Youssef A., Maria B.
        name_initial_pattern = r'\b([A-Z][a-zéëïöü]{2,})\s+([A-Z])\.'
        
        def replace_name_initial(match):
            full = match.group(0)
            if '[PERSOON_' in full:
                return full
            self.statistics['names'] += 1
            return self._get_person_pseudonym(full)
            
        result = re.sub(name_initial_pattern, replace_name_initial, result)
        
        # 7. Simpele voornaam + achternaam: Jeroen Bakker
        simple_pattern = r'\b([A-Z][a-zéëïöü]{2,})\s+([A-Z][a-zéëïöü]{2,})\b'
        
        # Lijst van woorden die geen namen zijn
        non_names = {
            'Adres', 'Telefoon', 'Email', 'Datum', 'Betreft', 'Locatie', 'Oost',
            'West', 'Noord', 'Zuid', 'Amsterdam', 'Rotterdam', 'Utrecht',
            'Praktijk', 'Polikliniek', 'Orthopedie', 'Indicatie', 'Conclusie',
            'Bevindingen', 'Beleid', 'Plan', 'Subjectief', 'Objectief',
            'Consult', 'Brief', 'Verslag', 'Document', 'Intake', 'Categorie'
        }
        
        def replace_simple(match):
            full = match.group(0)
            first = match.group(1)
            second = match.group(2)
            
            if '[PERSOON_' in full:
                return full
            if first in non_names or second in non_names:
                return full
            # Skip als het er uitziet als een locatie of organisatie
            if any(x in full for x in ['Locatie', 'Praktijk', 'Afdeling']):
                return full
                
            self.statistics['names'] += 1
            return self._get_person_pseudonym(full)
            
        result = re.sub(simple_pattern, replace_simple, result)
        
        return result

    def _replace_kvk(self, text: str) -> str:
        """Vervang KvK nummers"""
        pattern = r'\b(?:KvK|kvk)\s*[:\s]*(\d{8})\b'
        
        def replace(match):
            self.statistics['kvk'] += 1
            return 'KvK [KVK_NUMMER]'
            
        return re.sub(pattern, replace, text, flags=re.IGNORECASE)

    def _replace_policy_numbers(self, text: str) -> str:
        """Vervang polis- en schadenummers"""
        patterns = [
            (r'(Polis(?:nummer)?)\s*[:\s]*([A-Z0-9\-]+)', 'polis'),
            (r'(Schade(?:nummer)?|Schadenr\.?)\s*[:\s]*([A-Z0-9\-]+)', 'schade'),
            (r'\b(POL-[A-Z]+-\d{4}-\d+)\b', 'polis'),
            (r'\b(SCH-\d{4}-\d{2}-\d+)\b', 'schade'),
        ]
        
        result = text
        for pattern, stat_key in patterns:
            def make_replacer(key):
                def replace(match):
                    self.statistics[key + '_numbers'] += 1
                    if match.lastindex and match.lastindex >= 2:
                        return match.group(1) + ': [' + key.upper() + '_NUMMER]'
                    return '[' + key.upper() + '_NUMMER]'
                return replace
            result = re.sub(pattern, make_replacer(stat_key), result, flags=re.IGNORECASE)
            
        return result

    def _replace_patient_ids(self, text: str) -> str:
        """Vervang patiënt-IDs"""
        pattern = r'\b((?:patiënt|patient|cliënt|client)[-\s]?(?:ID|id|nummer)?)\s*[:\s]*([A-Z0-9]+-[A-Z0-9]+-\d+)\b'
        
        def replace(match):
            self.statistics['patient_ids'] += 1
            return match.group(1) + ': [PATIENT_ID]'
            
        return re.sub(pattern, replace, text, flags=re.IGNORECASE)

    def pseudonymize(self, text: str) -> PseudonymizationResult:
        """
        Hoofdmethode: pseudonimiseer de tekst.
        """
        # Reset
        self.name_mapping = {}
        self.name_counter = 0
        self.address_counter = 0
        self.statistics = defaultdict(int)
        self.warnings = []
        
        # Detecteer ongevalsdatum
        if not self.incident_date:
            detected = self._detect_incident_date(text)
            if detected:
                self.incident_date = detected
            else:
                self.warnings.append(
                    "Geen ongevalsdatum gevonden. Datums worden als [DATUM] weergegeven. "
                    "Vul de ongevalsdatum handmatig in voor relatieve datums."
                )
        
        # Voer vervangingen uit in specifieke volgorde
        result = text
        
        # 1. Specifieke identifiers eerst
        result = self._replace_birth_dates(result)
        result = self._replace_bsn(result)
        result = self._replace_iban(result)
        result = self._replace_patient_ids(result)
        result = self._replace_policy_numbers(result)
        result = self._replace_kvk(result)
        
        # 2. Contact gegevens
        result = self._replace_email(result)
        result = self._replace_phone_numbers(result)
        
        # 3. Locatie
        result = self._replace_addresses(result)
        result = self._replace_postal_codes(result)
        
        # 4. Namen (na adressen, zodat straatnamen niet als namen worden gezien)
        result = self._replace_names(result)
        
        # 5. Overige datums als laatste
        result = self._replace_dates(result)
        
        return PseudonymizationResult(
            original_text=text,
            pseudonymized_text=result,
            replacements=dict(self.name_mapping),
            statistics=dict(self.statistics),
            incident_date=self.incident_date,
            warnings=self.warnings
        )


def pseudonymize_text(
    text: str,
    incident_date: Optional[datetime] = None
) -> PseudonymizationResult:
    """Convenience functie"""
    pseudonymizer = MedicalPseudonymizer(incident_date=incident_date)
    return pseudonymizer.pseudonymize(text)


# Test
if __name__ == "__main__":
    test_text = """
    Dossierhouder: Sanne de Vries-van Dijk (geb. 14-07-1989)
    BSN: 1234.56.782 Telefoon: +31 6 1234 5678 E-mail: sanne.vries89@example.nl
    Adres: Johannes Vermeerstraat 18-2, 1071 DR Amsterdam
    IBAN: NL91ABNA0417164300
    Polisnummer: POL-AVP-2021-0098743
    Schadenummer: SCH-2025-11-483920
    Werkgever: Stad & Co Marketing B.V. (KvK 76543210)
    
    Huisarts: Dr. M. van Leeuwen
    Noodcontact: Jeroen van Dijk (partner) +31 6 8765 4321
    
    Datum onderzoek: 12-12-2025
    Trauma op 18-11-2025.
    
    Patiënt-ID: OLVG-PT-5589012
    Mevrouw de Vries kwam op consult.
    S. de Vries is telefonisch bereikbaar.
    N. Jansen behandelt het dossier.
    """
    
    result = pseudonymize_text(test_text)
    
    print("=== GEPSEUDONIMISEERDE TEKST ===")
    print(result.pseudonymized_text)
    print("\n=== STATISTIEKEN ===")
    for key, value in sorted(result.statistics.items()):
        print(f"  {key}: {value}")
    print("\n=== NAAM MAPPING ===")
    for orig, pseudo in result.replacements.items():
        print(f"  '{orig}' → {pseudo}")
