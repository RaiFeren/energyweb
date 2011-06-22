var chart;

$(function () {
    // This function is a callback, called when the DOM is loaded

    var xy_pairs = {};
    var sensor_groups = null;
    var mode = 'cycle';
    var desired_first_record = null;
    var first_time = true;

    var styles = ['ShortDashDot','Dash','DashDot',
		  'LongDashDotDot','ShortDot','Dot'];
    
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
		cycle_names = {0:'Today',1:'Yesterday',
			       2:'1 Week Ago',3:' 1 Month Ago',
			       4:'1 Year Ago'};
		break;
	    case 'week':
		cycle_names = {0:'This Week',1:'Last Week',
			       2:'1 Month Ago',3:' 1 Year Ago'};
		break;
	    case 'month':
		cycle_names = {0:'This Month', 1:'Last Month', 2:'1 Year Ago'};
		break;
	    case 'year':
		cycle_names = {0:'This Year', 1:'Last Year'};
		break;
	    }	 
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


	switch(mode)
	{
	case 'cycle':
	    $.each(data.graph_data, function(index,cycleData) {
		var cur_label = data.building +
		    '<br/>' + cycle_names[index];
		var curStyle = '';
		if (index == 0) {
		    curStyle = 'Solid';
		} else {
		    curStyle = styles.shift();
		    styles.push(curStyle);
		}
		data_series.push({
		    name: cur_label,			    
		    data: cycleData['total'],
		    dashStyle: curStyle,
		    color: '#' + data.building_color,
		});
	    });
	    break;
	case 'diagnostic':
	    // Iterate through each sensor with data points
	    $.each(data.graph_data[0], 
		   function(cur_sensor,data_points) {

		       var cur_label = data.building 
			   + ' ' + cur_sensor;
		       var curStyle = '';
		       if (cur_sensor == 'total') {
			   curStyle = 'Solid';
		       } else {
			   curStyle = styles.shift();
			   styles.push(curStyle);
		       }
		       data_series.push({
			   name: cur_label,			    
			   data: data_points,
			   dashStyle: curStyle,
			   color: '#' + data.building_color,
		       });
		   });
	    break;
	}

	// Clear the loading animation now
	// that we are about to show the graph:
	$('#graph').empty();

	// Find the x-axis tick options:
	var newTickOptions = tickhelper(timedelta_ms);

	// Actually make the graph:
	chart = new Highcharts.Chart({
	    chart: {
		renderTo: 'graph',
		defaultSeriesType: 'line',
		marginRight: 130,
		marginBottom: 25,
		events: {
		    // Refresh the graph!
		    load: function() {
			// get the series in scope
			var chart_series = this.series; 
			// Refresh data every 10 seconds
			setInterval(function() {
			    
			    $.getJSON(data_url, function(data) {
				write_table(data);
//				// Replace data for each sensor
//				$.each(sensor_groups, function(index, cur_sg) {
//				    group_id = cur_sg[0];
//				    chart_series[index].addPoint(data.sg_xy_pairs[group_id].pop());
//				});
			    });
			}, 10000); // time between redraws in milliseconds
		    }
		}
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
		tickInterval: newTickOptions[0],
		gridLineWidth: 2,
		minorTickInterval: newTickOptions[1],
		dateTimeLabelFormats: { // override with labels set in tickhelper.js
		    second: newTickOptions[2],
		    minute: newTickOptions[2],
		    hour: newTickOptions[2],
		    day: newTickOptions[2],
		    week: newTickOptions[2],
		    month: newTickOptions[2],
		    year: newTickOptions[2]
		}
	    },
	    yAxis: {
		title: {
		    text: 'Power (kW)'
		},
		plotLines: [{
		    value: 0,
		    width: 1,
		    color: '#808080'
		}],
		min: 0,
	    },
	    tooltip: { // enable tooltip when hovering above a point
		enabled: true
	    },
	    legend: {
		layout: 'vertical',
		align: 'right',
		verticalAlign: 'top',
		x: -20,
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