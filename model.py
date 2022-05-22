
import numpy as np
from numpy import mean
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.metrics import mean_squared_error
from matplotlib import pyplot as plt
import xgboost as xgb
import seaborn as sb
from colorama import Fore, Style
import pickle
import json
import datetime
import sys
import random
import data_utils, model_utils


START_YEAR = 2010
END_YEAR = 2022
GAME_DATA, PITCHER_DATA, BULLPEN_DATA = data_utils.get_data_dicts(START_YEAR, END_YEAR)
MODEL_FILE = 'my_model.sav'

FEATURE_LIST = [
    'pregame_BA',
    'pregame_SLG',
    'recent_BA',
    'recent_SLG',
    'left/right_BA',
    'left/right_SLG',
    'home/away_BA',
    'home/away_SLG',
    'opp_starter_ERA',
    'opp_starter_WHIP',
    'opp_bullpen_ERA',
    'opp_bullpen_WHIP',
    'stadium_score',
    'temp',
    'over_under',
    'has_DH',
]

def make_game_sample(game, year, team, date):
    """
    """
    sample = []             
    throw = 'right' if game['opp_starter_righty'] else 'left'
    loc = 'home' if game['home'] else 'away'
    home_team = team if game['home'] else game['opp']
    sample.append(game['pregame_BA'])
    sample.append(game['pregame_SLG'])
    sample.append(game['10-day_BA'])
    sample.append(game['10-day_SLG'])
    sample.append(game[f'{throw}_BA'])
    sample.append(game[f'{throw}_SLG'])
    sample.append(game[f'{loc}_BA'])
    sample.append(game[f'{loc}_SLG'])
    sample.append(data_utils.get_pitcher_ERA(PITCHER_DATA, year, game['opp_starter_id'], date))
    sample.append(data_utils.get_pitcher_WHIP(PITCHER_DATA, year, game['opp_starter_id'], date))
    sample.append(data_utils.get_bullpen_ERA(BULLPEN_DATA, year, game['opp'], date))
    sample.append(data_utils.get_bullpen_WHIP(BULLPEN_DATA, year, game['opp'], date))
    sample.append(data_utils.get_stadium_score(team, game))
    sample.append(game['temp'])
    sample.append(game['over_under'])
    sample.append(data_utils.has_DH(home_team, year))
    return np.array(sample)


def is_incomplete_sample(date, game):
    """
    Return true if the game contains all of the necessary info
    for a full sample. 
    """
    if 'opp_starter_id' not in game or game['opp_starter_id'] == 'not_found':
        return True
    if 'pregame_BA' not in game:
        return True
    if 'over_under' not in game:
        return True
    if '10-day_BA' not in game or '15-day_BA' not in game:
        return True
    if game['home'] and 'home_BA' not in  game:
        return True
    if not game['home'] and 'away_BA' not in game:
        return True
    if game['opp_starter_righty'] and 'right_BA' not in game:
        return True
    if not game['opp_starter_righty'] and 'left_BA' not in game:
        return True
    year = date.split('-')[0]
    opp_pitcher_id = game['opp_starter_id'] 
    if opp_pitcher_id not in PITCHER_DATA[year]:
        return True
    if 'pregame_ERA' not in PITCHER_DATA[year][opp_pitcher_id][date]:
        return True
    opp = game['opp']
    if date not in BULLPEN_DATA[year][opp]:
        return True
    if 'pregame_ERA' not in BULLPEN_DATA[year][opp][date]:
        return True
    return False


def get_samples(test_years):
    """
    Parse the game data and form data samples. Return 2d array of samples
    and a 1d array of targets.
    """
    print('Gathering samples...')
    incomplete = 0
    samples = []
    targets = []
    train_samples = []
    train_targets = []
    test_samples = []
    test_targets = []
    for year in GAME_DATA:
        for team in GAME_DATA[year]:
            for date in list(GAME_DATA[year][team])[1:]:
                game = GAME_DATA[year][team][date]
                team_runs = min(game['R'], 9)
                if is_incomplete_sample(date, game):
                    incomplete += 1
                    continue
                sample = make_game_sample(game, year, team, date)
                samples.append(sample)
                targets.append(team_runs)
                if year not in test_years:
                    train_samples.append(sample)
                    train_targets.append(team_runs)
                else:
                    test_samples.append(sample)
                    test_targets.append(team_runs)

    print(f'{Style.DIM}{len(samples)} complete samples.')
    print(f'{incomplete} incomplete samples.\n{Style.RESET_ALL}')

    df = pd.DataFrame(samples, columns=FEATURE_LIST)
    df['runs_scored'] = targets
    train_df = pd.DataFrame(train_samples, columns=FEATURE_LIST)
    train_df['runs_scored'] = train_targets
    test_df = pd.DataFrame(test_samples, columns=FEATURE_LIST)
    test_df['runs_scored'] = test_targets
    return df, train_df, test_df


def compare_to_vegas(rf, test_years, nearest_half=True):
    """
    """
    me_closer = 0
    vegas_closer = 0
    total = 1
    over_vegas = 0
    under_vegas = 0
    push_vegas = 0
    games = set()
    for year in test_years:
        for team in GAME_DATA[year]:
            for date in GAME_DATA[year][team]:
                game1 = GAME_DATA[year][team][date]
                game2 = GAME_DATA[year][game1['opp']][date]
                home_team = team if game1['home'] else game1['opp']
                away_team = game1['opp'] if home_team == team else team
                game_id = home_team + away_team + date
                if game_id in games:
                    continue
                if is_incomplete_sample(date, game1) or is_incomplete_sample(date, game2):
                    continue

                sample1 = make_game_sample(game1, year, team, date).reshape(1, len(FEATURE_LIST))
                sample2 = make_game_sample(game2, year, game1['opp'], date).reshape(1, len(FEATURE_LIST))
                prediction1 = float(rf.predict(sample1)[0])
                prediction2 = float(rf.predict(sample2)[0])

                my_total = round(prediction1 + prediction2, 2)
                if nearest_half:
                    my_total = round(my_total*2)/2
                vegas_total = game1['over_under']
                actual_total = game1['R'] + game2['R']

                if abs(my_total - vegas_total) >= 0:
                    total += 1
                    games.add(game_id)
                    if my_total > vegas_total:
                        over_vegas += 1
                    elif my_total < vegas_total:
                        under_vegas += 1
                    else:
                        push_vegas += 1

                    if abs(my_total - actual_total) < abs(vegas_total - actual_total):
                        me_closer += 1
                    elif abs(my_total - actual_total) > abs(vegas_total - actual_total):
                        vegas_closer += 1

                # print(f'{team} vs {game1["opp"]} {date}')
                # print(f'My total:     {my_total}')
                # print(f'Vegas total:  {vegas_total}')
                # print(f'Actual score: {actual_total}\n')

    print(f'over vegas: {round(over_vegas*100/total)}%, under vegas: {round(under_vegas*100/total)}%, same: {round(push_vegas*100/total)}%')
    print('---------------------------')
    print(f'Model success {test_years[0]}: {round(me_closer*100/(total-push_vegas), 2)}%')
    print('---------------------------')


def develop(rf, df):
    """
    Main function used to develop and test the model.
    """
    samples, targets = df.loc[:, df.columns!='runs_scored'], df['runs_scored']
    X_train, X_test, y_train, y_test = train_test_split(samples, targets)

    cv = KFold(n_splits=3, shuffle=True, random_state=42)
    train_scores = cross_val_score(rf, X_train, y_train, scoring='neg_root_mean_squared_error', cv=cv, n_jobs=-1)
    train_rmse = round(-1*mean(train_scores), 2)
    print(f'train RMSE: {train_rmse}')

    # score the test data
    rf.fit(X_train, y_train)
    predictions = rf.predict(X_test)
    test_rmse = round(mean_squared_error(y_test, predictions, squared=False), 2)
    print(f'test RMSE:  {test_rmse}')

    # create correlation heatmap
    plt.figure(figsize=(35, 35))
    heatmap = sb.heatmap(df.corr(), cmap='Blues', annot=True)
    plt.savefig('figures/correlation_heatmap.png')
    plt.close()

    # create feature importance chart
    importances = rf.feature_importances_
    sorted_indices = np.argsort(importances)[::-1]
    plt.bar(range(X_train.shape[1]), importances[sorted_indices], align='center')
    plt.xticks(range(X_train.shape[1]), X_train.columns[sorted_indices], rotation=90)
    plt.tight_layout()
    plt.savefig('figures/feature_importance.png')
    plt.close()


def fit_and_save(rf, df, filename):
    """
    """
    samples, targets = df.loc[:, df.columns!='runs_scored'], df['runs_scored']
    rf.fit(samples, targets)
    pickle.dump(rf, open(filename, 'wb'))
 

def test_each_year():
    """
    """
    for year in [str(year) for year in range(2021, 2022) if year != 2020]:
        rf = xgb.XGBRFRegressor(n_estimators=1000, max_depth=7, gamma=0, min_child_weight=7, subsample=.6, reg_alpha=.1)
        test_years = [year]
        df, train_df, test_df = get_samples(test_years)
        X_train, y_train = train_df.loc[:, train_df.columns!='runs_scored'], train_df['runs_scored']
        rf.fit(X_train, y_train)
        compare_to_vegas(rf, test_years, nearest_half=True)


def main():
    """
    """
    rf = xgb.XGBRFRegressor(n_estimators=1000, max_depth=7, gamma=0, min_child_weight=7, subsample=.6, reg_alpha=.1)
    test_years = ['2021']
    df, train_df, test_df = get_samples(test_years)

    args = sys.argv
    if '-d' in args or '-develop' in args:
        develop(rf, df)
    elif '-f' in args or '-fit' in args:
        fit_and_save(rf, df, MODEL_FILE)
    elif '-c' in args or '-compare' in args:
        X_train, y_train = train_df.loc[:, train_df.columns!='runs_scored'], train_df['runs_scored']
        rf.fit(X_train, y_train)
        compare_to_vegas(rf, test_years, nearest_half=True)


if __name__ == '__main__':
    main()