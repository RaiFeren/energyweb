'''
    Used for various constants shared across the files.
'''

import calendar, datetime, simplejson, time

# Whether or not to report any academic data or not:
SHOW_ACADEMIC = True

# MAGIC CONSTANT: changes whenever a new sensor is added.
RESIDENTIAL_SENSORGROUP_IDS = [1, 2, 3, 4, 5, 6, 7, 8]
ACADEMIC_SENSORGROUP_IDS = [9, 10, 11, 12]

# If a full graph has this many points or fewer, show the individual
# points.  (Otherwise only draw the lines.)
GRAPH_SHOW_POINTS_THRESHOLD = 40

# Used to figure out what resolutions should be used by detail graph.
# Converts from the key's resolution, to the resolution shown on the graph.
# Key's resolution is really the Time Interval you're looking over.
# Based off of static graph's resolution determiner for 'auto'.
AUTO_RES_CONVERT = {
    'day':'minute*10',
    'week':'hour',
    'month':'hour',
    'year':'day',
    }

# Defines how big a resolution is.
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

# These mark the different previous cycle options.
# Used in the detail graphs page.
CYCLE_START_DELTAS = {
    'day':[
        RESOLUTION_DELTAS['day'], # Today
        2*RESOLUTION_DELTAS['day'], # Yesterday
        RESOLUTION_DELTAS['week'], # A Week Ago
        RESOLUTION_DELTAS['month'], # A Month Ago
        RESOLUTION_DELTAS['year'] # A Year Ago
        ],
    'week':[
        RESOLUTION_DELTAS['week'], # This Week
        2*RESOLUTION_DELTAS['week'], # Last Week
        RESOLUTION_DELTAS['month'], # A Month Ago
        RESOLUTION_DELTAS['year'], # A Year Ago
        ],
    'month':[
        RESOLUTION_DELTAS['month'], # This Month
        2*RESOLUTION_DELTAS['month'], # Last Month
        RESOLUTION_DELTAS['year'], # A Year Ago
        ],
    'year':[
        RESOLUTION_DELTAS['year'], # This Year
        2*RESOLUTION_DELTAS['year'], # Last Year
        ]
    }

# Similar to the above list, used in cycle mode of detail graph.
# Used to determine start offset for detail graph.
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

# These are magic strings representing different pages (or
# groups of pages) on the website for which page views
# will be counted.
CUSTOM = 'Custom Graph Form'
CUSTOM_GRAPH = 'Custom Graph Data'
DATA_ACCESS = 'Data Access'
DATA_DOWNLOAD = 'Data Download (from Custom Graph)'
DETAILED_VIEW = 'Detailed View'
DYNAMIC_GRAPH = 'Dynamic Graph'
DYNAMIC_TABLE = 'Dynamic Table'
MAINT_DATA_DOWNLOAD = 'Maintenance Data Download'
MON_STATUS = 'Monitor Statuses'
SERVER_STATS = 'Server Statistics'
SIGNAL_PROCESSING = 'Signal Processing'
SYSTEM_STATUS = 'System Status'

PAGES = [CUSTOM, CUSTOM_GRAPH, DATA_ACCESS, DATA_DOWNLOAD, DETAILED_VIEW, \
             DYNAMIC_GRAPH, DYNAMIC_TABLE, MAINT_DATA_DOWNLOAD, MON_STATUS, \
             SERVER_STATS, SIGNAL_PROCESSING, SYSTEM_STATUS]
