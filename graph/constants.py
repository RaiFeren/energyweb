'''
Used for various constants
'''

import calendar, datetime, simplejson, time

# Whether or not to report any academic data or not:
SHOW_ACADEMIC = True

RESIDENTIAL_SENSORGROUP_IDS = [1, 2, 3, 4, 5, 6, 7, 8]
ACADEMIC_SENSORGROUP_IDS = [9, 10, 11, 12]

# If a full graph has this many points or fewer, show the individual
# points.  (Otherwise only draw the lines.)
GRAPH_SHOW_POINTS_THRESHOLD = 40

AUTO_RES_CONVERT = {
    'day':'minute*10',
    'week':'hour',
    'month':'hour',
    'year':'day',
    }

RESOLUTION_DELTAS = {
    'year':datetime.timedelta(365,0,0), # TODO: do we care about leap?
    'month':datetime.timedelta(30,0,0), # TODO: make less of a hack number
    'week':datetime.timedelta(7,0,0),
    'day':datetime.timedelta(1,0,0),
    'hour':datetime.timedelta(0,3600,0),
    'minute*10':datetime.timedelta(0,600,0),
    'minute':datetime.timedelta(0,60,0),
    'second*10':datetime.timedelta(0,10,0),
    }

# These mark the different previous cycle options
# Used in the detail graphs page.
# First one is the Current cycle.
CYCLE_START_DELTAS = {
    'day':[
        RESOLUTION_DELTAS['day'],
        2*RESOLUTION_DELTAS['day'],
        RESOLUTION_DELTAS['week'],
        RESOLUTION_DELTAS['month'],
        RESOLUTION_DELTAS['year']
        ],
    'week':[
        RESOLUTION_DELTAS['week'],
        2*RESOLUTION_DELTAS['week'],
        RESOLUTION_DELTAS['month'],
        RESOLUTION_DELTAS['year'],
        ],
    'month':[
        RESOLUTION_DELTAS['month'],
        2*RESOLUTION_DELTAS['month'],
        RESOLUTION_DELTAS['year'],
        ],
    'year':[
        RESOLUTION_DELTAS['year'],
        2*RESOLUTION_DELTAS['year'],
        ]
    }

CYCLE_START_DIFFS = {
    'second*10': [0],
    'minute': [0],
    'minute*10': [0],
    'day':[ #use day averages
        0,
        1,
        7,
        30,
        365,
        ],
    'week':[ #use week averages
        0,
        1,
        4,
        52,
        ],
    'month':[ #use month averages
        0,
        1,
        12,
        ],
    'year':[ #use year averages
        0,
        1
        ]
    }
