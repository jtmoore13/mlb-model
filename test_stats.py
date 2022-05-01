
import random as rand
import datetime
import utils
import get_data


GAME_DATA, PITCHER_DATA, BULLPEN_DATA = utils.get_data_dicts()
YEARS = list(GAME_DATA.keys())


def test_num_teams():
    """
    Tests that all 30 teams are accounted for.
    """
    for year in YEARS:
        assert(len(GAME_DATA[year]) == 30)
        assert(len(BULLPEN_DATA[year]) == 30)


def test_num_games():
    """
    Test that the number of games scraped in a full season is above ~155.
    """
    for year in YEARS:
        if year == str(datetime.date.today().year):
            break
        for team in BULLPEN_DATA[year]:
            assert(len(BULLPEN_DATA[year][team]) > 155)
        for team in GAME_DATA[year]:
            assert(len(GAME_DATA[year][team]) > 155)



# =========================== GAME TESTS =========================== #


def test_game_keys():
    """
    Tests that all necessary fields are present in each game.
    """
    extra_stats = ['pregame_BA', 'pregame_OBP', 'pregame_SLG', 'pregame_OPS',  '10-day_BA', '10-day_OBP', '10-day_SLG', '10-day-OPS']
    for year in GAME_DATA:
        data = GAME_DATA[year]
        for team in data:
            dates = list(data[team])
            for i in range(len(dates)):
                date = dates[i]
                keys = list(data[team][date])
                for cat in get_data.HITTING_STATS:
                    assert(cat in keys)
                if i > 0:
                    for cat in extra_stats:
                        assert(cat in keys)


# =========================== OFFENSIVE TESTS =========================== #


# =========================== PITCHING TESTS =========================== #


def test_bullpen_keys():
    """
    Tests that all fields are present in each bullpen game.
    """
    for year in BULLPEN_DATA:
        data = BULLPEN_DATA[year]
        for team in data:
            dates = list(data[team])
            for i in range(len(dates)):
                keys = list(data[team][dates[i]])
                # accounting for starting pitcher CG on game 1 (ex: SEA 2011)
                if i >= 2:
                    assert('pregame_ERA' in keys)
                    assert('pregame_WHIP' in keys)
                assert('game_H' in keys)
                assert('game_ER' in keys)
                assert('game_BB' in keys)
                assert('game_H' in keys)


def test_bullpen_season_stats():
    """
    Test that randomly selected dates from a team's season have been correctly
    added from previous games. 
    """
    for year in BULLPEN_DATA:
        data = BULLPEN_DATA[year]
        for team in data:
            dates = list(data[team])
            # choose a random date 10 times, see if stats were calculated correctly
            for i in range(10):
                choice = rand.randint(4, len(dates)-1)
                chosen_date = dates[choice]
                chosen_game = data[team][chosen_date]
                season_IP, season_ER, season_BB, season_H = (0, 0, 0, 0)
                for date in dates[:choice]:
                    game = data[team][date]
                    season_IP = utils.add_IP(season_IP, game['game_IP'])
                    season_ER += game['game_ER']
                    season_BB += game['game_BB']
                    season_H += game['game_H']
                assert(chosen_game['pregame_ERA'] == utils.calculate_ERA(season_ER, season_IP))
                assert(chosen_game['pregame_WHIP'] == utils.calculate_WHIP(season_IP, season_BB, season_H))


def check_bullpen(game, innings_pitched, hits, earned_runs, walks):
    """
    Verifty certain values are correct.
    """
    assert(game['game_IP'] == innings_pitched)
    assert(game['game_H'] == hits)
    assert(game['game_ER'] == earned_runs)
    assert(game['game_BB'] == walks)


def test_bullpen_game_stats():
    """
    Test that the bullpen stats are correct for the
    selected games. Hard-coded stats calculated by hand to
    be compared with the scraped values.
    """
    game1 = BULLPEN_DATA['2021']['ARI']['2021-04-06']
    game2 = BULLPEN_DATA['2021']['SFG']['2021-07-04']
    game3 = BULLPEN_DATA['2021']['BOS']['2021-08-17 (2)']
    game4 = BULLPEN_DATA['2021']['BAL']['2021-08-14']
    game5 = BULLPEN_DATA['2021']['SEA']['2021-04-23']
    check_bullpen(game1, 7.1, 5, 2, 4)
    check_bullpen(game2, .1, 0, 0, 1)
    check_bullpen(game3, 1.0, 1, 0, 0)
    check_bullpen(game4, 4.2, 8, 9, 2)
    check_bullpen(game5, 3.1, 5, 0, 0)


def test_ERA_fn():
    """
    Test that calculate_ERA() in utils.py works.
    """
    assert(utils.calculate_ERA(1, 1) == 9)
    assert(utils.calculate_ERA(2, 2.1) == 7.71)
    assert(utils.calculate_ERA(0, 9) == 0)
    assert(utils.calculate_ERA(1, 21) == .43)
    assert(utils.calculate_ERA(23, 40) == 5.17)
    assert(utils.calculate_ERA(258, 974) == 2.38)


def test_WHIP_fn():
    """
    Test that calculate_WHIP() in utils.py works.
    """
    assert(utils.calculate_WHIP(7, 0, 0) == 0)
    assert(utils.calculate_WHIP(1, 1, 0) == 1)
    assert(utils.calculate_WHIP(9, 8, 4) == 1.33)
    assert(utils.calculate_WHIP(21, 1, 0) == .05)
    assert(utils.calculate_WHIP(428, 340, 98) == 1.02)


def test_ERA_stats():
    """
    Test that ERAs were calculated correctly. 
    """
    game1 = PITCHER_DATA['2012']['verlaju01']['2012-05-08']
    game2 = PITCHER_DATA['2015']['syndeno01']['2015-06-02']
    game3 = PITCHER_DATA['2011']['kershcl01']['2011-05-18']
    game4 = PITCHER_DATA['2017']['klubeco01']['2017-04-27']
    assert(game1['pregame_ERA'] == 2.38)
    assert(game2['pregame_ERA'] == 1.82)
    assert(game3['pregame_ERA'] == 2.75)
    assert(game4['pregame_ERA'] == 4.28)

    game5 = BULLPEN_DATA['2021']['CIN']['2021-04-05']
    game6 = BULLPEN_DATA['2021']['BOS']['2021-04-05']
    game7 = BULLPEN_DATA['2018']['NYY']['2018-04-03']
    game8 = BULLPEN_DATA['2012']['CLE']['2012-04-09']
    assert(game5['pregame_ERA'] == 2.63)
    assert(game6['pregame_ERA'] == 4.30)
    assert(game7['pregame_ERA'] == 7.42)
    assert(game8['pregame_ERA'] == 7.2)


def test_WHIP_stats():
    """
    Test that WHIPs were calculated correctly.
    """

    game1 = PITCHER_DATA['2016']['scherma01']['2016-04-26']
    game2 = PITCHER_DATA['2016']['scherma01']['2016-05-27']
    game3 = PITCHER_DATA['2019']['verlaju01']['2019-04-13']
    game4 = PITCHER_DATA['2010']['hernafe02']['2010-04-26']
    assert(game1['pregame_WHIP'] == 1.2)
    assert(game2['pregame_WHIP'] == 1.1)
    assert(game3['pregame_WHIP'] == 1.29)
    assert(game4['pregame_WHIP'] == 1.09)

    game5 = BULLPEN_DATA['2021']['SEA']['2021-04-05']
    game6 = BULLPEN_DATA['2021']['OAK']['2021-04-04']
    game7 = BULLPEN_DATA['2014']['NYM']['2014-04-04']
    game8 = BULLPEN_DATA['2015']['PHI']['2015-04-10']
    assert(game5['pregame_WHIP'] == .91)
    assert(game6['pregame_WHIP'] == 2.11)
    assert(game7['pregame_WHIP'] == 2.36)
    assert(game8['pregame_WHIP'] == 1.42)

