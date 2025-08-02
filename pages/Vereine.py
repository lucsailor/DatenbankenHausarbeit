import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Vereine", page_icon="🏟️", layout="wide")

st.title("Vereinsübersicht")

# Verbindung zur Datenbank herstellen
conn = sqlite3.connect('sports_league.sqlite', check_same_thread=False)

def load_teams(conn):
    return pd.read_sql(
        """
        SELECT t.team_id, t.name, t.founded_year, s.name AS stadium, s.location, s.capacity,
               c.name AS coach, t.cresturl
        FROM teams AS t
        LEFT JOIN stadiums AS s ON t.stadium_id = s.stadium_id
        LEFT JOIN coaches AS c ON t.coach_id = c.coach_id
        ORDER BY t.name
        """,
        conn,
    )

teams_df = load_teams(conn)

search_team = st.text_input("Nach Verein suchen")

filtered_teams = teams_df[teams_df["name"].str.contains(search_team, case=False, na=False)]

teams_display_df = (
    filtered_teams
    .rename(
        columns={
            "name": "Verein",
            "founded_year": "Gründungsjahr",
            "stadium": "Stadion",
            "coach": "Trainer",
        }
    )[
        ["Verein", "Gründungsjahr", "Stadion", "Trainer"]
    ]
)

team_event = st.dataframe(
    teams_display_df,
    hide_index=True,
    use_container_width=True,
    on_select="rerun",
    selection_mode="single-row",
    key="teams_table1",
)

if getattr(team_event, "selection", None) and team_event.selection.rows:
    row_index = team_event.selection.rows[0]
    info = filtered_teams.iloc[row_index]
    st.markdown("---")
    st.subheader("Vereinsinformationen")

    st.image(info["cresturl"], width=80)
    st.markdown(f"**Name:** {info['name']}")
    if pd.notna(info["founded_year"]):
        st.markdown(f"**Gegründet:** {int(info['founded_year'])}")
    else:
        st.markdown("**Gegründet:** unbekannt")

    stadium_line = info["stadium"] if pd.notna(info["stadium"]) else "Unbekanntes Stadion"
    details = []
    if pd.notna(info["location"]):
        details.append(info["location"])
    if pd.notna(info["capacity"]):
        details.append(f"Kapazität: {int(info['capacity'])}")
    if details:
        stadium_line += " (" + ", ".join(details) + ")"
    st.markdown(f"**Stadion:** {stadium_line}")

    st.markdown(f"**Trainer:** {info['coach'] if pd.notna(info['coach']) else 'unbekannt'}")

    players_df = pd.read_sql(
        f"""
        SELECT p.name, p.position, p.nationality, p.date_of_birth,
               t.name AS team, t.cresturl
        FROM players AS p
        JOIN teams AS t ON p.team_id = t.team_id
        WHERE p.team_id = {int(info['team_id'])}
        ORDER BY p.name
        """,
        conn,
    )

    st.subheader("Spieler des Vereins")
    search_player = st.text_input("Nach Spieler im Verein suchen")
    players_filtered = players_df[players_df["name"].str.contains(search_player, case=False, na=False)]

    players_display_df = (
        players_filtered
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

    player_event = st.dataframe(
        players_display_df,
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        key="players_table1",
    )

    if getattr(player_event, "selection", None) and player_event.selection.rows:
        row_index = player_event.selection.rows[0]
        player_info = players_filtered.iloc[row_index]
        age = int((pd.Timestamp.now() - pd.to_datetime(player_info["date_of_birth"])).days // 365)
        st.markdown("---")
        st.subheader("Spielerinformationen")

        st.image(player_info["cresturl"], width=60)
        st.markdown(f"**Name:** {player_info['name']}")
        st.markdown(f"**Team:** {player_info['team']}")
        st.markdown(f"**Position:** {player_info['position']}")
        st.markdown(f"**Geburtsdatum:** {player_info['date_of_birth']}")
        st.markdown(f"**Nationalität:** {player_info['nationality']}")
        st.markdown(
            f"{player_info['name']} ist {age} Jahre alt und spielt aktuell im {player_info['position']} von {player_info['team']}.",
        )

    standings_df = pd.DataFrame()
    try:
        standings_df = pd.read_sql(
            f"""
            SELECT SUM(played_games) AS games, SUM(won) AS wins, SUM(draw) AS draws,
                   SUM(lost) AS losses, SUM(points) AS points, SUM(goals_for) AS goals_for,
                   SUM(goals_against) AS goals_against
            FROM standings
            WHERE team_id = {int(info['team_id'])}
            """,
            conn,
        )
    except Exception:
        pass

    stats = None
    if not standings_df.empty and standings_df.loc[0, "games"] > 0:
        stats = standings_df.loc[0]
    else:
        matches_df = pd.read_sql(
            """
            SELECT m.home_team_id, m.away_team_id, s.full_time_home, s.full_time_away
            FROM matches AS m
            JOIN scores AS s ON m.match_id = s.match_id
            WHERE m.home_team_id = ? OR m.away_team_id = ?
            """,
            conn,
            params=(int(info['team_id']), int(info['team_id'])),
        )
        if not matches_df.empty:
            games = len(matches_df)
            wins = draws = losses = points = goals_for = goals_against = 0
            for _, row in matches_df.iterrows():
                if row["home_team_id"] == int(info["team_id"]):
                    gf, ga = row["full_time_home"], row["full_time_away"]
                else:
                    gf, ga = row["full_time_away"], row["full_time_home"]
                goals_for += gf
                goals_against += ga
                if gf > ga:
                    wins += 1
                    points += 3
                elif gf < ga:
                    losses += 1
                else:
                    draws += 1
                    points += 1
            stats = pd.Series(
                {
                    "games": games,
                    "wins": wins,
                    "draws": draws,
                    "losses": losses,
                    "points": points,
                    "goals_for": goals_for,
                    "goals_against": goals_against,
                }
            )

    st.markdown("---")
    if stats is not None and stats["games"] > 0:
        st.subheader(f"Statistiken von {info['name']}")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Ø Tore/Spiel", f"{stats['goals_for']/stats['games']:.2f}")
        with col2:
            st.metric("Ø Gegentore/Spiel", f"{stats['goals_against']/stats['games']:.2f}")
        with col3:
            st.metric("Punkte/Spiel", f"{stats['points']/stats['games']:.2f}")
        with col4:
            st.metric("Siegquote", f"{stats['wins']/stats['games']*100:.1f}%")

        pie_df = pd.DataFrame(
            {
                "Ergebnis": ["Siege", "Unentschieden", "Niederlagen"],
                "Anzahl": [stats["wins"], stats["draws"], stats["losses"]],
            }
        )
        pie_chart = px.pie(
            pie_df,
            values="Anzahl",
            names="Ergebnis",
            color="Ergebnis",
            color_discrete_map={
                "Siege": "#green",
                "Unentschieden": "#yellow",
                "Niederlagen": "red",
            },
        )
        st.plotly_chart(pie_chart, use_container_width=True)
    else:
        st.info("Keine Statistiken verfügbar.")
