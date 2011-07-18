'''
    Defines the database tables.

    Lists all of the various fields of each table.

    Member functions are generally convenience functions for
    inputting data or querying data.
'''

from django.db import models
from django.conf import settings
from datetime import datetime, timedelta


class SensorGroup(models.Model):
    '''
    Stores information about a sensor group (aka: building).
    Does NOT store what sensors belong to it.
    '''
    SCOPE_TYPES = ['residential','academic']
    
    name = models.CharField(max_length=32, unique=True)
    color = models.CharField(max_length=6) # color rendered on graph
    scope = models.CharField(max_length=32,
                             choices=[(t, t) for t in SCOPE_TYPES])
    # choices needs a short name and verbose name.

    def __unicode__(self):
        return self.name


class Sensor(models.Model):
    name = models.CharField(max_length=32, blank=True)
    ip = models.IPAddressField()
    sensor_group = models.ForeignKey(SensorGroup)
    three_phase = models.BooleanField()
    factor = models.FloatField()
    port = models.IntegerField()

    def __unicode__(self):
        if self.name:
            return u'%s %s' % (self.sensor_group.name, self.name)
        else:
            return self.sensor_group.name


class SensorReading(models.Model):
    sensor = models.ForeignKey(Sensor)
    reading_time = models.DateTimeField(db_index=True)
    rindex = models.PositiveSmallIntegerField()

    awatthr = models.PositiveIntegerField()
    bwatthr = models.PositiveIntegerField()
    cwatthr = models.PositiveIntegerField()

    avarhr = models.PositiveIntegerField()
    bvarhr = models.PositiveIntegerField()
    cvarhr = models.PositiveIntegerField()

    avahr = models.PositiveIntegerField()
    bvahr = models.PositiveIntegerField()
    cvahr = models.PositiveIntegerField()

    airms = models.PositiveIntegerField()
    birms = models.PositiveIntegerField()
    cirms = models.PositiveIntegerField()

    avrms = models.PositiveIntegerField()
    bvrms = models.PositiveIntegerField()
    cvrms = models.PositiveIntegerField()

    freq = models.PositiveIntegerField()
    tempc = models.IntegerField()

    def __unicode__(self):
        return u'%s at %s' % (self.sensor, self.reading_time)


class PowerAverage(models.Model):
    AVERAGE_TYPES = ('month', 'week', 'day', 'hour', 
                     'minute*10', 'minute', 'second*10')
    # TODO: month timedelta? (okay that it's None, for now, since we
    # should never have to use it as a resolution... it feels hacky
    # though)
    AVERAGE_TYPE_TIMEDELTAS = {
        'month': None,
        'week': timedelta(7, 0, 0),
        'day': timedelta(1, 0, 0),
        'hour': timedelta(0, 3600, 0),
        'minute*10': timedelta(0, 600, 0),
        'minute': timedelta(0, 60, 0),
        'second*10': timedelta(0, 10, 0)
    }
    AVERAGE_TYPE_DESCRIPTIONS = {
        'month': '1 month',
        'week': '1 week',
        'day': '1 day',
        'hour': '1 hour',
        'minute*10': '10 minutes',
        'minute': '1 minute',
        'second*10': '10 seconds'
    }

    first_reading_time = models.DateTimeField()
    last_reading_time = models.DateTimeField()
    trunc_reading_time = models.DateTimeField(db_index=True)

    sensor = models.ForeignKey(Sensor)
    num_points = models.PositiveIntegerField()
    watts = models.FloatField()
    average_type = models.CharField(max_length=32, db_index=True,
        choices=[(t, t) for t in AVERAGE_TYPES])

    @classmethod
    def average_type_sql(cls, average_type, reading_time_field):
        '''
        Return SQL (Postgres) for computing a truncated reading time
        from the original one.  (Hard to explain; look at the code.)
        '''
        if average_type == 'minute*10':
            return ('''date_trunc('hour', %s) 
                       + FLOOR(EXTRACT(MINUTE FROM %s) / 10)
                       * interval '10 minutes' '''
                    % (reading_time_field, reading_time_field))
        elif average_type == 'second*10':
            return ('''date_trunc('minute', %s) 
                       + FLOOR(EXTRACT(SECOND FROM %s) / 10)
                       * interval '10 seconds' '''
                    % (reading_time_field, reading_time_field))
        elif average_type in cls.AVERAGE_TYPES:
            return '''date_trunc('%s', %s)''' % (average_type, 
                                                 reading_time_field)
        else:
            raise ValueError('Invalid average type \'%s\'.' % average_type)

    @classmethod
    def date_trunc(self, field, dt):
        '''
        Return a truncated datetime, given the name of an average type
        and a datetime object.
        '''
        if field == 'second*10':
            return datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, 
                            dt.second - dt.second % 10)
        elif field == 'minute':
            return datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute)
        elif field == 'minute*10':
            return datetime(dt.year, dt.month, dt.day, dt.hour,
                            dt.minute - dt.minute % 10)
        elif field == 'hour':
            return datetime(dt.year, dt.month, dt.day, dt.hour)
        elif field == 'day':
            return datetime(dt.year, dt.month, dt.day)
        elif field == 'week':
            return (datetime(dt.year, dt.month, dt.day) 
                    - timedelta(dt.weekday()))
        elif field == 'month':
            return datetime(dt.year, dt.month, 1)
        else:
            raise ValueError('Unrecognized field \'%s\'.' % field)

    @classmethod
    def graph_data_execute(cls, cur, res, start_dt, end_dt=None):
        '''
        Using the supplied DB cursor, execute a query that selects
        the data for e.g. a graph starting at datetime start_dt,
        ending at datetime end_dt, and having resolution res.
        '''
        cur.execute('''SELECT 
                         AVG(graph_poweraverage.watts) / 1000, 
                         graph_sensor.id, 
                         graph_poweraverage.trunc_reading_time
                       FROM graph_poweraverage 
                       INNER JOIN graph_sensor 
                         ON graph_poweraverage.sensor_id = graph_sensor.id 
                       WHERE graph_poweraverage.average_type = %s
                         AND graph_poweraverage.trunc_reading_time >= %s '''

                    + (end_dt is not None 
                       and ' AND graph_poweraverage.trunc_reading_time <= %s '
                       or '') + '''

                       GROUP BY 
                         graph_poweraverage.trunc_reading_time, 
                         graph_sensor.sensor_group_id,
                         graph_sensor.id
                       ORDER BY 
                         graph_poweraverage.trunc_reading_time ASC, 
                         graph_sensor.sensor_group_id ASC,
                         graph_sensor.id ASC;''', 

                    (res, start_dt) 
                    + (end_dt is not None and (end_dt,) or ()))

    @classmethod
    def insert_averages(cls, cur, average_type, sensor, 
                        trunc_latest_reading_time):
        '''
        Insert power averages for the given average type, for all
        sensor readings before trunc_latest_reading_time.
        '''
        trunc_sql = cls.average_type_sql(average_type, 'reading_time')
        # The query below effectively does the following:
        # 1. Finds all truncated reading times in graph_sensorreading,
        #    before latest_trunc_reading, for this sensor id;
        # 2. Removes all truncated reading times in graph_poweraverage,
        #    before latest_trunc_reading, for this sensor id and
        #    average type;
        # 3. Computes the average power for each of the truncated
        #    reading times that remain, and inserts those calculations
        #    into graph_poweraverage.
        cur.execute('''
            INSERT INTO graph_poweraverage
              (first_reading_time,
              last_reading_time,
              trunc_reading_time,
              sensor_id,
              average_type,
              num_points,
              watts)

            SELECT
              MIN(reading_time),
              MAX(reading_time),
              ''' + trunc_sql + ''' AS sr_trunc_reading_time,
              %s,
              %s,
              COUNT(*),
              AVG(awatthr + bwatthr + cwatthr)
            FROM graph_sensorreading
            WHERE sensor_id = %s
              AND ''' + trunc_sql + ''' IN
                (SELECT ''' + trunc_sql + '''
                FROM graph_sensorreading
                WHERE sensor_id = %s
                  AND ''' + trunc_sql + ''' < %s
                EXCEPT
                SELECT trunc_reading_time
                FROM graph_poweraverage
                WHERE sensor_id = %s
                  AND average_type = %s
                  AND trunc_reading_time < %s)
            GROUP BY sr_trunc_reading_time;
            ''',
            (sensor.pk, 
             average_type, 
             sensor.pk, 
             sensor.pk, 
             trunc_latest_reading_time, 
             sensor.pk, 
             average_type, 
             trunc_latest_reading_time))
        return cur.rowcount

    def __unicode__(self):
        return u'%s for %s starting %s' % (self.sensor, self.average_type, 
                                           self.trunc_reading_time)

    class Meta:
        unique_together = (('trunc_reading_time', 'sensor', 'average_type'),)


class SRProfile(models.Model):
    sensor_reading = models.ForeignKey(SensorReading)

    power_average_inserts = models.IntegerField()
    power_average_updates = models.IntegerField()

    transaction_time = models.IntegerField()


class Setting(models.Model):
    VALUE_TYPE_CHOICES = (('bool', 'Boolean'),)

    name = models.CharField(max_length=32, unique=True)
    value_type = models.CharField(max_length=32, choices=VALUE_TYPE_CHOICES)
    value = models.TextField(blank=True)

    def get_value(self):
        if self.value_type == 'bool':
            if self.value == 'true':
                return True
            elif self.value == 'false':
                return False
            else:
                raise ValueError('Value does not match value type %s: .' % (self.value_type, self.value))
        else:
            raise ValueError('Invalid value type: %s.' % self.value_type)

    @classmethod
    def get_value_of(cls, name):
        s = cls.objects.get(name=name)
        return s.get_value()

    def set_value(self, value):
        if self.value_type == 'bool':
            if value:
                self.value = 'true'
            else:
                self.value = 'false'
        else:
            raise ValueError('Invalid value type: %s.' % self.value_type)
        self.save()

    @classmethod
    def set_value_of(cls, name, value):
        s = cls.objects.get(name=name)
        return s.set_value(value)

    def __unicode__(self):
        return u'%s: %s' % (self.name, self.value)


class Signal(models.Model):
    name = models.CharField(max_length=32)
    data = models.TextField(blank=True)

    @classmethod
    def dequeue(cls, name, **filter_args):
        signals = cls.objects.filter(name=name)
        if filter_args:
            signals = signals.filter(**filter_args)
        try:
            signal = signals.order_by('pk')[0]
            signal.delete()
            return signal.data
        except IndexError:
            return None

    @classmethod
    def enqueue(cls, name, data=None):
        if data is None:
            cls.objects.create(name=name)
        else:
            cls.objects.create(name=name, data=data)

    def __unicode__(self):
        return u'%s: %s' % (self.name, self.data)


class LogMessage(models.Model):
    ''' Model for Log Messages stored by the energymons and the
        energyfakers upon encountering interesting things.
    '''
    sensor = models.ForeignKey(Sensor)
    reading_time = models.DateTimeField(db_index=True)
    
    SENSOR_TYPE_CHOICES = (
        ('M', 'Monitor'),
        ('F', 'Faker'),
        )
    sensor_type = models.CharField(max_length=1, choices=SENSOR_TYPE_CHOICES)
    
    LOG_TYPE_CHOICES = (
        ('E', 'Error'),
        ('W', 'Warning'),
        ('S', 'Status'),
        )
    log_type = models.CharField(max_length=1, choices=LOG_TYPE_CHOICES)

    # Magic number: 32 because we don't know what topics we might put, but they
    # shouldn't be long anyways since we have details.
    topic = models.CharField(max_length=32)
    details = models.TextField()

class viewCount(models.Model):
    '''
    Keeps track of page views by page and by day.
    '''
    count = models.IntegerField()
    date = models.DateField()
    page = models.CharField(max_length=35)
