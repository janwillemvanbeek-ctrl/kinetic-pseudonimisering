# 🔒 Kinetic Pseudonimisering Tool

Privacy-by-Design verwerking van medische dossiers voor Kinetic Medische Expertises.

## 🚀 Live Demo

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://kinetic-pseudonimisering.streamlit.app)

## ✨ Features

- **Nederlandse context**: Geoptimaliseerd voor NL namen, ziekenhuizen, adressen
- **BSN validatie**: 11-proef controle voorkomt false positives  
- **Relatieve tijdlijn**: Datums → T+dagen voor heldere medische chronologie
- **Lokale verwerking**: Geen data wordt naar servers gestuurd
- **Consistente labels**: Dezelfde naam krijgt altijd hetzelfde label

## 📋 Wat wordt gedetecteerd?

| Categorie | Voorbeelden |
|-----------|-------------|
| 👤 Namen | Jan van der Berg → [NAAM_1] |
| 🏥 Ziekenhuizen | Amsterdam UMC → [ZIEKENHUIS_1] |
| 📍 Plaatsen | Utrecht → [PLAATS_1] |
| 📮 Postcodes | 3512 AB → [POSTCODE_1] |
| 📅 Datums | 15 januari 2024 → [T+365] |
| 🔢 BSN | 123456782 → [BSN] |
| 📱 Telefoon | 06-12345678 → [TELEFOON] |
| 📧 Email | jan@test.nl → [EMAIL] |
| 💳 IBAN | NL91ABNA... → [IBAN] |

## 🛠️ Lokaal draaien

```bash
# Clone repository
git clone https://github.com/[username]/kinetic-pseudonimisering.git
cd kinetic-pseudonimisering

# Installeer dependencies
pip install -r requirements.txt

# Start de app
streamlit run app.py
```

## 📦 Deploy naar Streamlit Cloud

1. Fork deze repository naar je GitHub account
2. Ga naar [share.streamlit.io](https://share.streamlit.io)
3. Klik op "New app"
4. Selecteer je repository en `app.py`
5. Klik "Deploy"

De app is binnen enkele minuten live!

## 🔐 Privacy & Compliance

Deze tool is onderdeel van de Privacy-by-Design aanpak van Kinetic Medische Expertises:

- ✅ Lokale verwerking (geen cloud upload)
- ✅ AVG-compliant workflow
- ✅ Audit trail ondersteuning
- ✅ Geen training op data

## 📄 Licentie

© 2024 Kinetic Medische Expertises. Alle rechten voorbehouden.

## 🤝 Contact

Voor vragen over deze tool of Kinetic Medische Expertises, neem contact op via [contact info].
