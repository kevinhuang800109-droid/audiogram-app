from audiogram.calc import four_freq_average


def test_average_of_four_frequencies():
    th = {250: 10, 500: 20, 1000: 30, 2000: 40, 4000: 50, 8000: 70}
    assert four_freq_average(th) == 35


def test_missing_frequency_gives_none():
    th = {500: 20, 1000: 30, 2000: None, 4000: 50}
    assert four_freq_average(th) is None
