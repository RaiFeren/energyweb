var chart;

$(function () {
    // This function is a callback, called when the DOM is loaded

    var sg_xy_pairs = {};
    var sensor_groups = null;

    // TODO: Get these keys from the database!
    // Must be a map to use the "in" functionality efficiently.
    var ac_groups = {"9":0,"10":0,"11":0,"12":0};
    var res_groups = {"1":0,"2":0,"3":0,"4":0,"5":0,"6":0,"7":0,"8":0};

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
	    var plot = false;
	    switch(scope) {
	    case 'all':
		plot = true; break;
	    case 'academic':
		if (cur_sg[0] in ac_groups)
		{ 
		    plot = true; 
		}
		break;
	    case 'residential':
		if (cur_sg[0] in res_groups)
		{ 
		    plot = true; 
		}
		break;
	    }	    

	    if (plot) {
		group_id = cur_sg[0];
		sg_xy_pairs[group_id] = data.sg_xy_pairs[group_id];
		
		data_series.push({
		    name: cur_sg[1],
		    data: sg_xy_pairs[group_id]
		});
		data_colors.push('#' + cur_sg[2]);
	    }
        });

	// Clear the loading animation now
	// that we are about to show the graph:
	$('#graph').empty();

	// MAGIC: 2 hours is the start time.
	var newTickOptions = tickhelper(2*3600*1000);

	// Actually make the graph:
	chart = new Highcharts.Chart({
	    chart: {
		renderTo: 'graph',
		defaultSeriesType: 'line',
		marginRight: 130,
		marginBottom: 40,
		events: {
		    // Update the graph!
		    load: function() {
			var chart_series = this.series; // get the series in scope
			// Refresh data every 10 seconds
			setInterval(function() {

			    $.getJSON(data_url, function(data) {
				// Add a datapoint for each sensor
				
				$.each(sensor_groups, function(index, cur_sg) {
				    group_id = cur_sg[0];
				    if (chart_series[index]) {
					chart_series[index].addPoint(
					    data.sg_xy_pairs[group_id].pop(), true, true);
				    }
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