
import json
from matplotlib import pyplot as plt
from scipy import stats
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn import metrics
import get_data, data_utils


def best_model_log():
    """
    """
    with open('models/best_model.json', 'r') as f:
        return json.load(f)


def set_best_model(best_rmse, param_grid, run_max, features):
    """
    """
    with open('models/best_model.json', 'w') as f:
        f.seek(0)
        f.truncate(0)
        model_info = {
            'best_rmse': best_rmse,
            'features': features,
            'run_max': run_max,
            'param_grid': param_grid
        }
        json.dump(model_info, f, indent=4)


def show_scatterplot(samples, x_stat, y_stat):
    """
    """
    plt.scatter(samples[x_stat], samples[y_stat], s=.5, color='steelblue')
    plt.style.use('seaborn')
    plt.gcf().set_size_inches(9, 7)
    plt.xlabel(x_stat, fontsize=12)
    plt.ylabel(y_stat, fontsize=12)
    plt.show()


def get_correlation(arr1, arr2):
    """
    Return the correlation coefficient between two arrays.
    """
    r = stats.linregress(arr1, arr2)[2]
    return round(r**2, 5)


def print_predictions(num, predictions, y_test):
    """
    """  
    for i in range(num):
        print('Predicted:', round(predictions[i], 1))
        print('Actual:   ', float(y_test[i]), '\n')


def get_rmse(rf, samples, targets):
    """
    """
    X_train, X_test, y_train, y_test = train_test_split(samples, targets)
    rf.fit(X_train, y_train)
    predictions = rf.predict(X_test)
    rmse = round(metrics.mean_squared_error(y_test, predictions, squared=False), 2)
    return rmse


def get_stadium_score(team, game):
    """
    """
    if game['home']:
        return data_utils.STADIUM_SCORES[team]
    return data_utils.STADIUM_SCORES[game['opp']]


def get_pitcher_ERA(pitcher_data, year, id, date):
    """
    Return a pitcher's pregame ERA.
    """
    return pitcher_data[year][id][date]['pregame_ERA']


def get_pitcher_WHIP(pitcher_data, year, id, date):
    """
    Return a pitcher's pregame WHIP.
    """
    return pitcher_data[year][id][date]['pregame_WHIP']


def get_bullpen_ERA(bullpen_data, year, team_abbr, date):
    """
    Return a team's bullpen pregame ERA.
    """
    return bullpen_data[year][team_abbr][date]['pregame_ERA']


def get_bullpen_WHIP(bullpen_data, year, team_abbr, date):
    """
    Return a team's bullpen pregame WHIP.
    """
    return bullpen_data[year][team_abbr][date]['pregame_WHIP']

