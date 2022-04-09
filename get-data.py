
from sportsipy.mlb.schedule import Game
from sportsipy.mlb.boxscore import Boxscore, BoxscorePlayer
from sportsipy.mlb.roster import Player
import pandas as pd
from bs4 import BeautifulSoup
import requests
import datetime
from unidecode import unidecode
import re
import json
from pprint import pprint

import utils

GAME_DATA = 'data/game-data.json'
PITCHING_DATA = 'data/pitching-data.json'

session = requests.Session()

def remove_headers(soup):
    """
    Removes the repetitive stat headers that occur throughout the season table
    """
    headers = soup.find_all('tr', class_='thead')
    for header in headers:
        header.extract()


def add_game_id(box_score, game_id):
    """
    Adds the game id used for the box score uri. 
    Normal game = 0, first game of DH = 1, second game of DH = 2
    """
    box_score['game_id'] = game_id


def add_location(row):
    """
    Adds the location (home or away) to the row of other game stats.
    """
    if row[2] == '@':
        row[2] = int(False)
    else:
        row.insert(2, int(True))


def add_date(row, year):
    """
    Adds the date to the row of other game stats. Combines the first two values in 'row'.
    row: ['Apr', '1', ...] ---> ['2021-04-01', ...]
    """
    date = str(datetime.date(year, utils.MONTHS[row[0]], int(row[1])))
    row[0] = date
    row.pop(1)


def add_yesterday_off(box_score, season_games, team_abbr):
    """
    Adds whether or not the specified team had an off day.
    """
    y_m_d = box_score['date'].split('-')
    date = datetime.date(int(y_m_d[0]), int(y_m_d[1]), int(y_m_d[2]))
    day_before = utils.get_day_before(date)
    box_score['yesterday_off'] = int(team_abbr not in season_games or day_before not in season_games[team_abbr])


def add_opp_starter(box_score):
    """
    Add the opponent starter and his throwing hand.
    """
    starter = box_score['opp_starter']
    box_score['opp_starter'] = starter[:starter.find('(')]
    hand = box_score['opp_starter_righty']
    box_score['opp_starter_righty'] = float(hand == 'R')


def convert_to_floats(box_score):
    """
    Convert stat types from string to float.
    {'RBI': '7'} ---> {'RBI': 7.0}
    """
    for category in box_score:
        try:
            box_score[category] = float(box_score[category])
        except:
            pass


def add_is_night_game(season_games, team_abbr, date, is_night):
    """
    Adds whether or not the game is at night for both teams for a given game. 
    """
    opp_abbr = season_games[team_abbr][date]['opp']
    season_games[team_abbr][date]['night'] = is_night
    season_games[opp_abbr][date]['night'] = is_night


def should_skip(row):
    """
    Return true if the game is either the second of a doubleheader,
    or the game was suspended. Only including the first game of 
    a doublheader for simplicity.
    """
    return '(2)' in row[:5] or 'susp' in row[:5]


def get_night_game(game_page):
    """
    Returns true if the game took place at night (7:00 pm local start)
    """
    return float(game_page.find(text=re.compile('Night Game')) != None)


def get_temperature(game_page):
    """
    Parse for and return the game time temperature.
    """
    weather = game_page.find('', text=re.compile('&deg'))
    degrees = weather.find('&deg')
    temp = int(weather[degrees-3:degrees].strip())
    return temp


def away_table_finished(line):
    """
    Return true if keywords that indicate the end of a pitching table
    has been reached are found.
    """
    return 'Team Totals' in line and 'data-stat="ER"' in line


def dump_data(file, dict):
    """
    Dump the dictionary of games into a json file.
    """
    with open(file, 'w') as f:
        f.seek(0)
        f.truncate(0)
        json.dump(dict, f, indent=4)


def scrape_offensive_data(team_abbr, year):
    """
    Adds a team's desired boxscore values for each game in the specified season.
    Adds the desired stats from each row listed here: 
    https://www.baseball-reference.com/teams/tgl.cgi?team=BOS&t=b&year=2021'
    """
    season_page = session.get(f'https://www.baseball-reference.com/teams/tgl.cgi?team={team_abbr}&t=b&year={year}').text
    soup = BeautifulSoup(season_page, 'lxml')
    remove_headers(soup)
    table = soup.find(id='team_batting_gamelogs').select('tbody')
    season = table[0].get_text(separator=' ').split('\n')
    season = [row.split()[2:] for row in season if len(row) > 1]

    # dict to fill with stats
    season_games = {}
    for game in season:
        if should_skip(game):
            utils.print_game(False)
            continue
        if '(1)' in game[:4]:
            game.pop(game.index('(1)'))
        
        add_location(game)
        add_date(game, year)
        box_score = {utils.HITTING_STATS[i]:game[i] for i in range(len(utils.HITTING_STATS)) if utils.HITTING_STATS[i] in utils.STATS_TO_USE}
        add_yesterday_off(box_score, season_games, team_abbr)
        add_opp_starter(box_score)
        convert_to_floats(box_score)

        date = box_score['date']
        season_games[date] = box_score
        utils.print_game(True)

    return season_games


def parse_pitcher_stats(line):
    """
    Parse the boxscore page for pitcher stats. Return a map of each 
    pitcher's stats for that game.
    """
    csv = line.find('data-append-csv="')+17
    shtml = line.find('.shtml')
    player_id = line[csv : line.find('"', csv)].strip()
    player_name = line[line.find('>', shtml)+1:line.find('<', shtml)].strip()
    game_stats = {
        'name': player_name,
        'id': player_id, 
    }
    for stat in utils.PITCHING_STATS:
        i = line.find(f'data-stat="{stat}"')
        num = float(line[line.find('>', i)+1:line.find('<', i)].strip())
        game_stats[stat] = num

    return game_stats


def add_pitcher_stats(stats, opp, date, pitcher_data, season_games):
    """
    Adds a pitcher's game stats to the dictionary containing all of the pitcher
    data. pitcher_data dict in the form of:

    pitcher_data['verlaju01'] = {'2015-05-13': {stats}, '2015-05-18': {stats}}

    Also adds the starter's player_id to dictionary of season games, under the 
    appropriate game for the starter's opponent.
    """
    player_id = stats['id']
    if player_id not in pitcher_data:
        pitcher_data[player_id] = {}

    pitcher_data[player_id][date] = {'opp': opp}
    for cat in utils.PITCHING_STATS:
        pitcher_data[player_id][date][cat] = stats[cat]

    if 'opp_starter_id' not in season_games[opp][date]:
        season_games[opp][date]['opp_starter_id'] = stats['id']


def get_starters(soup):
    """
    Returns a len-2 list containing each starter's name and id.

    [('Lucas Giolito', 'giolilu01'), ('Dylan Bundy', 'bundydy01')]
    """
    lineups = str(soup.find('div', id='all_lineups')).split('\n')
    starters = []
    for i in range(len(lineups)):
        if '<td>P</td>' in lineups[i]:
            line = lineups[i-1].strip()
            shtml = line.find('.shtml')
            name = line[shtml+8:line.find('<', shtml)]
            last_initial = name.split()[1][0].lower()
            id = line[line.find(f'players/{last_initial}/')+10:shtml]
            starters.append((name, id))
            if len(starters) == 2:
                break
    return starters[0], starters[1]


def scrape_pitching_data(year, season_games):
    """
    Scrape all of the desired pitching data from the given year and load
    a dictionary containing all of the stats into a json file. Also add some 
    information about the game like temperature and time.
    """
    schedule_page = session.get(f'https://www.baseball-reference.com/leagues/majors/{year}-schedule.shtml').text
    soup = BeautifulSoup(schedule_page, 'lxml')
    schedule = soup.find_all('p', class_='game')
    
    pitcher_data = {}
    for game in schedule:
        game_id = game.select('a')[2].get('href')
        game_page = session.get('https://www.baseball-reference.com/' + game_id).text
        soup = BeautifulSoup(game_page, 'lxml')
    
        if utils.is_playoffs(soup):
            break
        if utils.is_second_game(soup) or utils.was_suspended(soup):
            print('skipping')
            continue
        
        away_starter, home_starter = get_starters(soup)
        date, away_abbr, home_abbr = utils.parse_title(soup.title.text)
        season_games[away_abbr][date]['opp_starter_name'] = home_starter[0]
        season_games[away_abbr][date]['opp_starter_id'] = home_starter[1]
        season_games[home_abbr][date]['opp_starter_name'] = away_starter[0]
        season_games[home_abbr][date]['opp_starter_id'] = away_starter[1]

        night_game = get_night_game(soup)
        temp = get_temperature(soup)
        season_games[home_abbr][date]['night_game'] = night_game
        season_games[away_abbr][date]['night_game'] = night_game
        season_games[home_abbr][date]['temp'] = temp
        season_games[away_abbr][date]['temp'] = temp

        opp = home_abbr
        for line in game_page.split('\n'):
            if not utils.is_pitching_row(line):
                continue
            # finished with the away pitching table, now onto the home table
            if away_table_finished(line):
                opp = away_abbr
                continue
            stats = parse_pitcher_stats(line)
            add_pitcher_stats(stats, opp, date, pitcher_data, season_games)
            if away_table_finished(line) and opp == away_abbr:
                break
            
        print(date, f'- {away_abbr} @ {home_abbr}', utils.format.GREEN+utils.format.CHECK+utils.format.END)

    dump_data(PITCHING_DATA, pitcher_data)

        
def collect_pitching_data():
    """
    Collect pitching data from every game in the year range. 
    """
    print(utils.format.BOLD+utils.format.BLUE+f'\nCollecting pitching data from {utils.YEARS[0]}-{utils.YEARS[-1]}...\n'+utils.format.END)
    with open(GAME_DATA, 'r') as f:
        all_games = json.load(f)
        
    for year in utils.YEARS:
        print('==========', year, '==========')
        scrape_pitching_data(year, all_games[str(year)])

    dump_data(GAME_DATA, all_games)


def collect_offensive_data():
    """
    Collects offensive box score data from every game, stores it in a dictionary, and writes
    it to a json file. 

    Format of dict is: all_games['2021']['ATL']['2021-07-09'] = {box_score_stats}
    """
    print(utils.format.BOLD+utils.format.BLUE+f'\nCollecting hitting data from {utils.YEARS[0]}-{utils.YEARS[-1]}...\n'+utils.format.END)

    all_games = {}
    for year in utils.YEARS:
        print('==========', year, '==========')
        teams = utils.get_team_abbreviations(year)
        for team_abbr in teams:
            utils.print_team(team_abbr)
            season_games = scrape_offensive_data(team_abbr, year)
            if year not in all_games:
                all_games[year] = {}
            all_games[year][team_abbr] = season_games
            utils.print_check()

    dump_data(GAME_DATA, all_games)


def main():
    # 1) Collect offensive data
    collect_offensive_data()
    
    # 2) Collect pitching data
    collect_pitching_data()

    # 3) Calculate per-game/recent/season statisitcs 



if __name__ == '__main__':
    main()