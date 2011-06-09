$(function () {
    // This function is a callback, called when the DOM is loaded

    var first_time = true;
    var desired_first_record = null;
    var xy_pairs = {};
    var sensor_groups = null;

    function kw_tickformatter(val, axis) {
        // Workaround to get units on the y axis
        return val + " kW";
    }
    
    function array_index_of(ar, x) {
        // (IE doesn't have Array.indexOf)
        for (var i=0; i < ar.length; i++) {
            if (ar[i] == x) {
                return i;
            }
        }
        return -1;
    }
    
    function rnd(x) {
        // (Used to format numbers in the table)
        if (x) {
            return x.toFixed(2);
        }
        else {
            return x;
        }
    }

    // Interprets data from the server and updates the table
    function update_table(data) 
    {
	// We've already confirmed we have the right data
	// with the function that calls this

        // data_url gives the json dump of data transferred from database
	data_url = data.data_url;

	// defines where the start of data is
        // used in the graph, not really here.
	desired_first_record = data.desired_first_record;

	var missed_min_average,
            missed_week_average,
	    missed_month_average,
	    sensor_id,
       	    group_name,
            group_current,
	    group_week_average,
	    group_month_average;

        // get the sensor groups
        if (first_time) {
            sensor_groups = data.sensor_groups;
        }

	for (var i=0; i < sensor_groups.length; i++)
	{
            group_current = 0;
	    group_week_average = 0;
	    group_month_average = 0;
            missed_min_average = false;
	    missed_week_average = false;
	    missed_month_average = false;
	    group_name = sensor_groups[i][1];

	    for (var j=0; j < sensor_groups[i][3].length; j++)
	    {
		sensor_id = sensor_groups[i][3][j][0];

		// Add sensor's average to the sensor group's average. 
                if (sensor_id in data.min_averages)
                {
                    group_current += data.min_averages[sensor_id];
                }
		if (sensor_id in data.week_averages)
		{
		    group_week_average += data.week_averages[sensor_id];
		}
		if (sensor_id in data.month_averages)
		{
		    group_month_average += data.month_averages[sensor_id];
		}
	    }
                        
	    // Update the averages in the table for the sensor group.
	    // id for placement should be: curr{buildingname}
            if (! missed_min_average)
            {
                $('#curr' + group_name).empty();
                $('#curr' + group_name).append( rnd(group_current) );
            }
	    // id for placement should be: week{buildingname}
	    if (! missed_week_average)
	    {
		$('#week' + group_name).empty();
		$('#week' + group_name).append( rnd( group_week_average ) );
	    }
	    // id for placement should be: month{buildingname}
	    if (! missed_month_average)
	    {
		$('#month' + group_name).empty();
		$('#month' + group_name).append( rnd( group_month_average) );
	    }
	}
	
	if (first_time) 
	{
	    first_time = false;
	}

        $("#energystats").tablesorter(); 
	setTimeout(refreshdata, 10000);
    }
    

    function refreshdata_json_cb(data) {
        // Given new data from the server, update the page (graph and
        // table).


        // TODO: what if somehow we get no results and it's not the 
        // first time?
        if (first_time && data.no_results) {
	    alert('No data! Check connection to sensors.');
            return;
        }

        // When this function is first called, it is expected that 
        // data_url was defined previously (before loading this file).
        data_url = data.data_url;

        desired_first_record = data.desired_first_record;

        var series_opts = [];
        var series = [];
        var sensor_id,
            group_id,
            graph_opts;

	var options = $("#mode_settings");

        if (first_time) {
            sensor_groups = data.sensor_groups;

            // When data is received the first time,
            // remove the graph's loading animation
            $('#graph').empty();
	    options.append('<input type = "checkbox" name="'
			   + 'showSensors" checked="checked" id="showSensors">'
			   + '<label for "showSensors">'
			   + 'Show by Sensors' +'</label>');

	    $(':checkbox').click(function() {
		refreshdata();
	    });
        }

	// Iterate through each sensor with data points
	$.each(data.xy_pairs, function(cur_sensor,data_points) {
	    if (first_time) {
		xy_pairs[cur_sensor] = data_points;
            } else {
		/* We've already collected some data, so combine it 
		 * with the new.  About this slicing:  We're 
		 * discarding our latest record, preferring the new copy
		 * from the sever, since last time we may have e.g. 
		 * collected data just before a sensor reported a 
		 * reading (for the 10-second time period we were 
		 * considering).  Hence, while the latest record may be
		 * incomplete, the second latest (and older) records are
		 * safe---they will never change.
		 */
		var j;
		for (j=0; j < xy_pairs[cur_sensor].length; j++) {
                    if (xy_pairs[cur_sensor][j][0] >= desired_first_record) {
			// We break out of the loop when j is the index
			// of the earliest record on or later than
			// desired_first_record
			break;
                    }
		}
		xy_pairs[cur_sensor] = 
		    xy_pairs[cur_sensor].slice(j,
                                               xy_pairs[cur_sensor].length - 1
                                              ).concat(data_points);
            }
	});

	$.each(xy_pairs, function(sensor_name, data_points) {
	    if (sensor_name =='total') {
		series.push({
		    data: data_points,
		    label: data.building + ' ' + sensor_name,
		    color: '#' + data.building_color,
		});
	    } else if ($('#showSensors').is(':checked')) {
		series.push({
		    data: data_points,
		    label: data.building + ' ' + sensor_name,
		    //points: {
			//symbol: 'diamond',
		    //},
		});
	    }
	});
	
        // Finally, make the graph
        graph_opts = {
            series: {
                lines: {show: true},
                points: {show: false}
            },
            legend: {
                show: true, 
                position: 'ne',
                backgroundOpacity: 0.6,
                noColumns: xy_pairs.length
            },
            yaxis: {
                min: 0,
                tickFormatter: kw_tickformatter,
            },
            xaxis: {
                min: desired_first_record,
                mode: 'time',
                timeformat: '%h:%M %p',
                twelveHourClock: true
            },
            grid: {
                show: true,
                color: '#d0d0d0',
                borderColor: '#bbbbbb',
                backgroundColor: { colors: ['#dbefff', '#ffffff']}
            }
        };

        if (first_time) {
            first_time = false;
        }

        $.plot($('#graph'), series, graph_opts);
    
    }
    
    function refreshdata() {
        // Calls built in functions to get JSON data then pass it to a parsing function
        $.getJSON(data_url, refreshdata_json_cb);
    }

    function mainloop() {
        refreshdata()
        setTimeout(mainloop, 10000);
    }

    // Initially, show a loading animation instead of the graph
    $('#graph').append(
        '<img class="loading" src="' + MEDIA_URL + 'loading.gif" />');
    mainloop();

    
});
