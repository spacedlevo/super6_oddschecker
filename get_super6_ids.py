import requests
import sqlite3 as sql
import time



BASE_URL = 'https://api.s6.sbgservices.com/v2/round'
db_location = 'super6.db'

def get_round_ids():
    r = s.get(BASE_URL)
    round_data = r.json()
    return [i['id'] for i in round_data]

def get_round_data(round_id):
    r = s.get(f'{BASE_URL}/{round_id}')
    data = r.json()
    return data['scoreChallenges']

def add_team(team_id, name):
    name = name.lower()
    with sql.connect(db_location) as con:
        cur = con.cursor()
        cur.execute(''' SELECT id FROM teams WHERE id = ?''', (team_id,))
        q = cur.fetchone()
        if q is None:
            cur.execute(''' INSERT INTO teams (id, name) VALUES (?, ?)  ''', (team_id, name))
            print(f"Added {name}")

def add_competiton(competition_id, name):
    name = name.lower()
    with sql.connect(db_location) as con:
        cur = con.cursor()
        cur.execute(''' SELECT id FROM competitions WHERE id = ?''', (competition_id,))
        q = cur.fetchone()
        if q is None:
            cur.execute(''' INSERT INTO competitions (id, name) VALUES (?, ?)  ''', (competition_id, name))
            print(f"Added {name}")


if __name__ == "__main__":
    rounds = []
    with requests.Session() as s:
        round_ids = get_round_ids()

    for _id in round_ids:
        rounds.append(get_round_data(_id))
    
    for matches in rounds:
        for match in matches:
            teams = match['match']
            add_team(teams['homeTeam']['id'], teams['homeTeam']['name'])
            add_team(teams['awayTeam']['id'], teams['awayTeam']['name'])
            add_competiton(teams['competitionId'], teams['competitionName'])
            time.sleep(0.5)




