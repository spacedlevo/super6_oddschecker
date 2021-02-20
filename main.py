import requests
from bs4 import BeautifulSoup
import re
import sqlite3 as sql
import os
from dotenv import load_dotenv
import sys


BASE_URL = 'https://super6.skysports.com/api/v2/'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
DB = 'super6.db'
load_dotenv()
USERNAME = os.getenv('USERNAME')
PIN = os.getenv('PIN')



def get_team_name(team_id):
    with sql.connect(DB) as con:
        cur = con.cursor()
        cur.execute( ''' SELECT name FROM teams WHERE id = ? ''', (team_id,))
        return cur.fetchone()[0]

def get_competiton_name(competition_id):
    with sql.connect(DB) as con:
        cur = con.cursor()
        cur.execute( ''' SELECT name FROM competitions WHERE id = ? ''', (competition_id,))
        return cur.fetchone()[0]

def check_draw(fixture):
    goals = parse_score(fixture)
    if goals[0] == goals[1]:
        return True
    else:
        return False

def parse_score(score):
    score_regex = re.compile(r'\d-\d')
    result = score_regex.findall(score)
    result = result[0].split('-')
    return result        

def get_round_info():
    end_point = 'round/active'
    r = s.get(f"{BASE_URL}{end_point}")
    return r.json()

def get_fav_odds(round_data):
    base = 'http://www.oddschecker.com/football/'
    competiton = get_competiton_name(int(round_data['competitionId']))
    home_team = get_team_name(round_data['homeTeam']['id'])
    away_team = get_team_name(round_data['awayTeam']['id'])
    home_team = home_team.replace(' ','-')
    away_team = away_team.replace(' ','-')
    competiton = competiton.replace(' ','-')
    if competiton != 'champions-league':
        base += 'english/'
    print(f"Trying: {base}{competiton}/{home_team}-v-{away_team}/correct-score")
    url = f"{base}{competiton}/{home_team}-v-{away_team}/correct-score"

    try:
        r = s.get(url, headers=HEADERS)
    except Exception as e:
        print(e)


    soup = BeautifulSoup(r.content, "html.parser")
    tableData = soup.find_all("td", class_="sel nm basket-active")
    for row in tableData:
        print(row.text.strip())
        try:
            if check_draw(row.text.strip()):
                continue
            elif row.text.strip().lower == 'any other score':
                continue
            else:
                score = row.text.strip()
                break
        except IndexError:
            continue
    return score

def sort_scores(score, game):
    team_re = re.compile(r'^\D+')
    winner = team_re.findall(score)[0].strip().lower()
    score_re = re.compile(r'\d')
    goals = score_re.findall(score)
    goals_int = [int(i) for i in goals]
    with sql.connect(DB) as con:
        cur = con.cursor()
        cur.execute(''' SELECT id FROM teams WHERE name = ?  ''', (winner, ))
        winner_id = cur.fetchone()[0]
    if game['homeTeam']['id'] ==  winner_id:
        return max(goals_int), min(goals_int)
    else:
        return min(goals_int), max(goals_int)

def post_predictions(data):
    login_url = "https://www.skybet.com/secure/identity/m/login/super6"
    params = {"username": USERNAME, "pin": PIN}
    headers = {"X-Requested-With": "XMLHttpRequest"}
    p = s.post(login_url, json=params, headers=headers).json()

    try:
        sso_token = p["user_data"]["ssoToken"]
    except KeyError:
        print("\nYour username or password is incorrect\n")
        sys.exit(1)
    headers = {"authorization": f"sso {sso_token}"}

    predictions_url = 'https://api.s6.sbgservices.com/v2/user/self/prediction'
    s.post(predictions_url, json=data, headers=headers)


if __name__ == "__main__":
    data = {}
    data["scores"] = []
    with requests.Session() as s:
        active_round = get_round_info()
        matches = active_round['scoreChallenges']
        for game in matches:
            predictions = {}
            predictions['challengeId'] = game['id']
            score = get_fav_odds(game['match'])
            predictions['scoreHome'], predictions['scoreAway'] = sort_scores(score, game['match'])
            data['scores'].append(predictions)


    data['goldenGoal'] = {
        'challengeId': active_round['goldenGoalChallenge']['id'],
        "time":11
    }
    data["headToHeadEnter"] = True
    post_predictions(data)


