
from sportsipy.mlb.teams import Teams
import sys
import datetime
import json
import re

YEARS = [str(year) for year in range(2021, 2022) if year != 2020]
PITCHING_STATS = ['IP', 'ER', 'H', 'BB']  #  'R', 'SO', 'HR', 'earned_run_avg'
HITTING_STATS = ['date', 'home', 'opp', 'AB', 'R', 'H', '2B', '3B', 'HR', 'RBI', 'BB', 'HBP', 'SF', 'postgame_BA', 'postgame_OBP', 'postgame_SLG', 'postgame_OPS', 'opp_starter_righty', 'opp_starter']
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

REGEX = re.compile('/players/./')

TEAM_NAMES = {
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
    'Colorado Rockies': 'COL',
    'Detroit Tigers': 'DET',
    'Houston Astros': 'HOU',
    'Kansas City Royals': 'KCR',
    'Los Angeles Angels': 'LAA',
    'Los Angeles Dodgers': 'LAD',
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
    'Texas Rangers': 'TEX',
    'Toronto Blue Jays': 'TOR',
    'Washington Nationals': 'WSN'
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

class format:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'
   CHECK = u'\u2713'
   DEGREES = u'\xb0'


def load_data(year, file):
    """
    Return a dict from a json file.
    """
    with open(f'data/{year}/{file}', 'r') as f:
        return json.load(f)


def dump_data(year, file, dict):
    """
    Dump the dictionary of games into a json file.
    """
    with open(f'data/{year}/{file}', 'w') as f:
        f.seek(0)
        f.truncate(0)
        json.dump(dict, f, indent=4)


def get_starting_pitchers(soup):
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
            id = line[re.search(REGEX, line).span()[1]:shtml]
            starters.append((name, id))
            if len(starters) == 2:
                break
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
    

def to_total_outs(ip):
    """
    Convert innings pitched into total outs.
    5.1 --> 16
    """
    ip = str(ip).split('.')
    return float(ip[0])*3 + float(ip[-1])


def to_IP(total_outs):
    """
    Convert total outs to innings pitched.
    16 --> 5.33
    """
    return total_outs/3


def calculate_ERA(earned_runs, innings_pitched):
    """
    Return earned-run-average from earned runs and innings pitched
    """
    return round(earned_runs*9/innings_pitched, 2)


def calculate_WHIP(innings_pitched, walks, hits):
    """
    Return WHIP.
    """
    return round((walks+hits)/innings_pitched, 2)


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


def print_game(char):
    """
    Print the given character ('.' for a game, ' ' for no game)
    """
    sys.stdout.write(char)
    sys.stdout.flush()


def print_team(team_abbr):
    """
    Print the team abbreviation.
    """
    print(team_abbr, end='')
    sys.stdout.flush()


def print_check():
    """
    Print green check mark.
    """           
    print(format.GREEN+format.CHECK+format.END)


def print_total(total_games, year):
    """
    Print the number of games added for a particular season.
    """
    print(f'\n{format.BOLD}{format.DARKCYAN}{total_games}{format.END} datapoints added for {year}{format.END} season.\n')

