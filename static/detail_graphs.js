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
            return; // TODO: tell the user what happened?
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

        if (first_time) {
            sensor_groups = data.sensor_groups;

            // When data is received the first time,
            // remove the graph's loading animation
            $('#graph').empty();            
        }

        cur_sensor = 'total'
    
        if (first_time) {
            xy_pairs[cur_sensor] = data.xy_pairs[cur_sensor];
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
            for (j=0; j < xy_pairs[cur_sensor].length; j++) {
                if (xy_pairs[cur_sensor][j][0] >= desired_first_record) {
                    // We break out of the loop when j is the index
                    // of the earliest record on or later than
                    // desired_first_record
                    break;
                }
            }
            xy_pairs[cur_sensor] = xy_pairs[cur_sensor].slice(j,
                                                              xy_pairs[cur_sensor].length - 1
                                                             ).concat(
                                                                 data.xy_pairs[cur_sensor]);
            
            // plot

            series.push({
                data: xy_pairs[cur_sensor],
                label: cur_sensor, //sensor_groups[i][1],
                //color: '#' + sensor_groups[i][2]
            });
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