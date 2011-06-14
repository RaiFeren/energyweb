$(function () {
    // This function is a callback, called when the DOM is loaded

    var sg_xy_pairs = {};
    var sensor_groups = null;

    function kw_tickformatter(val, axis) {
        // Workaround to get units on the y axis
        return val + " kW";
    }

    function getdata_json_cb(data) {
        // Given data from the server, update the graph.
        if (data.no_results) {
	    alert("No data received. Check connection to sensors.");
            return;
        }
    
        var series_opts = [];
        var show_points = false;
        var series = [];
        var sensor_id,
            group_id,
            graph_opts;

        sensor_groups = data.sensor_groups;

        // When data is received, remove the graph's loading animation
        // and show the download link
        $('#graph').empty();
        $('#download').show();
    
        for (var i=0; i < sensor_groups.length; i++) {
            group_id = sensor_groups[i][0];
    
            sg_xy_pairs[group_id] = data.sg_xy_pairs[group_id];

            show_points = data.show_points;
            
            series.push({
                data: sg_xy_pairs[group_id],
                label: sensor_groups[i][1],
                color: '#' + sensor_groups[i][2]
            });
        }
        // Finally, make the graph
        graph_opts = {
            series: {
                lines: {show: true},
                points: {show: show_points, radius: 4}
            },
            legend: {
                show: true,
                position: 'ne',
                backgroundOpacity: 0.6,
                noColumns: sensor_groups.length
            },
            yaxis: {
                min: 0,
                tickFormatter: kw_tickformatter,
            },
            xaxis: {
                min: start,
                max: end,
                mode: 'time',
                timeformat: '%m/%d/%y %h:%M %p',
                twelveHourClock: true
            },
            grid: {
                show: true,
                color: '#d0d0d0',
                borderColor: '#bbbbbb',
                backgroundColor: { colors: ['#dbefff', '#ffffff']}
            }
        };
        $.plot($('#graph'), series, graph_opts);
    }
    
    // Initially, show a loading animation instead of the graph 
    // and hide the download link.
    $('#graph').append(
        '<img class="loading" src="' + MEDIA_URL + 'img/loading.gif" />');
    $('#download').hide();

    // It is expected that data_url was defined previously (before
    // loading this file).
    $.getJSON(data_url, getdata_json_cb);


});
