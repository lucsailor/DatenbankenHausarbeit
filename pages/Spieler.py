import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="Spieler", page_icon="⚽", layout="wide")

st.title("Spieler Übersicht")

# Verbindung zur Datenbank herstellen
conn = sqlite3.connect('sports_league.sqlite', check_same_thread=False)

def load_players(conn):
    return pd.read_sql(
    """
    SELECT p.player_id, p.name, p.position, p.date_of_birth, p.nationality, t.name AS team, t.cresturl
    FROM players AS p
    JOIN teams AS t ON p.team_id = t.team_id
    ORDER BY p.name
    """,
    conn,
)

# Alle Spieler mit Teamnamen laden
players_df = load_players(conn)

# Dropdown-Optionen vorbereiten
teams_df = pd.read_sql("SELECT team_id, name FROM teams ORDER BY name", conn)
positions = sorted(players_df["position"].dropna().unique().tolist())
nationalities = sorted(players_df["nationality"].dropna().unique().tolist())

with st.expander("Neuen Spieler anlegen"):
    with st.form("add_player"):
        new_name = st.text_input("Name")
        team_selection = st.selectbox(
            "Team wählen",
            options=teams_df.itertuples(index=False),
            format_func=lambda x: x.name  # zeigt nur Namen an, gibt aber das ganze Tupel zurück
        )
        new_position = st.selectbox("Position", positions, index=0)
        new_nationality = st.selectbox("Nationalität", nationalities, index=0)
        birth_date = st.date_input(
            "Geburtsdatum",
            min_value=pd.Timestamp(1900, 1, 1),
            max_value=pd.Timestamp.now().date(),
        )
        submitted = st.form_submit_button("Spieler hinzufügen")
        if submitted:
            if new_name:
                team_id = team_selection.team_id
                # Neuen eindeutigen Spieler-ID bestimmen
                max_id = pd.read_sql("SELECT MAX(player_id) AS m FROM players", conn)["m"].iloc[0]
                new_player_id = 1 if pd.isna(max_id) else int(max_id) + 1
                conn.execute(
                    "INSERT INTO players (player_id, team_id, name, position, date_of_birth, nationality) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        new_player_id,
                        team_id,
                        new_name,
                        new_position,
                        birth_date.isoformat(),
                        new_nationality,
                    ),
                )
                conn.commit()
                # Nach dem Speichern sofort aktualisieren
                players_df = load_players(conn)
                st.session_state["players_df"] = players_df
                st.success("Spieler hinzugefügt")
                st.rerun()
            else:
                st.error("Name darf nicht leer sein")

search = st.text_input("Nach Spieler suchen")

filtered_df = players_df[players_df["name"].str.contains(search, case=False, na=False)]

# Spaltenbeschriftungen fuer die Anzeige anpassen
display_df = (
    filtered_df
    .rename(
        columns={
            "name": "Name",
            "team": "Mannschaft",
            "position": "Position",
            "nationality": "Nationalität",
            "date_of_birth": "Geburtsdatum",
        }
    )[
        ["Name", "Mannschaft", "Position", "Nationalität", "Geburtsdatum"]
    ]
)

event = st.dataframe(
    display_df,
    hide_index=True,
    use_container_width=True,
    on_select="rerun",
    selection_mode="single-row",
)

if getattr(event, "selection", None) and event.selection.rows:
    row_index = event.selection.rows[0]
    info = filtered_df.iloc[row_index]
    age = int((pd.Timestamp.now() - pd.to_datetime(info["date_of_birth"])).days // 365)
    st.markdown("---")
    st.subheader("Spielerinformationen")

    st.image(info["cresturl"], width=60)
    st.markdown(f"**Name:** {info['name']}")
    st.markdown(f"**Team:** {info['team']}")
    st.markdown(f"**Position:** {info['position']}")
    st.markdown(f"**Geburtsdatum:** {info['date_of_birth']}")
    st.markdown(f"**Nationalität:** {info['nationality']}")
    st.markdown(
        f"{info['name']} ist {age} Jahre alt und spielt aktuell im {info['position']} von {info['team']}.",
    )

    if st.button("Spieler löschen", type="primary"):
        conn.execute(
            "DELETE FROM players WHERE player_id = ?",
            (int(info["player_id"]),),
        )
        conn.commit()
        st.success("Spieler gelöscht")
        st.rerun()

