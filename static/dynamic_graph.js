$(function () {
    // This function is a callback, called when the DOM is loaded

    var first_time = true;
    var desired_first_record = null;
    var sg_xy_pairs = {};
    var sensor_groups = null;

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
    
    function refreshdata_json_cb(data) {
        // Given new data from the server, update the page (graph and
        // table).

        // TODO: what if somehow we get no results and it's not the 
        // first time?
        if (first_time && data.no_results) {
            alert("No data received. Check connection to sensors.");
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

        // Used to mark which lines to plot
        var choice_container =$("#choices");
        var chosen_lines = {};

        if (first_time) {
            sensor_groups = data.sensor_groups;

            // When data is received the first time,
            // remove the graph's loading animation
            $('#graph').empty();

            // Creates table for listing off Buildings
            choice_container.append('Show Buildings:<br/>');
            for (var i=0; i < sensor_groups.length; i++) {

                var build_id = sensor_groups[i][0];
                var build_name = sensor_groups[i][1];
                var build_color = sensor_groups[i][2];

                choice_container.append('<table><td><div id="colorBox'
                                        + build_id
                                        + '">&nbsp;</div></td>'
                                        + '<td><input type="checkbox" name="' 
                                        + build_id
                                        + '" checked="checked" id="selector">'
                                        + '<label for "id' 
                                        + build_id
                                        + '">'
                                        + build_name
                                        + '</label></td></table>');

                var colorid = $("#colorBox" + build_id);
                var linecolor = "#" + build_color;
                colorid.css("background-color", linecolor);
                colorid.css("width", 25);
            }
	    // Make it so checkboxes cause a refresh of the graph.
	    $(':checkbox').click(function() {
		refreshdata();
	    });
        }
        
        // Update which lines we want to plot. Must happen each update
        choice_container.find("input:checked").each(function () {
            var group_number = $(this).attr("name");
            chosen_lines[group_number]=''; // dummy so can use the in function
        });

        for (var i=0; i < sensor_groups.length; i++) {
            group_id = sensor_groups[i][0];
    
            if (first_time) {
                sg_xy_pairs[group_id] = data.sg_xy_pairs[group_id];
            } else {
                /* We've already collected some data, so combine it 
                 * with the new.  About this slicing:  We're 
                 * discarding our latest record, preferring the new copy
                 * from the sever, since last time we may have e.g. 
                 * collected data just before a sensor reported a 
                 * reading (for the 10-second time period we were 
                 * considering).  Hence, while the latest record may be
                 * incomplete, the second latest (and older) records are
                 * safe---they will never change.
                 */
                var j;
                for (j=0; j < sg_xy_pairs[group_id].length; j++) {
                    if (sg_xy_pairs[group_id][j][0] >= desired_first_record) {
                        // We break out of the loop when j is the index
                        // of the earliest record on or later than
                        // desired_first_record
                        break;
                    }
                }
                sg_xy_pairs[group_id] = sg_xy_pairs[group_id].slice(j,
                        sg_xy_pairs[group_id].length - 1
                    ).concat(
                        data.sg_xy_pairs[group_id]);
            }
            
            // plot only the selected lines
            if (group_id in chosen_lines) {
                series.push({
                    data: sg_xy_pairs[group_id],
                    label: sensor_groups[i][1],
                    color: '#' + sensor_groups[i][2]
                });
            }
        }
        // Finally, make the graph
        graph_opts = {
            series: {
                lines: {show: true},
                points: {show: false}
            },
            legend: {
                show: false, // Set to true if want it back...
                position: 'ne',
                backgroundOpacity: 0.6,
                noColumns: sensor_groups.length
            },
            yaxis: {
                min: 0,
                tickFormatter: kw_tickformatter,
            },
            xaxis: {
                min: desired_first_record,
                mode: 'time',
                timeformat: '%h:%M %p',
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
    
        if (first_time) {
            first_time = false;
        }
    
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
        '<img class="loading" src="' + MEDIA_URL + 'loading.gif" />');
    mainloop();

    
});
