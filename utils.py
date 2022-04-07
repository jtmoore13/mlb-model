
from sportsipy.mlb.teams import Team, Teams
import sys
import datetime


YEARS = [year for year in range(2010, 2022) if year != 2020]
HITTING_STATS = ['date', 'home', 'opp', 'result', 'PA', 'AB', 'R', 'H', '2B', '3B', 'HR', 'RBI', 'BB', 'IBB', 'SO', 'HBP', 'SH', 'SF', 'ROE', 'GDP', 'SB', 'CS', 'current_BA', 'current_OBP', 'current_SLG', 'current_OPS', 'LOB', '#', 'opp_starter_righty', 'opp_starter']
STATS_TO_USE = ['2B', '3B', 'AB', 'current_BA', 'BB', 'H', 'HBP', 'HR', 'current_OBP', 'current_OPS', 'PA', 'R', 'RBI', 'SF', 'current_SLG', 'SO', 'date', 'home', 'opp', 'opp_starter', 'opp_starter_righty']
PITCHING_STATS = ['IP', 'ER', 'H', 'BB']  #  'R', 'SO', 'HR', 'earned_run_avg'

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


def is_playoffs(title):
    """
    Returns true if the game is playoff game.
    """
    playoffs = ['ALWC', 'NLWC', 'ALDS', 'NLDS', 'ALCS', 'NLCS', 'World Series']
    for series in playoffs:
        if series in title:
            return True
    return False


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
    home_name = teams.split(' at ')[0].strip()
    away_name = teams.split(' at ')[1].strip()
    return date, TEAM_ABBRS[home_name], TEAM_ABBRS[away_name]


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


def print_game(should_print):
    """
    Prints '.' is should_print is true, ' ' otherwise.
    """
    if should_print:
        sys.stdout.write('.')
    else:
        sys.stdout.write(' ')
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

