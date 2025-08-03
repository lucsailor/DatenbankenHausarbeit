# StreamlitApp
BITTE AUSSCHLIEßLICH IM LIGHT MODE BENUTZEN!!!

Dieses Projekt ist eine interaktive Streamlit Anwendung zur Analyse der Top-5 Fußballligen Europas. Die Daten stammen aus einer SQLite-Datenbank und werden in übersichtlichen Tabellen und Grafiken aufbereitet. Sie ist über: https://hausarbeitwwi23scb.streamlit.app erreichbar.

## Features
- **Startseite mit Ligawahl**: Auswahl der gewünschten Liga und farblich hervorgehobene Tabellenplätze (Champions League, Europa League, Abstiegsränge).
- **Letzte Spiele**: Darstellung der drei aktuellsten Partien der gewählten Liga inklusive Vereinslogos und Ergebnisse.
- **Einzelseiten pro Liga**: Detaillierte Tabellen und Spieltagsnavigation für Bundesliga, La Liga, Ligue 1, Premier League und Serie A.
- **Weitere Auswertungen**: Zusätzliche Seiten zur Verwaltung von Spielen, Spielern und Vereinen.

## Installation
1. Repository klonen:
   ```bash
   git clone https://github.com/lucsailor/DatenbankenHausarbeit.git
   cd DatenbankenHausarbeit
   ```
2. Abhängigkeiten installieren (optional in einer virtuellen Umgebung):
   ```bash
   pip install -r requirements.txt
   ```

## Nutzung
Die Anwendung lässt sich mit Streamlit starten:
```bash
streamlit run Startseite.py
```
Nach dem Start öffnet sich eine lokale Webseite, über die alle Seiten der App erreichbar sind.

## Projektstruktur
```
StreamliteApp/
├── Startseite.py        # Einstiegsseite der Anwendung
├── pages/               # Weitere Streamlit-Seiten
├── sports_league.sqlite # SQLite-Datenbank mit Spieldaten
└── requirements.txt     # Benötigte Python-Pakete
```

## Hinweise
- Die Datenbank `sports_league.sqlite` enthält alle benötigten Daten. Sie muss sich im selben Verzeichnis wie die Python-Skripte befinden.
- Das Projekt wurde mit Python 3 und den in `requirements.txt` aufgeführten Paketen entwickelt.
- 
