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

	// Actually make the graph:
	chart = new Highcharts.Chart({
	    chart: {
		renderTo: 'graph',
		defaultSeriesType: 'line',
		marginRight: 130,
		marginBottom: 25
	    },
	    credits: {
		enabled: false
	    },
	    title: {
		text: 'Energy Usage at Mudd',
		x: -20 //center
	    },
	    xAxis: {
		type: 'datetime'
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
    // and hide the download link.
    $('#graph').append(
	'<img class="loading" src="' + MEDIA_URL + 'img/loading.gif" />');

    // It is expected that data_url was defined previously (before
    // loading this file).
    $.getJSON(data_url, getdata_json_cb);
});