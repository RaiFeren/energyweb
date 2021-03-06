"""
    For running the admin page.
    Admin page is used for allowing someone to edit the database via
    web browser. Which we don't really want to let people do
    for security reasons..
    
    To view, enable admin in ../settings.py with the current apps
"""

from django.contrib import admin

# Uncomment the below line to allow the data tables
#from energyweb.graph.models import Sensor, SensorGroup, \
#     SensorReading, PowerAverage

# Enables raw viewing and editing of the various data tables.
#admin.site.register(SensorGroup)
#admin.site.register(Sensor)
#admin.site.register(SensorReading)
#admin.site.register(PowerAverage)
