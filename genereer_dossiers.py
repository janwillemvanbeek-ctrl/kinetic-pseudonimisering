"""
Generator voor synthetische medische dossiers
Voor het testen van de Kinetic Pseudonimiseringstool
"""

import random
from datetime import datetime, timedelta

# ============================================================================
# DATA POOLS
# ============================================================================

VOORNAMEN_M = ["Jan", "Piet", "Klaas", "Willem", "Henk", "Peter", "Marco", "Dennis", "Robert", "Michel"]
VOORNAMEN_V = ["Maria", "Sandra", "Linda", "Monique", "Patricia", "Jessica", "Angela", "Esther", "Marloes", "Anouk"]
ACHTERNAMEN = ["Van der Berg", "De Vries", "Jansen", "De Groot", "Bakker", "Van Dijk", "Smit", "Meijer", "De Boer", "Mulder"]
TUSSENVOEGSELS = ["van", "van de", "van den", "van der", "de", ""]

STRATEN = ["Hoofdstraat", "Kerkstraat", "Dorpsstraat", "Schoolstraat", "Molenweg", "Julianastraat", "Beatrixlaan", "Wilhelminastraat"]
STEDEN = ["Amsterdam", "Rotterdam", "Utrecht", "Den Haag", "Eindhoven", "Groningen", "Tilburg", "Almere", "Breda", "Nijmegen"]
POSTCODES = ["1012 AB", "3011 CD", "3500 EF", "2500 GH", "5600 IJ", "9700 KL", "5000 MN", "1300 OP", "4800 QR", "6500 ST"]

ZIEKENHUIZEN = [
    ("Amsterdam UMC", "Amsterdam"),
    ("Erasmus MC", "Rotterdam"),
    ("UMC Utrecht", "Utrecht"),
    ("OLVG", "Amsterdam"),
    ("Antonius Ziekenhuis", "Nieuwegein"),
    ("Isala", "Zwolle"),
    ("Catharina Ziekenhuis", "Eindhoven"),
    ("Maasstad Ziekenhuis", "Rotterdam"),
    ("Reinier de Graaf", "Delft"),
    ("Jeroen Bosch Ziekenhuis", "Den Bosch"),
]

REVALIDATIECENTRA = ["Reade", "De Hoogstraat", "Heliomare", "Roessingh", "Sint Maartenskliniek"]

SPECIALISMEN = ["neuroloog", "orthopeed", "revalidatiearts", "neurochirurg", "anesthesioloog"]
HUISARTSEN = ["dr. Pietersen", "dr. Van Dam", "dr. Willemsen", "dr. Hendriks", "dr. De Jong"]

ONGEVAL_TYPES = [
    "een verkeersongeval op de {snelweg}",
    "een aanrijding op de kruising {straat}/{straat2}",
    "een bedrijfsongeval bij {bedrijf}",
    "een val van een trap",
    "een fietsongeval",
    "een ongeval met een scooter",
    "een botsing op de parkeerplaats van {winkel}",
]

LETSEL_TYPES = [
    ("whiplash", "nekpijn, hoofdpijn en duizeligheid"),
    ("hernia L4-L5", "uitstralende pijn in het been en krachtsverlies"),
    ("schouderletsel", "beperkte bewegelijkheid en pijn bij heffen"),
    ("knieletsel", "instabiliteit en zwelling van de knie"),
    ("polsfractuur", "pijn en beperkte grip"),
    ("hersenschudding", "hoofdpijn, concentratieproblemen en vermoeidheid"),
    ("ribfracturen", "pijn bij ademhaling en beperkte mobiliteit"),
]

BEDRIJVEN = ["Jumbo Distributiecentrum", "PostNL", "Bol.com warehouse", "Albert Heijn", "DHL depot"]
SNELWEGEN = ["A2", "A12", "A27", "A1", "A28", "A4", "A10", "A15"]
WINKELS = ["Albert Heijn", "Jumbo", "IKEA", "Praxis", "Gamma"]

# ============================================================================
# DOSSIER GENERATOR
# ============================================================================

def genereer_bsn():
    """Genereert een geldig BSN (voldoet aan 11-proef)."""
    while True:
        cijfers = [random.randint(0, 9) for _ in range(8)]
        # Bereken 9e cijfer zodat het voldoet aan 11-proef
        gewichten = [9, 8, 7, 6, 5, 4, 3, 2]
        som = sum(c * w for c, w in zip(cijfers, gewichten))
        # Laatste cijfer: som + (-1 * x) moet deelbaar zijn door 11
        for x in range(10):
            if (som - x) % 11 == 0:
                cijfers.append(x)
                bsn = ''.join(map(str, cijfers))
                # Verificatie
                check = sum(int(c) * w for c, w in zip(bsn, [9,8,7,6,5,4,3,2,-1]))
                if check % 11 == 0 and check != 0:
                    return bsn
                break

def genereer_iban():
    """Genereert een Nederlands IBAN-achtig nummer."""
    banken = ["ABNA", "INGB", "RABO", "SNSB"]
    return f"NL{random.randint(10,99)}{random.choice(banken)}{random.randint(1000000000, 9999999999)}"

def genereer_telefoon():
    """Genereert een Nederlands telefoonnummer."""
    if random.choice([True, False]):
        return f"06-{random.randint(10000000, 99999999)}"
    else:
        netnummer = random.choice(["010", "020", "030", "040", "050"])
        return f"{netnummer}-{random.randint(1000000, 9999999)}"

def genereer_datum(basis_datum, dagen_offset):
    """Genereert een datum relatief aan de basis."""
    return basis_datum + timedelta(days=dagen_offset)

def format_datum(datum):
    """Formatteert datum in Nederlands formaat."""
    maanden = ["januari", "februari", "maart", "april", "mei", "juni", 
               "juli", "augustus", "september", "oktober", "november", "december"]
    return f"{datum.day} {maanden[datum.month-1]} {datum.year}"

def genereer_dossier(nummer):
    """Genereert één compleet synthetisch dossier."""
    
    # Basis gegevens
    is_vrouw = random.choice([True, False])
    voornaam = random.choice(VOORNAMEN_V if is_vrouw else VOORNAMEN_M)
    achternaam = random.choice(ACHTERNAMEN)
    
    geslacht = "vrouw" if is_vrouw else "man"
    aanspreekvorm = "mevrouw" if is_vrouw else "de heer"
    zij_hij = "zij" if is_vrouw else "hij"
    haar_zijn = "haar" if is_vrouw else "zijn"
    
    # Ongeval datum (ergens in 2020-2022)
    ongeval_datum = datetime(2020 + random.randint(0, 2), random.randint(1, 12), random.randint(1, 28))
    geboortedatum = ongeval_datum - timedelta(days=365 * random.randint(25, 60))
    
    # Adressen
    straat = random.choice(STRATEN)
    huisnummer = random.randint(1, 200)
    postcode = random.choice(POSTCODES)
    woonplaats = random.choice(STEDEN)
    
    # Medische gegevens
    ziekenhuis1, zh1_stad = random.choice(ZIEKENHUIZEN)
    ziekenhuis2, zh2_stad = random.choice(ZIEKENHUIZEN)
    revalidatie = random.choice(REVALIDATIECENTRA)
    huisarts = random.choice(HUISARTSEN)
    specialist = random.choice(SPECIALISMEN)
    letsel, klachten = random.choice(LETSEL_TYPES)
    
    # Ongeval details
    ongeval_type = random.choice(ONGEVAL_TYPES).format(
        snelweg=random.choice(SNELWEGEN),
        straat=random.choice(STRATEN),
        straat2=random.choice(STRATEN),
        bedrijf=random.choice(BEDRIJVEN),
        winkel=random.choice(WINKELS)
    )
    
    # Behandelend artsen
    arts1_voornaam = random.choice(VOORNAMEN_M + VOORNAMEN_V)[0]
    arts1_achternaam = random.choice(ACHTERNAMEN)
    arts2_voornaam = random.choice(VOORNAMEN_M + VOORNAMEN_V)[0]
    arts2_achternaam = random.choice(ACHTERNAMEN)
    
    # Contact gegevens
    bsn = genereer_bsn()
    telefoon = genereer_telefoon()
    email = f"{voornaam.lower()}.{achternaam.lower().replace(' ', '')}@gmail.com"
    
    # Adviseur
    adviseur_voornaam = random.choice(VOORNAMEN_M + VOORNAMEN_V)[0]
    adviseur_achternaam = random.choice(ACHTERNAMEN)
    adviseur_email = f"{adviseur_voornaam.lower()}.{adviseur_achternaam.lower().replace(' ', '')}@sedgwick.nl"
    
    # Tijdlijn
    d_seh = ongeval_datum
    d_huisarts1 = genereer_datum(ongeval_datum, random.randint(3, 10))
    d_specialist1 = genereer_datum(ongeval_datum, random.randint(30, 90))
    d_mri = genereer_datum(ongeval_datum, random.randint(60, 120))
    d_revalidatie_start = genereer_datum(ongeval_datum, random.randint(90, 180))
    d_revalidatie_eind = genereer_datum(d_revalidatie_start, random.randint(90, 180))
    d_onderzoek = genereer_datum(ongeval_datum, random.randint(400, 800))
    d_advies = genereer_datum(d_onderzoek, random.randint(14, 60))
    
    # Arbeidsongeschiktheid
    ao_percentage = random.choice([25, 50, 75, 100])
    werkuren = 40 - (40 * ao_percentage // 100)
    beroep = random.choice(["administratief medewerker", "magazijnmedewerker", "verpleegkundige", 
                           "docent", "accountant", "monteur", "verkoper"])
    werkgever = random.choice(["ABN AMRO", "Philips", "ASML", "Rabobank", "NS", "KLM", "Unilever"])
    
    # Genereer het dossier
    dossier = f"""MEDISCH ADVIES - DOSSIER {nummer:03d}

Dossiernummer: {2024}-MA-{random.randint(1000, 9999)}
Datum advies: {format_datum(d_advies)}

═══════════════════════════════════════════════════════════════════════════════
PERSOONSGEGEVENS
═══════════════════════════════════════════════════════════════════════════════

Betreft: {aanspreekvorm} {voornaam} {achternaam}
Geboortedatum: {format_datum(geboortedatum)}
BSN: {bsn}
Adres: {straat} {huisnummer}, {postcode} {woonplaats}
Telefoon: {telefoon}
Email: {email}

═══════════════════════════════════════════════════════════════════════════════
AANLEIDING
═══════════════════════════════════════════════════════════════════════════════

Op {format_datum(ongeval_datum)} was betrokkene betrokken bij {ongeval_type}. 
{zij_hij.capitalize()} werd hierbij gewond en heeft sindsdien klachten.

═══════════════════════════════════════════════════════════════════════════════
MEDISCHE VOORGESCHIEDENIS
═══════════════════════════════════════════════════════════════════════════════

Uit het huisartsenjournaal van {huisarts} te {woonplaats} blijkt dat {aanspreekvorm} 
{achternaam} voor het ongeval geen relevante klachten had op het gebied van {letsel.split()[0] if ' ' in letsel else letsel}.

═══════════════════════════════════════════════════════════════════════════════
BEHANDELVERLOOP
═══════════════════════════════════════════════════════════════════════════════

{format_datum(d_seh)} - SPOEDEISENDE HULP
Direct na het ongeval werd {achternaam} per ambulance vervoerd naar het {ziekenhuis1} 
te {zh1_stad}. De SEH-arts constateerde {letsel}.

{format_datum(d_huisarts1)} - HUISARTS
Eerste controle bij {huisarts}. Betrokkene klaagt over {klachten}. 
Verwezen naar {specialist}.

{format_datum(d_specialist1)} - SPECIALIST
Consult bij dr. {arts1_voornaam}. {arts1_achternaam}, {specialist} in het {ziekenhuis2} 
te {zh2_stad}. Lichamelijk en neurologisch onderzoek verricht.

{format_datum(d_mri)} - BEELDVORMING
MRI-onderzoek in het {ziekenhuis1}. Bevindingen passend bij {letsel}.

{format_datum(d_revalidatie_start)} - {format_datum(d_revalidatie_eind)} - REVALIDATIE
Multidisciplinair revalidatietraject bij {revalidatie}. Behandeling door fysiotherapeut, 
ergotherapeut en psycholoog.

═══════════════════════════════════════════════════════════════════════════════
HUIDIGE SITUATIE (per {format_datum(d_onderzoek)})
═══════════════════════════════════════════════════════════════════════════════

{aanspreekvorm.capitalize()} {achternaam} geeft aan nog steeds last te hebben van:
- {klachten.split(',')[0].strip().capitalize()}
- Verminderde belastbaarheid
- Concentratieproblemen

{zij_hij.capitalize()} is momenteel {ao_percentage}% arbeidsongeschikt en werkt {werkuren} uur 
per week als {beroep} bij {werkgever}.

═══════════════════════════════════════════════════════════════════════════════
CONCLUSIE
═══════════════════════════════════════════════════════════════════════════════

Er is sprake van persisterende klachten na {letsel}, meer dan {(d_onderzoek - ongeval_datum).days // 30} 
maanden na het ongeval. De prognose voor volledig herstel is gereserveerd.

═══════════════════════════════════════════════════════════════════════════════
ONDERTEKENING
═══════════════════════════════════════════════════════════════════════════════

Met vriendelijke groet,

Dr. {adviseur_voornaam}. {adviseur_achternaam}
Medisch adviseur

Sedgwick Nederland B.V.
Postbus {random.randint(100, 9999)}
{random.choice(POSTCODES)} Rotterdam
Tel: 010-{random.randint(1000000, 9999999)}
Email: {adviseur_email}

═══════════════════════════════════════════════════════════════════════════════
"""
    
    return dossier, ongeval_datum


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("Genereren van 10 synthetische dossiers...")
    
    for i in range(1, 11):
        dossier, ongeval_datum = genereer_dossier(i)
        
        filename = f"/home/claude/test_dossiers/dossier_{i:02d}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(dossier)
        
        print(f"  ✓ Dossier {i:02d} gegenereerd (ongeval: {ongeval_datum.strftime('%d-%m-%Y')})")
    
    print("\nKlaar! 10 dossiers opgeslagen in /home/claude/test_dossiers/")
