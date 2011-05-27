alert("this alert is in the external javascript file.");

$(function () 
{
    var debug = true;
    var first_time = true;
    alert("This function ran!");

    // Theoretically data_url should be defined.
    alert("data_url is: " + data_url);

    // Take in new data from the server and update the table.
    function refreshdata_json_cb(data) 
    {
	if (first_time && data.no_results)
	{
	    alert("No data received :(");
	    return;
	}

	// We expect that data_url actually exists -_-
	data_url = data.data_url;

	// TODO: what is this here for?
	desired_first_record = data.desired_first_record;

	// TODO: what are all of these variables for?
	var series_opts = [];
	var series = [];
	var missed_week_average,
	    missed_month_average,
	    sensor_id,
       	    group_name,
	    group_week_average,
	    group_month_average;

	for (var i=0; i < sensor_groups.length; i++)
	{
	    group_week_average = 0;
	    group_month_average = 0;
	    missed_week_average = false;
	    missed_month_average = false;
	    group_name = sensor_groups[i][1];

	    for (var j=0; j < sensor_groups[i][3].length; j++)
	    {
		sensor_id = sensor_groups[i][3][j][0];

		// Add sensor's average to the sensor group's average.
		if (sensor_id in data.week_averages)
		{
		    group_week_average += data.week_averages[sensor_id];
		}
		if (sensor_id in data.month_averages)
		{
		    group_month_average += data.month_averages[sensor_id];
		}
	    }

	    // Update the averages in the table for the sensor group.
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
	}
	
	if (first_time) 
	{
	    first_time = false;
	}

	setTimeout(refreshdata, 10000);
    }

    // Get data from server and pass it to the table builder function.
    function refreshdata() 
    {
	alert("In refreshdata()");
	$.getJSON(data_url, refreshdata_json_cb);
    }

    // Start getting data!
    refreshdata();

})();