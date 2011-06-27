var chart;

$(function () {
    // This function is a callback, called when the DOM is loaded

    var xy_pairs = {};
    var sensor_groups = null;
    var mode = 'cycle';
    var desired_first_record = null;
    var first_time = true;

    function rnd(x)
    {
	// (Used to format numbers in the table)
        if (x) {
            return x.toFixed(2);
        }
        else {
            return x;
        }
    }

    // Clear the graph and put the options up
    function set_table_mode_settings(data)
    {
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
    
    function write_table(data)
    {
        var table = $('#energystats');
        switch (mode) 
	{
        case 'diagnostic':
            var data_source = data.diagnosticTable;
            var data_row = data.diagnosticRow;
            break;
        case 'cycle':
            var data_source = data.cycleTable;
            var data_row = data.cycleRow;
            break;
        }
        

        if (first_time) {
            table.empty();
            var table_head = $('#trhead');
            table_head.empty();
            switch (mode) 
	    {
            case 'cycle':
                table_head.append('<th>Cycle</th>'+
                    '<th>Average This Cycle (kW)</th>'+
                    '<th>Integrated Power This Cycle (kW*hr)</th>');
		break;
            case 'diagnostic':
                table_head.append('<th>Sensor</th>'+
                    '<th>Average This Minute (kW)</th>'+
	            '<th>Average This Interval (kW)</th>'+
	            '<th>Integrated Power This Interval (kW*hr)</th>');
                break;
            }
        }
   
        // Write data to each row
	$.each(data_source, function(source,values) {
	    // Make the row
	    if (first_time) {
		table.append('<tr id="row'+source+'"></tr>');
                var table_row = $('#row'+source);
		var source_name = ''
		switch(mode)
		{
		case 'cycle':
		    $.each(cycle_names, function(index,value) {
			if (index == parseInt(source)) {
			    source_name = value;
			}
		    });
		    break;
		default:
		    source_name = source;
		}

                table_row.append(
                    '<td id="name'+source+'">'
                        +data.building + ' ' + source_name
                        +'</td>');
                $.each(data_row, function(index,type) {
                    table_row.append(
                        '<td id="'+type+source+'">&nbsp;</td>');
                });
	    }
	    
	    // Insert data values
	    $.each(values, function(type,statistic) {
		$('#'+type+source).empty();
		$('#'+type+source).append( rnd(statistic) );
	    });
	});
    }

    function getdata_json_table_cb(data) {
        // Given data from the server, make a table.
	if (data.no_results) {
	    alert("No data received. Check sensor connections.");
	    return;
	}

	sensor_groups = data.sensor_groups;

        set_table_mode_settings(data);
        write_table(data);
    }


    function refresh_table_data() {
        // Calls built in functions to get JSON data then pass it to a parsing function
        $.getJSON(table_url, getdata_json_table_cb);
    }

    // It is expected that data_url was defined previously (before
    // loading this file).
    $.getJSON(table_url, getdata_json_table_cb);
});