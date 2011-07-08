var chart;

$(function () {
    // This function is a callback, called when the DOM is loaded

    var sg_xy_pairs = {};
    var sensor_groups = null;

    function getdata_json_cb(data) {
        // Given data from the server, make a graph.
	if (data.no_results) {
	    alert("No data received. Check data_url.");
	    return;
	}

	var data_series = [];
	var data_colors = [];
	var group_id;

	sensor_groups = data.sensor_groups;
	
	// Get the xy points, color, and label for each sensor group
	for (var i=0; i < sensor_groups.length; i++) {
	    group_id = sensor_groups[i][0];
	    sg_xy_pairs[group_id] = data.sg_xy_pairs[group_id];
	        
	    data_series.push({
		name: sensor_groups[i][1],
		data: sg_xy_pairs[group_id]
	    });
	    data_colors.push('#' + sensor_groups[i][2]);
	}

	// Clear the loading animation and show the download link now
	// that we are about to show the graph:
	$('#graph').empty();
	$('#download').show();

	// Find the x-axis tick options:
	var newTickOptions = tickhelper(timedelta_ms);
	
        // Turning dates into a readable string:
        function process_date(date_obj) {
            var cur_date = new Date(date_obj);
            cur_date.setTime(cur_date.getTime()+cur_date.getTimezoneOffset()*60*1000);
            return hour_format(cur_date) + ", " + cur_date.toDateString();
        }

	// Make the graph title text:
	var titletext = "Energy Usage at Mudd from " +
            process_date(start) + " to " + process_date(end);

	// Actually make the graph:
	chart = new Highcharts.Chart({
	    chart: {
		renderTo: 'graph',
		defaultSeriesType: 'line',
		marginRight: 130,
		marginBottom: 50
	    },
	    credits: {
		enabled: false
	    },
	    title: {
		text: titletext,
		x: -20 //center
	    },
	    xAxis: { 
		title: {
		    text: 'Time'
		},
		type: 'datetime',
		min: start, // Don't autoscale the axis
		max: end,
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
		min: 0,
		plotLines: [{
		    value: 0,
		    width: 1,
		    color: '#808080'
		}]
	    },
	    tooltip: { // Disable tooltip when hovering above a point
		enabled: false
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
	    colors: data_colors, // Set colors from the json data
	    series: data_series, // Set data from the json data
	    exporting:
	    {
		enabled: true,
	    },
	});
    }

    // Initially, show a loading animation instead of the graph
    // and hide the download link while we're waiting for data.
    $('#graph').append(
	'<img class="loading" src="' + MEDIA_URL + 'img/loading.gif" />');
    $('#download').hide();

    // It is expected that data_url was defined previously (before
    // loading this file).
    $.getJSON(data_url, getdata_json_cb);
});