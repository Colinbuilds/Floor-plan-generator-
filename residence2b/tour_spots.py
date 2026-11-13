"""360-degree tour spots (plan feet) and the hotspot links between them."""
F = 0.3048
EYE = 1.55

SPOTS = {
    # id: (label, x_ft, y_ft, has_windows)
    'entry':          ('Entry',            37.6, 41.6, False),
    'den':            ('Den / Library',    24.0, 37.4, False),
    'kitchen':        ('Kitchen & Dining', 38.8, 19.5, True),
    'living':         ('Living Room',      31.0, 26.0, True),
    'balcony':        ('Balcony',          28.0, 6.0,  True),
    'primary_bed':    ('Primary Bedroom',  10.2, 12.5, True),
    'primary_bath':   ('Primary Bath',     9.8,  24.0, False),
    'primary_closet': ('Primary Closet',   9.5,  37.2, False),
    'bedroom2':       ('Bedroom 2',        51.0, 10.5, True),
    'bath2':          ('Bath 2',           54.6, 24.0, False),
}
# from -> [(to, hotspot floor point (x, y) in plan feet)]
LINKS = {
    'entry':          [('living', (31.0, 26.0)), ('kitchen', (38.8, 19.5)), ('den', (33.5, 34.2)), ('bedroom2', (46.0, 36.4))],
    'den':            [('entry', (24.2, 35.0)), ('living', (25.6, 34.4))],
    'kitchen':        [('living', (31.0, 26.0)), ('balcony', (28.4, 11.6)), ('entry', (37.6, 36.5))],
    'living':         [('kitchen', (38.8, 19.5)), ('balcony', (28.4, 11.6)), ('primary_bed', (14.4, 16.2)),
                       ('den', (24.2, 34.6)), ('entry', (37.6, 36.0))],
    'balcony':        [('living', (28.2, 11.4))],
    'primary_bed':    [('living', (14.4, 16.2)), ('primary_bath', (9.6, 18.3))],
    'primary_bath':   [('primary_bed', (9.6, 18.4)), ('primary_closet', (9.6, 34.8))],
    'primary_closet': [('primary_bath', (9.6, 34.8))],
    'bedroom2':       [('entry', (48.2, 16.4)), ('bath2', (49.4, 17.6))],
    'bath2':          [('bedroom2', (50.6, 22.4))],
}
SEASONS = ['spring', 'summer', 'fall', 'winter']
TIMES = ['morning', 'midday', 'golden', 'night']
T_VALUE = {'morning': 0.0, 'midday': 1.0, 'golden': 2.0, 'night': 3.0}


def variants(spot):
    """(season, time) panoramas rendered for a spot; windowless rooms only need day / evening."""
    if SPOTS[spot][3]:
        return [(s, t) for s in SEASONS for t in TIMES]
    return [('fall', 'midday'), ('fall', 'night')]


def pano_name(spot, season, tod):
    return f'{spot}_{season}_{tod}.jpg'
