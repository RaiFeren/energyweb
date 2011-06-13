$(function () {
    // This function is a callback, called when the DOM is loaded

    var first_time = true;
    var desired_first_record = null;
    var xy_pairs = {};
    var sensor_groups = null;
    var mode = 'sensors';

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

    // Clear the graph and put the options up
    function set_mode_settings(data)
    {
        // When data is received the first time,
        // remove the graph's loading animation
        $('#graph').empty();
	
	var options = $("#mode_settings");
	options.empty();
	// Enable the form for switching resolutions
	options.append('View By:' +
		       '<form action=""><select name="period"' +
		       'OnChange="location.href=' +
		       'period.options[selectedIndex].value">' +
		       '<option value="" selected="selected">' +
		       'Select Resolution</option>' +
		       '<option value="'+ day_url +'">Day</option>' +
		       '<option value="'+ week_url +'">Week</option>' +
		       '<option value="'+ month_url +'">Month</option>' +
		       '<option value="'+ year_url +'">Year</option>' +
		       ' </select></form>');
	if (mode == 'sensors') {
	    // Enable checkbox for splitting sensors
	    options.append('<input type = "checkbox" name="'
			   + 'showSensors" id="showSensors">'
			   + '<label for "showSensors">'
			   + 'Show by Sensors' +'</label>');
	
	    $(':checkbox').click(function() {
		refreshdata();
	    });
	} else if (mode == 'cycle') {
	    var cycles = '';
	    switch (data.res)
	    {
	    case 'day':
		cycles += '<option value="1"> Previous Day </option>';
		cycles += '<option value="2"> 1 Week Ago </option>';
		cycles += '<option value="3"> 1 Month Ago </option>';
		break;
	    case 'week':
		cycles += '<option value="1"> Previous Week </option>';
		cycles += '<option value="2"> 1 Month Ago </option>';
		cycles += '<option value="3"> 1 Year Ago </option>';
		break;
	    case 'month':
		cycles += '<option value="1"> Previous Month </option>';
		cycles += '<option value="2"> 1 Year Ago </option>';
		break;
	    case 'year':
		cycles += '<option value="1"> Previous Year </option>';
		break;
	    }	    
	    options.append('Previous Cycles:' + 
			   '<form action=""><select name="cycles"'+
			   'multiple="multiple" id="cycles">'+
			   cycles +
			   '</select></form>' );
	    $('#cycles').change(function() {

		refreshdata();
	    });
	}
    }
    
    // Interprets data from the server and updates the table
    function update_table(data) 
    {
	// We've already confirmed we have the right data
	// with the function that calls this

        // data_url gives the json dump of data transferred from database
	data_url = data.data_url;

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

	var table = $('#energystats')

	$.each(data.averages, function(sensor,values) {
	    // Make the row
	    if (first_time) {
		table.append('<tr id="'+sensor+'">'+
			     '<td id="name'+sensor+'">'+
			     data.building + ' ' + sensor +
			     '</td><td id="minute'+sensor+'"></td>' +
			     '<td id="week'+sensor+'"></td>' +
			     '<td id="month'+sensor+'"></td></tr>');
	    }
	    
	    $.each(values, function(average_type,average_value) {
		$('#'+average_type+sensor).empty();
		$('#'+average_type+sensor).append( rnd(average_value) );
	    });

	});

        // $("#energystats").tablesorter(); 
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

	update_table(data);

        // When this function is first called, it is expected that 
        // data_url was defined previously (before loading this file).
        data_url = data.data_url;

        desired_first_record = data.desired_first_record;

        var series_opts = [];
        var series = [];
        var sensor_id,
            group_id,
            graph_opts;

	// Clear the loading animation and put up the various options
        if (first_time) {
	    set_mode_settings(data);
        }

	// get what cycles to plot
	var cycles = [];
	cycles.push(0);
	if ($("#cycles").val()){
	    cycles = cycles.concat($("#cycles").val());
	}

	$.each(cycles, function(cycleID) {
	    xy_pairs[cycleID] = {};
	    // Iterate through each sensor with data points
	    $.each(data.graph_data[cycleID], function(cur_sensor,data_points) {
		xy_pairs[cycleID][cur_sensor] = data_points;
	    });
	    
	    $.each(xy_pairs[cycleID], function(sensor_name, data_points) {
		if (sensor_name =='total') {
		    series.push({
			data: data_points,
			label: data.building + ' ' + sensor_name + ' ' + cycleID,
			color: '#' + data.building_color,
		    });
		} else if ($('#showSensors').is(':checked')) {
		    series.push({
			data: data_points,
			label: data.building + ' ' + sensor_name,
		    });
		}
	    });
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

    // Make the mode selector work
    $('select').change(function() {
	mode = $("select option:selected").val() ;
	first_time = true; // Set to first time such that it reloads everything.
	// Open the loading animation
	$('#graph').empty();
	$('#graph').append(
            '<img class="loading" src="' + MEDIA_URL + 'loading.gif" />');
	refreshdata();
    });
    mainloop();

    
});
