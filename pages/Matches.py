import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="Matches", page_icon="📅", layout="wide")

st.title("Matches Übersicht")

# Verbindung zur Datenbank herstellen
conn = sqlite3.connect('sports_league.sqlite', check_same_thread=False)


def recalc_standings(conn: sqlite3.Connection, league_id: int, season_id: int) -> None:
    """Recalculate the standings table for the given league/season."""
    teams = pd.read_sql(
        "SELECT team_id FROM teams WHERE league_id = ?", conn, params=(league_id,)
    )
    stats = pd.DataFrame(index=teams["team_id"].tolist())
    for col in [
        "played_games",
        "won",
        "draw",
        "lost",
        "points",
        "goals_for",
        "goals_against",
    ]:
        stats[col] = 0

    matches = pd.read_sql(
        """
        SELECT m.home_team_id, m.away_team_id, s.full_time_home, s.full_time_away
        FROM matches m
        JOIN scores s ON m.match_id = s.match_id
        WHERE m.league_id = ? AND m.season_id = ?
        """,
        conn,
        params=(league_id, season_id),
    )

    for _, m in matches.iterrows():
        h, a = int(m.home_team_id), int(m.away_team_id)
        gh, ga = int(m.full_time_home), int(m.full_time_away)
        stats.at[h, "played_games"] += 1
        stats.at[a, "played_games"] += 1
        stats.at[h, "goals_for"] += gh
        stats.at[h, "goals_against"] += ga
        stats.at[a, "goals_for"] += ga
        stats.at[a, "goals_against"] += gh
        if gh > ga:
            stats.at[h, "won"] += 1
            stats.at[a, "lost"] += 1
            stats.at[h, "points"] += 3
        elif gh < ga:
            stats.at[a, "won"] += 1
            stats.at[h, "lost"] += 1
            stats.at[a, "points"] += 3
        else:
            stats.at[h, "draw"] += 1
            stats.at[a, "draw"] += 1
            stats.at[h, "points"] += 1
            stats.at[a, "points"] += 1

    stats["goal_difference"] = stats["goals_for"] - stats["goals_against"]
    stats = (
        stats.reset_index()
        .rename(columns={"index": "team_id"})
        .sort_values(
            ["points", "goal_difference", "goals_for"], ascending=False
        )
        .reset_index(drop=True)
    )
    stats["position"] = range(1, len(stats) + 1)

    for row in stats.itertuples(index=False):
        conn.execute(
            """
            UPDATE standings
            SET season_id = ?, played_games = ?, won = ?, draw = ?, lost = ?,
                points = ?, goals_for = ?, goals_against = ?, goal_difference = ?,
                position = ?
            WHERE league_id = ? AND team_id = ?
            """,
            (
                season_id,
                row.played_games,
                row.won,
                row.draw,
                row.lost,
                row.points,
                row.goals_for,
                row.goals_against,
                row.goal_difference,
                row.position,
                league_id,
                row.team_id,
            ),
        )

    conn.commit()

# Alle Teams und Ligen laden
teams_df = pd.read_sql("SELECT team_id, league_id, name FROM teams ORDER BY name", conn)
team_names = teams_df['name'].tolist()
leagues_df = pd.read_sql("SELECT league_id, name FROM leagues ORDER BY name", conn)

with st.expander("Neues Match anlegen"):
    league_selection = st.selectbox(
        "Liga wählen",
        options=leagues_df.itertuples(index=False),
        format_func=lambda x: x.name,
    )
    league_teams = teams_df[teams_df["league_id"] == league_selection.league_id]
    with st.form("add_match"):
        matchday = st.number_input("Spieltag", min_value=1, step=1)
        team_cols = st.columns(2)
        with team_cols[0]:
            home_selection = st.selectbox(
                "Heimmannschaft",
                options=league_teams.itertuples(index=False),
                format_func=lambda x: x.name,
            )
        with team_cols[1]:
            away_selection = st.selectbox(
                "Auswärtsmannschaft",
                options=league_teams.itertuples(index=False),
                format_func=lambda x: x.name,
            )
        match_date = st.date_input("Datum")
        score_cols = st.columns(2)
        with score_cols[0]:
            full_home = st.number_input("Tore Heimteam", min_value=0, step=1)
        with score_cols[1]:
            full_away = st.number_input("Tore Auswärtsteam", min_value=0, step=1)
        submitted = st.form_submit_button("Match hinzufügen")
        if submitted:
            if home_selection.team_id == away_selection.team_id:
                st.error("Heim- und Auswärtsteam müssen unterschiedlich sein")
            else:
                league_id = league_selection.league_id
                home_id = home_selection.team_id
                away_id = away_selection.team_id
                season_row = pd.read_sql(
                    "SELECT season_id FROM seasons WHERE league_id = ? ORDER BY year DESC LIMIT 1",
                    conn,
                    params=(league_id,),
                )
                season_id = int(season_row.iloc[0]["season_id"]) if not season_row.empty else None
                max_match = pd.read_sql("SELECT MAX(match_id) AS m FROM matches", conn)["m"].iloc[0]
                new_match_id = 1 if pd.isna(max_match) else int(max_match) + 1
                max_score = pd.read_sql("SELECT MAX(score_id) AS m FROM scores", conn)["m"].iloc[0]
                new_score_id = 1 if pd.isna(max_score) else int(max_score) + 1
                if full_home > full_away:
                    winner = "HOME_TEAM"
                elif full_home < full_away:
                    winner = "AWAY_TEAM"
                else:
                    winner = "DRAW"
                conn.execute(
                    "INSERT INTO matches (match_id, season_id, league_id, matchday, home_team_id, away_team_id, winner, utc_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        new_match_id,
                        season_id,
                        league_id,
                        int(matchday),
                        home_id,
                        away_id,
                        winner,
                        match_date.isoformat(),
                    ),
                )
                conn.execute(
                    "INSERT INTO scores (score_id, match_id, full_time_home, full_time_away, half_time_home, half_time_away) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        new_score_id,
                        new_match_id,
                        int(full_home),
                        int(full_away),
                        0,
                        0,
                    ),
                )
                conn.commit()
                recalc_standings(conn, league_id, season_id)
                st.success("Match hinzugefügt")
                st.rerun()

col1, col2 = st.columns(2)
with col1:
    home_team = st.selectbox("Heimmannschaft", ["Alle"] + team_names)
with col2:
    away_team = st.selectbox("Auswärtsmannschaft", ["Alle"] + team_names)

# Alle Spiele laden
query = """
    SELECT
        m.match_id,
        m.league_id,
        m.season_id,
        l.name AS league,
        ht.name AS home_team,
        at.name AS away_team,
        s.full_time_home AS home_goals,
        s.full_time_away AS away_goals,
        m.utc_date
    FROM matches AS m
    JOIN teams AS ht ON m.home_team_id = ht.team_id
    JOIN teams AS at ON m.away_team_id = at.team_id
    JOIN scores AS s ON m.match_id = s.match_id
    JOIN leagues AS l ON m.league_id = l.league_id
    ORDER BY datetime(m.utc_date) DESC
"""

matches_df = pd.read_sql(query, conn)

# DataFrame filtern
filtered_df = matches_df.copy()
if home_team != "Alle":
    filtered_df = filtered_df[filtered_df["home_team"] == home_team]
if away_team != "Alle":
    filtered_df = filtered_df[filtered_df["away_team"] == away_team]

# Spalten beschriften
filtered_df = filtered_df.rename(
    columns={
        "league": "Liga",
        "home_team": "Heimteam",
        "away_team": "Auswärtsteam",
        "utc_date": "Datum",
    }
)

filtered_df["Ergebnis"] = (
    filtered_df["home_goals"].astype(str) + " - " + filtered_df["away_goals"].astype(str)
)

display_df = filtered_df[["Heimteam", "Ergebnis", "Auswärtsteam", "Datum", "Liga"]]

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
    if st.button("Match löschen", type="primary"):
        conn.execute("DELETE FROM scores WHERE match_id = ?", (int(info["match_id"]),))
        conn.execute("DELETE FROM matches WHERE match_id = ?", (int(info["match_id"]),))
        conn.commit()
        recalc_standings(conn, int(info["league_id"]), int(info["season_id"]))
        st.success("Match gelöscht")
        st.rerun()
