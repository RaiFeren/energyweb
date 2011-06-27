var chart;

$(function () {
    // This function is a callback, called when the DOM is loaded

    var xy_pairs = {};
    var sensor_groups = null;
    var mode = 'cycle';
    var desired_first_record = null;
    var first_time = true;

    var styles = ['ShortDashDotDot', 'Dot', 'DashDot', 
		  'ShortDash', 'ShortDot', 'ShortDashDot'];
    var colorchanges = [0, 10, -20, -10, 20, -30];

    // Clear the graph and put the options up
    function set_mode_settings(data)
    {
        // When data is received the first time,
        // remove the graph's loading animation
        $('#graph').empty();
	
	var options = $("#mode_settings");
	options.empty();
	// Enable the form for switching resolutions
	options.append(
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
		alert(cycleData['total'][0][0] + ", " + cycleData['total'][0][1]);
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
		marginRight: 155,
		marginBottom: 55,
		events: {
		    // Refresh the graph!
		    load: function() {
			// get the series in scope
			var chart_series = this.series; 
			// Refresh data every 10 seconds
			setInterval(function() {
			    
			    $.getJSON(data_url, function(data) {
				write_table(data);
				// get the data from each cycle or sensor
				/*switch(mode) {
				case 'cycle':
				    $.each(data.graph_data, function(cycleID, data) {
					chart_series[cycleID].addPoint(
					    data['total'].pop());
				    });
				    break;
				case 'diagnostic':
				    $.each(data.graph_data[0], 
					   function(sensorID, data) {
					       chart_series[sensorID].addPoint(
						   data.pop());
					   });
				    break;
				}*/ 				
			    });
			}, 10000); // time between redraws in milliseconds
		    }
		}
	    },
	    credits: {
		enabled: false
	    },
	    title: {
		text: null // Disable
	    },
	    xAxis: {
		title: {
		    text: 'Time'
		},
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
		    states: { // Enable line thickening upon hover
			hover: {
			    enabled: true,
			    lineWidth: 5
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
	    series: data_series, // Set data from the json data
	});
    }


    function refreshdata() {
        // Calls built in functions to get JSON data then pass it to a parsing function
        refresh_table_data(); // See detail_table.js
        $.getJSON(data_url, getdata_json_cb);
    }

    function mainloop() {
        refreshdata()
    }

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