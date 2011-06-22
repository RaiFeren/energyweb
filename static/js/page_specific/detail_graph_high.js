var chart;

$(function () {
    // This function is a callback, called when the DOM is loaded

    var xy_pairs = {};
    var sensor_groups = null;
    var mode = 'cycle';
    var desired_first_record = null;
    var first_time = true;

    var styles = ['Solid','Dot','Dash','DashDot','LongDashDotDot'];
    
    function rnd(x)
    {
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

	if (mode == 'cycle') {
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

    function getdata_json_cb(data) {
        // Given data from the server, make a graph.
	if (data.no_results) {
	    alert("No data received. Check sensor connections.");
	    return;
	}

	var data_series = [];
	var data_colors = [];
	var group_id;

	sensor_groups = data.sensor_groups;

        set_mode_settings(data);
        write_table(data);

	// get what cycles to plot
	var cycles = [];
	cycles.push(0);
	if ($("#cycles").val()){
	    cycles = cycles.concat($("#cycles").val());
	}

	$.each(cycles, function(index,cycleID) {
	    xy_pairs[cycleID] = {};
	    if (data.graph_data[cycleID] == null) {
		alert('Do not have data old enough for cycle ' + 
		      cycleID + '!');
	    }
	    else {
		if (mode == 'diagnostic') {
		// Iterate through each sensor with data points
		    $.each(data.graph_data[cycleID], 
			   function(cur_sensor,data_points) {
			       xy_pairs[cycleID][cur_sensor] = data_points;
			   });
		} else {
		    xy_pairs[cycleID]['total'] = 
			data.graph_data[cycleID]['total'];
		}
		
		$.each(xy_pairs[cycleID], function(sensor_name, data_points) {
		    var cur_label = data.building;
		    if (mode == 'cycle') {
			cur_label += ' ' + cycle_names[cycleID];
		    }
		    else {
			cur_label += ' ' + sensor_name;
		    }
		    var curStyle = styles.shift();
		    styles.push(curStyle);
		    data_series.push({
                        name: cur_label,			    
                        data: data_points,
			dashStyle: curStyle,
			color: '#' + data.building_color,
		    });
		});	   
	    }
	});

	// Clear the loading animation now
	// that we are about to show the graph:
	$('#graph').empty();

	// Actually make the graph:
	chart = new Highcharts.Chart({
	    chart: {
		renderTo: 'graph',
		defaultSeriesType: 'line',
		marginRight: 130,
		marginBottom: 25,
//		events: {
//		    // Refresh the graph!
//		    load: function() {
//			var chart_series = this.series; 
//                    // get the series in scope
//			// Refresh data every 10 seconds
//			setInterval(function() {
//
//			    $.getJSON(data_url, function(data) {
//				// Replace data for each sensor
//				$.each(sensor_groups, function(index, cur_sg) {
//				    group_id = cur_sg[0];
//				    chart_series[index].addPoint(data.sg_xy_pairs[group_id].pop());
//				});
//			    });
//			}, 10000); // time between redraws in milliseconds
//		    }
//		}
	    },
	    credits: {
		enabled: false
	    },
	    title: {
		text: 'Energy Usage at ' + data.building +
                    ' over a ' + data.res,
		x: -20 //center
	    },
	    xAxis: {
		type: 'datetime',
		min: data.desired_first_record,
		tickInterval: 4*3600 * 1000, // Every 4 hr
		tickWidth: 2,
		minorTickInterval: 3600 * 1000, // Every hr
	    },
	    yAxis: {
		title: {
		    text: 'Power (kW)'
		},
		plotLines: [{
		    value: 0,
		    width: 1,
		    color: '#808080'
		}]
	    },
	    tooltip: { // enable tooltip when hovering above a point
		enabled: true
	    },
	    legend: {
		layout: 'vertical',
		align: 'right',
		verticalAlign: 'top',
		x: -10,
		y: 100,
		borderWidth: 0
	    },
	    plotOptions: {
		line: {
		    states: { // Disable line thickening upon hover
			hover: {
			    enabled: false
			}
		    },
		    marker: { // Disable markers at each point
			enabled: false,
			states: {
			    hover: {
				enabled: false
			    }
			}
		    }
		}
	    },
//	    colors: data_colors, // Set colors from the json data
	    series: data_series // Set data from the json data
	});
    }


    function refreshdata() {
        // Calls built in functions to get JSON data then pass it to a parsing function
        $.getJSON(data_url, getdata_json_cb);
    }

    function mainloop() {
        refreshdata()
        //setTimeout(mainloop, 10000);
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

    // Initially, show a loading animation instead of the graph
    $('#graph').append(
	'<img class="loading" src="' + MEDIA_URL + 'img/loading.gif" />');

    // It is expected that data_url was defined previously (before
    // loading this file).
    $.getJSON(data_url, getdata_json_cb);
});