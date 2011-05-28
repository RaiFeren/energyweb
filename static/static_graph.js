$(function () {
    // This function is a callback, called when the DOM is loaded

    var sg_xy_pairs = {};
    var sensor_groups = null;

    function kw_tickformatter(val, axis) {
        // Workaround to get units on the y axis
        return val + " kW";
    }
    
    // For writing data to a table under the graph. 
    // HACK solution to 'how do I download data?'
    function writeOutput(data) {
        var outputTable = ['<table>'];

        var row = ['<tr><td>Time'];
        for (var i=0; i<data.length; i++){
            row.push(data[i]['label']); // add Names of buildings
        }
        outputTable.push( row.join('</td><td>'), '</td></tr>');

        // loop through all times in range.
        for (var j=0; i<data[0]['data'].length; j++) {
            var row = [data[0]['data'][j][0]]; // grab the time

            // loop through all buildings
            for (var i=0; i<data.length; j) {
                row.push(data[i]['data'][j][1]); // add y value for each building
            }
            outputTable.push('<tr><td>', row.join('</td><td>'), '</td></tr>');
        }
        outputTable.push('</table>');

        // insert table to html
        $('#outputDiv').append(outputTable.join(''));
    }

    function getdata_json_cb(data) {
        // Given data from the server, update the graph.
        if (data.no_results) {
            return; // TODO: tell the user what happened?
        }
    
        var series_opts = [];
        var show_points = false;
        var series = [];
        var sensor_id,
            group_id,
            graph_opts;

        sensor_groups = data.sensor_groups;

        // When data is received, remove the graph's loading animation
        $('#graph').empty();
    
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
        writeOutput(series);
    }
    
    // Initially, show a loading animation instead of the graph
    $('#graph').append(
        '<img class="loading" src="' + MEDIA_URL + 'loading.gif" />');
    $('#outputDiv').hide()

    // Make it so data toggles visibility when click on the button.
    $('#getData').click(function() {
        $('#outputDiv').toggle();
    });

    // It is expected that data_url was defined previously (before
    // loading this file).
    $.getJSON(data_url, getdata_json_cb);


});
