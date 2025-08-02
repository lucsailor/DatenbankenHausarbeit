import streamlit as st
import sqlite3
import plotly.express as px
import pandas as pd

# Seiten Einstellungen
st.set_page_config(
    page_title="Datenbanken Hausarbeit",
    page_icon="https://crests.football-data.org/BL1.png",
    layout="wide",
)

# Bild mit Text
image = "https://ethianum-klinik-heidelberg.de/wp-content/uploads/2024/01/header-sportorthopaedie_fussball_2400x824px.webp",
st.markdown(f"""
<div style="position: relative; text-align: center;">
    <img src="https://ethianum-klinik-heidelberg.de/wp-content/uploads/2024/01/header-sportorthopaedie_fussball_2400x824px.webp" style="width: 100%; border-radius: 10px;" />
    <div style="
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background-color: rgba(0,0,0,0.6);
        color: white;
        padding: 1.2rem 2rem;
        border-radius: 8px;
        font-size: 2.2rem;
        font-weight: bold;
        z-index: 2;">
        Willkommen zur Fußball-Datenanalyse
    </div>
</div>
""", unsafe_allow_html=True)

# Abstand und Text darunter
st.markdown("---")
st.subheader("Willkommen auf unserer Datenanalyse-Plattform")
st.write("Hier analysieren wir die Top-5 Fußballligen Europas anhand echter Daten.")

conn = sqlite3.connect('sports_league.sqlite')

# Alle Ligen laden
leagues_df = pd.read_sql("SELECT league_id, name FROM leagues", conn)
league_names = leagues_df['name'].tolist()

# Session-State für aktive Liga
# Initialisiere den Liga-State
if "selected_league" not in st.session_state:
    st.session_state.selected_league = leagues_df["name"].tolist()[0]  # z. B. "Serie A"

cols = st.columns(len(league_names))

# Temporärer Speicher für Klick
clicked_league = None

for i, col in enumerate(cols):
    with col:
        if st.button(league_names[i], use_container_width=True):
            clicked_league = league_names[i]

# Nach der Schleife den Zustand aktualisieren (nur wenn geklickt)
if clicked_league:
    st.session_state.selected_league = clicked_league

# Dann verwendest du diesen Wert:
selected_league = st.session_state.selected_league

for i, col in enumerate(cols):
    with col:
        if league_names[i] == st.session_state.selected_league:
            st.markdown(
                f"""
                <div style='
                    position: relative;
                    top: -3.65rem;
                    padding: 0.6rem 0.5rem;
                    background-color: #0066cc;
                    color: white;
                    border-radius: 10px;
                    font-weight: bold;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                    text-align: center;
                    z-index: 999;
                    margin-bottom: -10.8rem;
                '>{league_names[i]}</div>
                """,
                unsafe_allow_html=True
            ) 



# Lookup: ID zur gewählten Liga finden
selected_league_id = leagues_df.loc[leagues_df["name"] == selected_league, "league_id"].values[0]

# Informationen zur Liga (CL-, Europa- und Abstiegsränge)
league_info = pd.read_sql(
    f"SELECT cl_spot, uel_spot, relegation_spot FROM leagues WHERE league_id = {selected_league_id}",
    conn,
).iloc[0]

# Tabelle laden
standings_df = pd.read_sql(
    f"""
    SELECT *
    FROM standings
    WHERE league_id = {selected_league_id}
    ORDER BY points DESC, goal_difference DESC
""",
    conn,
)
standings_df["position"] = range(1, len(standings_df) + 1)

# Teamnamen und Logos hinzufügen
teams_df = pd.read_sql("SELECT team_id, name, cresturl FROM teams", conn)
df = (
    standings_df
    .rename(
        columns={
            "position": "Platz",
            "played_games": "Spiele",
            "won": "Siege",
            "draw": "Unentschieden",
            "lost": "Niederlagen",
            "goal_difference": "Torverhältnis",
            "points": "Punkte",
        }
    )
    .merge(teams_df, on="team_id", how="left")
    .drop(columns=["team_id"])
    .rename(columns={"name": "Team"})
)

# Darstellung für Logos vorbereiten
# Die Bildgröße wird per CSS festgelegt, um ein Überlappen der Spalte zu vermeiden
df["Logo"] = df["cresturl"].apply(
    lambda url: f"<img src='{url}' style='height:40px; width:auto; object-fit:contain;'>"
)
df = df.drop(columns=["cresturl"])

# Spaltenreihenfolge definieren
df = df[
    [
        "Platz",
        "Logo",
        "Team",
        "Spiele",
        "Siege",
        "Unentschieden",
        "Niederlagen",
        "Torverhältnis",
        "Punkte",
    ]
]
df = df.rename(columns={"Logo": ""})
df = df.reset_index(drop=True)


def highlight_row(row):
    # After setting the index to "Platz" the column is no longer
    # available in the row data, so fall back to the row's index if
    # necessary.
    pos = row["Platz"] if "Platz" in row else row.name
    if pos <= league_info.cl_spot:
        return ["background-color:#e6ffe6"] * len(row)
    elif pos <= league_info.uel_spot:
        return ["background-color:#e6f0ff"] * len(row)
    elif pos >= league_info.relegation_spot:
        return ["background-color:#ffe6e6"] * len(row)
    else:
        return [""] * len(row)

styled_df = (
    df.style.apply(highlight_row, axis=1)
    .hide(axis="index")
    .set_table_styles(
        [
            {"selector": "th", "props": "text-align:center; background-color:#f0f0f0;"},
            {"selector": "td", "props": "text-align:center;"},
            {"selector": "table", "props": "border-collapse:collapse;"},
        ]
    )
)

# Daten anzeigen
table_html = styled_df.to_html(escape=False)
centered_html = f"""
<div style="display: flex; justify-content: center;">
    {table_html}
</div>
"""
st.markdown(centered_html, unsafe_allow_html=True)

st.markdown("---")
st.subheader("Letzte drei Spiele")

# Die letzten drei Spiele der gewählten Liga abrufen
query_last_matches = f"""
    SELECT
        leagues.name AS Liga,
        leagues.icon_url AS LigaIcon,
        home_team.name AS Heim,
        home_team.cresturl AS HeimCrest,
        away_team.name AS Auswaerts,
        away_team.cresturl AS AuswaertsCrest,
        scores.full_time_home AS HeimTore,
        scores.full_time_away AS AuswaertsTore,
        matches.utc_date AS Datum
    FROM matches
    JOIN teams AS home_team ON matches.home_team_id = home_team.team_id
    JOIN teams AS away_team ON matches.away_team_id = away_team.team_id
    JOIN scores ON matches.match_id = scores.match_id
    JOIN leagues ON matches.league_id = leagues.league_id
    WHERE matches.league_id = {selected_league_id}
    ORDER BY datetime(matches.utc_date) DESC
    LIMIT 3
"""

last_matches_df = pd.read_sql(query_last_matches, conn)

# Schöne Anzeige der letzten drei Spiele
for _, row in last_matches_df.iterrows():
    st.markdown(
        f"""
        <div style='background-color:#f9f9f9; padding:1rem; border-radius:10px; margin-bottom:1rem;'>
            <div style='display:flex; justify-content:center; align-items:center; font-weight:bold;'>
                <div style='flex:1; text-align:right; margin-right:1rem;'>
                    <img src='{row['HeimCrest']}' width='40'><br>{row['Heim']}
                </div>
                <div style='margin:0 1rem; font-size:1.5rem;'>{row['HeimTore']} : {row['AuswaertsTore']}</div>
                <div style='flex:1; text-align:left; margin-left:1rem;'>
                    <img src='{row['AuswaertsCrest']}' width='40'><br>{row['Auswaerts']}
                </div>
            </div>
            <div style='text-align:center; font-size:0.9rem; margin-top:0.5rem;'>
                <img src='{row['LigaIcon']}' width='25' style='vertical-align:middle;'> {row['Liga']} - {row['Datum']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
