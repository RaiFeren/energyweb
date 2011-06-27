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
        $.each(sensor_groups, function(index,cur_sg) {
            group_id = cur_sg[0];
            sg_xy_pairs[group_id] = data.sg_xy_pairs[group_id];
	    
	    data_series.push({
		name: cur_sg[1],
		data: sg_xy_pairs[group_id]
	    });
	    data_colors.push('#' + cur_sg[2]);
        });

	// Clear the loading animation now
	// that we are about to show the graph:
	$('#graph').empty();

	var newTickOptions = tickhelper(2*3600*1000);

	// Actually make the graph:
	chart = new Highcharts.Chart({
	    chart: {
		renderTo: 'graph',
		defaultSeriesType: 'line',
		marginRight: 130,
		marginBottom: 40,
		events: {
		    // Refresh the graph!
		    load: function() {
			var chart_series = this.series; // get the series in scope
			// Refresh data every 10 seconds
			setInterval(function() {

			    $.getJSON(data_url, function(data) {
				// Replace data for each sensor
				$.each(sensor_groups, function(index, cur_sg) {
				    group_id = cur_sg[0];
				    chart_series[index].addPoint(data.sg_xy_pairs[group_id].pop());
				});
			    });
			}, 10000); // time between redraws in milliseconds
		    }
		}
	    },
	    credits: {
		enabled: false
	    },
	    title: {
		text: 'Energy Usage at Mudd in the Past 2 Hours',
		x: -20 //center
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
	    series: data_series // Set data from the json data
	});
    }

    // Initially, show a loading animation instead of the graph
    $('#graph').append(
	'<img class="loading" src="' + MEDIA_URL + 'img/loading.gif" />');

    // It is expected that data_url was defined previously (before
    // loading this file).
    $.getJSON(data_url, getdata_json_cb);
});