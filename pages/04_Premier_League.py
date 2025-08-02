import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(
    page_title="Premier League",
    page_icon="https://crests.football-data.org/PL.png",
    layout="wide",
)

# Bild mit Text
image = "https://ethianum-klinik-heidelberg.de/wp-content/uploads/2024/01/header-sportorthopaedie_fussball_2400x824px.webp"
st.markdown(f"""
<div style="position: relative; text-align: center;">
    <img src="{image}" style="width: 100%; border-radius: 10px;" />
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
        Premier League Ergebnisse
    </div>
</div>
""", unsafe_allow_html=True)

# Abstand und Text darunter
st.markdown("---")
st.subheader("Tabelle der Premier League")

# Datenbankverbindung herstellen
conn = sqlite3.connect('sports_league.sqlite')

LEAGUE_ID = 1

# Informationen zur Liga (CL-, Europa- und Abstiegsränge)
league_info = pd.read_sql(
    f"SELECT cl_spot, uel_spot, relegation_spot FROM leagues WHERE league_id = {LEAGUE_ID}",
    conn,
).iloc[0]

# Tabelle laden
standings_df = pd.read_sql(
    f"""
    SELECT *
    FROM standings
    WHERE league_id = {LEAGUE_ID}
    ORDER BY points DESC, goal_difference DESC
""",
    conn,
)
standings_df["position"] = range(1, len(standings_df) + 1)

teams_df = pd.read_sql("SELECT team_id, name, cresturl FROM teams", conn)

# Tabelle vorbereiten
pl_table = (
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

pl_table["Logo"] = pl_table["cresturl"].apply(
    lambda url: f"<img src='{url}' style='height:40px; width:auto; object-fit:contain;'>"
)
pl_table = pl_table.drop(columns=["cresturl"])

pl_table = pl_table[
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
pl_table = pl_table.rename(columns={"Logo": ""}).reset_index(drop=True)

# Zeilen einfärben

def highlight_row(row):
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
    pl_table.style.apply(highlight_row, axis=1)
    .hide(axis="index")
    .set_table_styles([
        {"selector": "th", "props": "text-align:center; background-color:#f0f0f0;"},
        {"selector": "td", "props": "text-align:center;"},
        {"selector": "table", "props": "border-collapse:collapse;"},
    ])
)

table_html = styled_df.to_html(escape=False)
centered_html = f"""
<div style="display: flex; justify-content: center;">
    {table_html}
</div>
"""
st.markdown(centered_html, unsafe_allow_html=True)

st.markdown("---")

# Spieltagauswahl
max_matchday = pd.read_sql(
    f"SELECT MAX(matchday) as m FROM matches WHERE league_id = {LEAGUE_ID}",
    conn,
)["m"].iloc[0]

if "pl_matchday" not in st.session_state:
    st.session_state.pl_matchday = 1
if "pl_selectbox" not in st.session_state:
    st.session_state.pl_selectbox = st.session_state.pl_matchday


def sync_selectbox():
    """Update matchday when the selectbox changes."""
    st.session_state.pl_matchday = st.session_state.pl_selectbox


def prev_matchday():
    """Go to the previous matchday."""
    if st.session_state.pl_matchday > 1:
        st.session_state.pl_matchday -= 1
        st.session_state.pl_selectbox = st.session_state.pl_matchday


def next_matchday():
    """Go to the next matchday."""
    if st.session_state.pl_matchday < max_matchday:
        st.session_state.pl_matchday += 1
        st.session_state.pl_selectbox = st.session_state.pl_matchday


col_prev, col_mid, col_next = st.columns(3)
with col_prev:
    st.button(
        "Vorheriger Spieltag",
        use_container_width=True,
        on_click=prev_matchday,
    )
with col_mid:
    st.markdown(
        f"<h3 style='text-align:center'>Spieltag {st.session_state.pl_matchday}</h3>",
        unsafe_allow_html=True,
    )
with col_next:
    st.button(
        "Nächster Spieltag",
        use_container_width=True,
        on_click=next_matchday,
    )

st.selectbox(
    "Spieltag auswählen",
    list(range(1, int(max_matchday) + 1)),
    index=st.session_state.pl_matchday - 1,
    key="pl_selectbox",
    on_change=sync_selectbox,
)

# Spiele des gewählten Spieltags laden
query_matches = f"""
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
    WHERE matches.league_id = {LEAGUE_ID}
      AND matches.matchday = {st.session_state.pl_matchday}
    ORDER BY datetime(matches.utc_date) ASC
"""

md_matches_df = pd.read_sql(query_matches, conn)

for _, row in md_matches_df.iterrows():
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
