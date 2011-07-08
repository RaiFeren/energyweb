$(function () 
{
    var first_time = true;
    var desired_first_record = null;
    var sensor_groups = null;

    function array_index_of(ar, x) {
        // (IE doesn't have Array.indexOf)
        for (var i=0; i < ar.length; i++) {
            if (ar[i] == x) {
                return i;
            }
        }
        return -1;
    }

    function rnd(x) {
        // (Used to format numbers in the table)
        if (x) {
            return x.toFixed(2);
        }
        else {
            return x;
        }
    }

    // Interprets data from the server and updates the table
    function refreshdata_json_cb(data) 
    {
	if (first_time && data.no_results)
	{
	    alert("No data received. Check connection to sensors.");
	    return;
	}

        // data_url gives the json dump of data transferred from database
	data_url = data.data_url;

	// defines where the start of data is
        // used in the graph, not really here.
	desired_first_record = data.desired_first_record;

	var missed_min_average,
            missed_week_average,
	    missed_month_average,
	    sensor_id,
       	    group_name,
            group_current,
	    group_week_average,
	    group_month_average;

        // get the sensor groups
        if (first_time) {
            sensor_groups = data.sensor_groups;
	    first_time = false;
        }

        $.each(sensor_groups, function(index, snr_gp){
            group_current = 0;
	    group_week_average = 0;
	    group_month_average = 0;
            missed_min_average = false;
	    missed_week_average = false;
	    missed_month_average = false;
	    group_name = snr_gp[1];

            // Increment building values for each sensor that belongs to it
            $.each( snr_gp[3], function(index, cur_snr){

		sensor_id = cur_snr[0];

                if (sensor_id in data.min_averages) 
                    group_current += data.min_averages[sensor_id];
		if (sensor_id in data.week_averages)
		    group_week_average += data.week_averages[sensor_id];
		if (sensor_id in data.month_averages)
		    group_month_average += data.month_averages[sensor_id];
	    });
                        
	    // Update the averages in the table for the sensor group.
	    // id for placement should be: curr{buildingname}
            if (! missed_min_average)
            {
                $('#curr' + group_name).empty();
                $('#curr' + group_name).append( rnd(group_current) );
            }
	    // id for placement should be: week{buildingname}
	    if (! missed_week_average)
	    {
		$('#week' + group_name).empty();
		$('#week' + group_name).append( rnd( group_week_average ) );
	    }
	    // id for placement should be: month{buildingname}
	    if (! missed_month_average)
	    {
		$('#month' + group_name).empty();
		$('#month' + group_name).append( rnd( group_month_average) );
	    }

        });
	
        $("#energystats").tablesorter({widgets: ['zebra']}); 
	setTimeout(refreshdata, 10000);
    }

    // Get data from server and pass it to the table builder function.
    function refreshdata() 
    {
	//alert("In refreshdata()");
	$.getJSON(data_url, refreshdata_json_cb);
    }

    // Start getting data!
    refreshdata();

});