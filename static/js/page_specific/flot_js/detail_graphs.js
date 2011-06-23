$(function () {
    // This function is a callback, called when the DOM is loaded

    var first_time = true;
    var desired_first_record = null;
    var xy_pairs = {};
    var sensor_groups = null;
    var mode = 'cycle'; // Default value
    var cycle_names = null;
    
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
	if (mode == 'diagnostic') {
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
	    cycle_names = null;
	    switch (data.res)
	    {
	    case 'day':
		cycles += '<option value="1"> Previous Day </option>';
		cycles += '<option value="2"> 1 Week Ago </option>';
		cycles += '<option value="3"> 1 Month Ago </option>';
		cycles += '<option value="4"> 1 Year Ago </option>';
		cycle_names = {0:'Today',1:'Yesterday',
			       2:'1 Week Ago',3:' 1 Month Ago',
			       4:'1 Year Ago'};
		break;
	    case 'week':
		cycles += '<option value="1"> Previous Week </option>';
		cycles += '<option value="2"> 1 Month Ago </option>';
		cycles += '<option value="3"> 1 Year Ago </option>';
		cycle_names = {0:'This Week',1:'Last Week',
			       2:'1 Month Ago',3:' 1 Year Ago'};
		break;
	    case 'month':
		cycles += '<option value="1"> Previous Month </option>';
		cycles += '<option value="2"> 1 Year Ago </option>';
		cycle_names = {0:'This Month', 1:'Last Month', 2:'1 Year Ago'};
		break;
	    case 'year':
		cycles += '<option value="1"> Previous Year </option>';
		cycle_names = {0:'This Year', 1:'Last Year'};
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
    
    function write_table(data)
    {
        var table = $('#energystats');
        switch (mode) 
	{
        case 'diagnostic':
            var data_source = data.diagnosticTable;
            var data_row = data.diagnosticRow;
            break;
        case 'cycle':
            var data_source = data.cycleTable;
            var data_row = data.cycleRow;
            break;
        }
        

        if (first_time) {
            table.empty();
            var table_head = $('#trhead');
            table_head.empty();
            switch (mode) 
	    {
            case 'cycle':
                table_head.append('<th>Cycle</th>'+
                    '<th>Average This Cycle (kW)</th>'+
                    '<th>Max This Cycle (kW)</th>'+
                    '<th>Integrated Power This Cycle (kW*hr)</th>');
		break;
            case 'diagnostic':
                table_head.append('<th>Sensor</th>'+
                    '<th>Average This Minute (kW)</th>'+
	            '<th>Average This Interval (kW)</th>'+
	            '<th>Integrated Power This Interval (kW*hr)</th>');
                break;
            }
        }
   
        // Write data to each row
	$.each(data_source, function(source,values) {
	    // Make the row
	    if (first_time) {
		table.append('<tr id="row'+source+'"></tr>');
                var table_row = $('#row'+source);
		var source_name = ''
		switch(mode)
		{
		case 'cycle':
		    $.each(cycle_names, function(index,value) {
			if (index == parseInt(source)) {
			    source_name = value;
			}
		    });
		    break;
		default:
		    source_name = source;
		    
		}

                table_row.append(
                    '<td id="name'+source+'">'
                        +data.building + ' ' + source_name
                        +'</td>');
                $.each(data_row, function(index,type) {
                    table_row.append(
                        '<td id="'+type+source+'">&nbsp;</td>');
                });
	    }
	    
	    // Insert data values
	    $.each(values, function(type,statistic) {
		$('#'+type+source).empty();
		$('#'+type+source).append( rnd(statistic) );
	    });

	});
     
    }

    function refreshdata_json_cb(data) {
        // Given new data from the server, update the page (graph and
        // table).

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

	$.each(cycles, function(index,cycleID) {
	    xy_pairs[cycleID] = {};
	    if (data.graph_data[cycleID] == null) {
		alert('Do not have data old enough for cycle ' + cycleID + '!');
	    }
	    else {
		// Iterate through each sensor with data points
		$.each(data.graph_data[cycleID], 
		       function(cur_sensor,data_points) {
		    xy_pairs[cycleID][cur_sensor] = data_points;
		});
		
		$.each(xy_pairs[cycleID], function(sensor_name, data_points) {
		    var cur_label = data.building;
		    if (mode == 'cycle') {
			cur_label += ' ' + cycle_names[cycleID];
		    }
		    else {
			cur_label += ' ' + sensor_name;
		    }
		    if (sensor_name =='total') {
			series.push({
			    data: data_points,
			    label: cur_label,
			    color: '#' + data.building_color,
			    points: { symbol:'triangle' },
			});
		    } else if ($('#showSensors').is(':checked')) {
			series.push({
			    data: data_points,
			    label: cur_label,
			    points: { symbol:'triangle' },
			});
		    }
		});
	    }
	});
        // Finally, make the graph
        graph_opts = {
            series: {
                lines: {show: true},
                points: {show: false, radius:3}
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
                timeformat: '%m/%d <br> %h:%M %p',
                twelveHourClock: true
            },
            grid: {
                show: true,
                color: '#d0d0d0',
                borderColor: '#bbbbbb',
                backgroundColor: { colors: ['#dbefff', '#ffffff']}
            }
        };

	write_table(data);

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
        '<img class="loading" src="' + MEDIA_URL + 'img/loading.gif" />');

    // Make the mode selector work
    $('select').change(function() {
	mode = $("select option:selected").val() ;
	first_time = true; // Set to first time such that it reloads everything.
	// Open the loading animation
	$('#graph').empty();
	$('#graph').append(
            '<img class="loading" src="' + MEDIA_URL + 'img/loading.gif" />');
	refreshdata();
    });
    
    mainloop();
});
