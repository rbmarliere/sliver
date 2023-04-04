import pylunar


def period(moon, time):
    moon.update(time)
    nm_sec = moon.time_to_new_moon() * 60 * 60
    if nm_sec - 1031220 <= 0 and nm_sec - 564020 > 0:
        # green
        return 1
    if nm_sec - 564020 <= 0 and nm_sec - 298620 > 0:
        # black
        return 2
    if nm_sec - 298620 <= 0 and nm_sec - 298620 + 612000 > 0:
        # green
        return 1
    if nm_sec - 1819620 <= 0 and nm_sec - 1531920 >= 0:
        # yellow
        return -1
    # red is remainder
    return 0


def MOON(ohlc):
    df = ohlc.copy()

    moon = pylunar.MoonInfo((28, 2, 4.9), (86, 55, 0.9))

    df["moon_phase"] = df["time"].apply(lambda x: period(moon, x))

    return df
