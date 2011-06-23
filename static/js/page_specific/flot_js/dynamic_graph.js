Highcharts.setOptions({
    global: {
	useUTC: false
    }
});

var chart;

$(function () {
    // This function is a callback, called when the DOM is loaded

    var first_time = true;
    var desired_first_record = null;
    var sg_xy_pairs = {};
    var sensor_groups = null;
    // Create our chart object right away - options can be added later.
    chart = new Highcharts.Chart({
        chart: {
          renderTo: 'graph',
          defaultSeriesType: 'line',
          marginRight: 130,
          marginBottom: 25
        },
        title: {
          text: 'Energy Usage in the Last 3 Hours',
          x: -20 //center
        },
        xAxis: {
          type: 'datetime'
        },
        yAxis: {},
        tooltip: {
          formatter: function() {
              return '<b>' + this.series.name +'</b><br/>'+this.x +': '+ this.y +'ÂkW';
          }
        },
        legend: {
          layout: 'vertical',
          align: 'right',
          verticalAlign: 'top',
          x: -10,
          y: 100,
          borderWidth: 0
        },
        point: {
            marker: {enabled: false}
        },
        series: [{
            data: [29.9, 71.5, 106.4, 129.2, 144.0, 176.0, 135.6, 148.5, 216.4, 194.1, 95.6, 54.4]
	}]
    }); 

    function refreshdata_json_cb(data) {
        // Given new data from the server, update the graph.
        
        // Alert the user if we have no data and it is the first time.
        if (first_time && data.no_results) {
          alert("No data received. Check connection to sensors.");
          return;
        }

        // When this function is first called, it is expected that 
        // data_url was defined previously (before loading this file).
        data_url = data.data_url;

        desired_first_record = data.desired_first_record;

        var sensor_id, group_id;

        if (first_time) {
            sensor_groups = data.sensor_groups;

            // When data is received the first time,
            // remove the graph's loading animation
           // $('#graph').empty();
        }

        // Push each sensor group's data onto the series
        $.each(sensor_groups,function(index,cur_group) {
	    group_id = cur_group[0];
    
            if (first_time) {
                sg_xy_pairs[group_id] = data.sg_xy_pairs[group_id];
            } else {
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
            
            
            chart.addSeries({
                name: cur_group[1],
                data: sg_xy_pairs[group_id]
            });
	});

    first_time = false;
    

    } // END function refreshdata_json_cb
    

    function refreshdata() {
        // Calls built in functions to get JSON data then pass it to a parsing function
        //$.getJSON(data_url, refreshdata_json_cb);
        //chart.series.push({name: 'something', data: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]});
    }

    function mainloop() {
        refreshdata()
        //setTimeout(mainloop, 10000);
    }

    // Initially, show a loading animation instead of the graph
    $('#graph').append(
      '<img class="loading" src="' + MEDIA_URL + 'img/loading.gif" />');
    mainloop();

});
