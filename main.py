import os
import re
import sqlite3 as sql
import sys

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

BASE_URL = 'https://super6.skysports.com/api/v2/'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
DB = 'super6.db'
load_dotenv()
USERNAME = os.getenv('USERNAME')
PIN = os.getenv('PIN')
PUSHOVER_TOKEN = os.getenv('PUSHOVER_TOKEN')
PUSHOVER_USER = os.getenv('PUSHOVER_USER')

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
    non_english = ['champions-league', 'euro-2020']
    base = 'http://www.oddschecker.com/football/'
    competiton = get_competiton_name(int(round_data['competitionId']))
    home_team = get_team_name(round_data['homeTeam']['id'])
    away_team = get_team_name(round_data['awayTeam']['id'])
    home_team = home_team.replace(' ','-')
    away_team = away_team.replace(' ','-')
    competiton = competiton.replace(' ','-')
    if competiton not in non_english:
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
                score = score.replace('Nottm', 'Nottingham')
                score = score.replace('Oxford Utd', 'Oxford')
            return score
        except UnboundLocalError:
            print('skipping')
            return None

def sort_scores(score, game):
    team_re = re.compile(r'^\D+')
    winner = team_re.findall(score)[0].strip().lower()
    score_re = re.compile(r'\d')
    goals = score_re.findall(score)
    goals_int = [int(i) for i in goals]
    with sql.connect(DB) as con:
        cur = con.cursor()
        cur.execute(" SELECT id FROM teams WHERE name LIKE ? ", (winner+'%', ))
        winner_id = cur.fetchone()[0]
    if game['homeTeam']['id'] ==  winner_id:
        return max(goals_int), min(goals_int)
    else:
        return min(goals_int), max(goals_int)

def post_predictions(data):
    login_url = "https://www.skybet.com/secure/identity/m/login/super6"
    params = {"username": USERNAME, "pin": PIN}
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36', "X-Requested-With": "XMLHttpRequest"}
    p = s.post(login_url, json=params, headers=headers).json()

    try:
        sso_token = p["user_data"]["ssoToken"]
    except KeyError:
        print("\nYour username or password is incorrect\n")
        sys.exit(1)
    headers = {"authorization": f"sso {sso_token}"}

    predictions_url = 'https://api.s6.sbgservices.com/v2/user/self/prediction'
    r = s.post(predictions_url, json=data, headers=headers)
    return r

def send_alert():
    text = 'Super 6 Script Failed, needs attention'
    payload = {"message": text, "user": PUSHOVER_USER, "token": PUSHOVER_TOKEN }
    r = requests.post('https://api.pushover.net/1/messages.json', data=payload, headers={'User-Agent': 'Python'})
    return r


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
            if score is None:
                continue
            else:
                predictions['scoreHome'], predictions['scoreAway'] = sort_scores(score, game['match'])
                data['scores'].append(predictions)


    data['goldenGoal'] = {
        'challengeId': active_round['goldenGoalChallenge']['id'],
        "time":11
    }
    data["headToHeadEnter"] = True
    r = post_predictions(data)
    print(r.status_code)
    if r.status_code != 201:
        send_alert()


