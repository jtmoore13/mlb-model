
from sportsipy.mlb.teams import Teams
import sys
import datetime
import json
import re
import math
from colorama import Fore, Style

import get_data


CHECK = u'\u2713'
GREEN_CHECK = Fore.GREEN+CHECK+Style.RESET_ALL
DONE = Style.BRIGHT+'Done '+GREEN_CHECK+Style.RESET_ALL
LINE_UP = '\033[1A'
LINE_CLEAR = '\x1b[2K'
BACKSPACE = '\b'


STAT_CHANGES = {
    'date': 'date_game',
    'home': 'team_homeORaway',
    'opp': 'opp_ID',
    'opp_starter': 'opposing_starter',
    'opp_starter_righty': 'opposing_starter_throws',
    'postgame_BA': 'batting_avg',
    'postgame_OBP': 'onbase_perc',
    'postgame_OPS': 'onbase_plus_slugging',
    'postgame_SLG': 'slugging_perc'
}

TEAM_NAMES = {
    'ANA': 'Anaheim Angels',
    'ARI': 'Arizona Diamondbacks',
    'ATL': 'Atlanta Braves',
    'BAL': 'Baltimore Orioles', 
    'BOS': 'Boston Red Sox', 
    'CHW': 'Chicago White Sox', 
    'CHC': 'Chicago Cubs', 
    'CIN': 'Cincinnati Reds', 
    'CLE': 'Cleveland Indians',
    'COL': 'Colorado Rockies', 
    'DET': 'Detroit Tigers', 
    'HOU': 'Houston Astros', 
    'KCR': 'Kansas City Royals',
    'LAA': 'Los Angeles Angels',
    'LAD': 'Los Angeles Dodgers', 
    'MIA': 'Miami Marlins', 
    'MIL': 'Milwaukee Brewers', 
    'MIN': 'Minnesota Twins', 
    'NYM': 'New York Mets', 
    'NYY': 'New York Yankees', 
    'OAK': 'Oakland Athletics', 
    'PHI': 'Philadelphia Phillies', 
    'PIT': 'Pittsburgh Pirates', 
    'SDP': 'San Diego Padres', 
    'SFG': 'San Francisco Giants', 
    'SEA': 'Seattle Mariners', 
    'STL': 'St. Louis Cardinals', 
    'TBR': 'Tampa Bay Rays', 
    'TBD': 'Tampa Bay Devil Rays',
    'TEX': 'Texas Rangers', 
    'TOR': 'Toronto Blue Jays', 
    'WSN': 'Washington Nationals',
}

TEAM_ABBRS = {
    'Arizona Diamondbacks': 'ARI',
    'Atlanta Braves': 'ATL',
    'Baltimore Orioles': 'BAL',
    'Boston Red Sox': 'BOS',
    'Chicago Cubs': 'CHC',
    'Chicago White Sox': 'CHW',
    'Cincinnati Reds': 'CIN',
    'Cleveland Indians': 'CLE',
    'Cleveland Guardians': 'CLE',
    'Colorado Rockies': 'COL',
    'Detroit Tigers': 'DET',
    'Houston Astros': 'HOU',
    'Kansas City Royals': 'KCR',
    'Los Angeles Angels': 'LAA',
    'Los Angeles Angels of Anaheim': 'ANA',
    'Los Angeles Dodgers': 'LAD',
    'Florida Marlins': 'FLA',
    'Miami Marlins': 'MIA',
    'Milwaukee Brewers': 'MIL',
    'Minnesota Twins': 'MIN',
    'New York Mets': 'NYM',
    'New York Yankees': 'NYY',
    'Oakland Athletics': 'OAK',
    'Philadelphia Phillies': 'PHI',
    'Pittsburgh Pirates': 'PIT',
    'San Diego Padres': 'SDP',
    'San Francisco Giants': 'SFG',
    'Seattle Mariners': 'SEA',
    'St. Louis Cardinals': 'STL',
    'Tampa Bay Rays': 'TBR',
    'Tampa Bay Devil Rays': 'TBD',
    'Texas Rangers': 'TEX',
    'Toronto Blue Jays': 'TOR',
    'Washington Nationals': 'WSN'
}


STADIUM_SCORES = {
    'ARI': 1.044,
    'ATL': 1.063,
    'BAL': 1.088, 
    'BOS': 1.174, 
    'CHW': .995, 
    'CHC': .968, 
    'CIN': 1.162, 
    'CLE': .984,
    'COL': 1.334, 
    'DET': .970, 
    'HOU': 1.005, 
    'KCR': 1.103,
    'LAA': 1.068,
    'LAD': .928, 
    'MIA': .982, 
    'FLA': .982,
    'MIL': 1.014, 
    'MIN': .980, 
    'NYM': .881, 
    'NYY': .952, 
    'OAK': .878, 
    'PHI': 1.000, 
    'PIT': 1.020, 
    'SDP': .885, 
    'SFG': .908, 
    'SEA': .911, 
    'STL': .884, 
    'TBR': .862,
    'TBD': .862,
    'TEX': .963, 
    'TOR': 1.017, 
    'WSN': .989,
}



MONTHS = {
    'Mar': 3, 
    'Apr': 4, 
    'May': 5, 
    'Jun': 6, 
    'Jul': 7, 
    'Aug': 8, 
    'Sep': 9, 
    'Oct': 10, 
    'Nov': 11,
}


def load_data(year, file):
    """
    Return a dict from a json file.
    """
    with open(f'data/{year}/{file}', 'r') as f:
        return json.load(f)


def has_not_happened(game_id):
    """
    Return true if the game has not happened yet.
    """
    return 'previews' in game_id


def dump_data(year, file, dict):
    """
    Dump the dictionary of games into a json file.
    """
    with open(f'data/{year}/{file}', 'w') as f:
        f.seek(0)
        f.truncate(0)
        json.dump(dict, f, indent=4)


def format_date_long(date_str):
    """
    Return a date string in the form of %weekday, %month %date, %year
    '2021-06-18' --> 'Friday, June 18'
    """
    date = str_to_datetime(date_str)
    return date.strftime('%A, %B %d')
    

def str_to_datetime(date_str):
    """
    Return a datetime object from a date string.
    '2021-09-03' --> datetime obj
    """
    return datetime.date.fromisoformat(date_str)


def get_starting_pitchers(soup):
    """
    Returns a len-2 list containing each starter's name and id.
    First tuple is away, second tupule is home.

    [('Lucas Giolito', 'giolilu01'), ('Dylan Bundy', 'bundydy01')]
    """
    lineups = str(soup.find('div', id='all_lineups')).split('\n')
    starters = []
    for i in range(len(lineups)):
        if '<td>P</td>' in lineups[i]:
            # <td><a href="players/w/wilsocj01.shtml">C.J. Wilson</a></td><td>P</td>
            line = lineups[i-1].strip()
            shtml = line.find('.shtml')
            name = line[shtml+8:line.find('<', shtml)]
            find_name = re.search(re.compile('/players/./'), line)
            if find_name == None:
                starters.append(('not_found', 'not_found'))
                continue
            id = line[find_name.span()[1]:shtml]
            starters.append((name, id))
            if len(starters) == 2:
                break
    # no <td>P</td> tags at all
    if len(starters) < 2:
        return [('not_found', 'not_found'), ('not_found', 'not_found')]
    return starters[0], starters[1]


def has_team_totals(line):
    """
    Return true if keywords that indicate the end of a pitching table
    has been reached are found.
    """
    return 'Team Totals' in line and 'data-stat="ER"' in line


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


def is_playoffs(soup):
    """
    Returns true if the game is playoff game.
    """
    title = soup.title.text
    playoffs = ['ALWC', 'NLWC', 'ALDS', 'NLDS', 'ALCS', 'NLCS', 'World Series']
    for series in playoffs:
        if series in title:
            return True
    return False


def is_pitching_row(line):
    """
    Return true if the line of the html contains text that indicates it is
    a row containing pitching game stats.
    """
    return ('data-stat="IP"' in line and 'data-append-csv' in line) or ('Team Totals' in line and 'data-stat="ER"' in line)


def was_suspended(soup):
    """
    Returns true if the game was suspended.
    """
    scorebox = soup.find('div', class_='scorebox_meta').text
    return 'suspended' in scorebox


def get_stat_value(row, stat):
    """
    Return the value of a particular stat from a game log row.
    """
    if stat in STAT_CHANGES:
        stat = STAT_CHANGES[stat]

    if stat == 'opposing_starter':
        name = row.find('td', {'data-stat': stat}).text.strip()
        return name[:name.find('(')]
    elif stat == 'opposing_starter_throws':
        return int(row.find('td', {'data-stat': stat}).text.strip() == 'R')
    elif stat == 'team_homeORaway':
        return int(row.find('td', {'data-stat': stat}).text.strip() == '@')
    elif stat == 'date_game':
        return row.find_all('td')[1]['csk'].split('.')[0]
    elif stat == 'opp_ID':
        return row.find('td', {'data-stat': stat}).text
    else:
        try:
            return int(row.find('td', {'data-stat': stat}).text)
        except:
            return float(row.find('td', {'data-stat': stat}).text)


def game_suspended(game):
    """
    Return true if the game was suspended. Used for hitting game logs.
    """
    return 'suspended' in str(game)


def is_second_game(soup):
    """
    Returns true if the game is the second of a doubleheader.
    """
    scorebox = soup.find('div', class_='box').find('div', class_='scorebox').find('div', class_='scorebox_meta').text
    return 'Second game of doubleheader' in scorebox


def parse_title(title):
    """
    Parse the title for the date, home team name, and away team name
    """
    vals = title[:title.find('|')].split(',')

    month = MONTHS[vals[1].strip().split()[0][:3]]
    day = int(vals[1].strip().split()[1])
    year = int(vals[2].strip())
    date = str(datetime.date(year, month, day))

    teams = vals[0][:vals[0].find('Box Score')]
    away_name = teams.split(' at ')[0].strip()
    home_name = teams.split(' at ')[1].strip()
    return date, TEAM_ABBRS[away_name], TEAM_ABBRS[home_name]
    

def add_IP(one, two):
    """
    Add or subtract innings pitched. 
    5.1 + 8.2 = 14.0 IP
    4.1 - 1.2 = 2.2 IP
    """
    sum = round(one + two, 2)
    tenth = int(str(sum).split('.')[-1])
    if 2 < tenth < 8:
        sum = float(math.ceil(sum) + (tenth % 3)/10)
    if tenth == 8 or tenth == 9:
        sum = float(math.floor(sum) + (3-(10-tenth))/10)
    return sum


def to_decimal(innings_pitched):
    """
    Convert conventional IP format to standard decimals.
    5.1 --> 5.33
    """
    tenth = float(str(float(innings_pitched)).split('.')[-1])
    return math.floor(innings_pitched) + tenth/3


def calculate_ERA(earned_runs, innings_pitched):
    """
    Return earned-run-average from earned runs and innings pitched.
    """
    return round(earned_runs*9/to_decimal(innings_pitched), 2)


def calculate_WHIP(innings_pitched, walks, hits):
    """
    Return WHIP.
    """
    return round((walks+hits)/to_decimal(innings_pitched), 2)


def calculate_BA(at_bats, hits):
    """
    Return batting average.
    """
    return round(hits/at_bats, 3)


def calculate_OBP(hits, walks, hbp, at_bats, sac_fly):
    """
    Return on-base percentage.
    """
    return round((hits+walks+hbp)/(at_bats+sac_fly+hbp+walks), 3)


def calculate_SLG(singles, doubles, triples, homeruns, at_bats):
    """
    Return slugging percentage.
    """
    return round((singles+2*doubles+3*triples+4*homeruns)/at_bats, 3)


def calculate_OPS(obp, slg):
    """
    Return on-base plus slugging percentage.
    """
    return round(obp + slg, 3)


def get_day_before(date):
    """
    Return the date before the specified data.
    """
    return str(date - datetime.timedelta(1)).split()[0]


def get_team_abbreviations(year):
    """
    Return a list of all the MLB team abbreviations for the given year.
    """
    return sorted([team.abbreviation for team in Teams(year)])


def starter_verified(last_name, full_name):
    """
    Return true if the given last name appears in the starter's full name.
    ('Snell', 'Blake Snell') --> True
    """
    return last_name.lower() in full_name.lower()


def print_same_line(message):
    """
    """
    print(message)
    print(LINE_UP, end=LINE_CLEAR)


def get_data_dicts():
    """
    Load the data for each year into separate dictionaries and return 
    them. 
    """
    print('Loading data from files...')
    game_data = {}
    pitcher_data = {}
    bullpen_data = {}
    years = [str(year) for year in range(get_data.START_YEAR, get_data.END_YEAR+1) if year != 2020]
    for year in years:  
        game_data[year] = load_data(year, get_data.GAME_DATA)
        pitcher_data[year] = load_data(year, get_data.PITCHER_DATA)
        bullpen_data[year] = load_data(year, get_data.BULLPEN_DATA)

    return game_data, pitcher_data, bullpen_data