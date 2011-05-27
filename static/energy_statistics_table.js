$(function () 
{
  var first_time = true;
  alert("This function ran!");

  // Theoretically data_url should be defined.
  alert("data_url is: " + data_url);

  function refreshdata_json_cb(data) 
  {

    // When this function is first called, it is expected that 
    // data_url was defined previously (before loading this file).
    data_url = data.data_url;
    alert("we have a data_url which is: " + data_url);
    // Given new data from the server, update the table

    // Given new data from the server, update the table

    // TODO: what if somehow we get no results and it's not the 
    // first time?
    if (first_time && data.no_results) 
    {
      alert("we received no data :(");
      return; // TODO: tell the user what happened?
    }
        var series_opts = [];
        var series = [];
        var missed_week_average, 
            missed_month_average, 
            sensor_id,
            group_id,
            group_week_average, 
            group_month_average, 

        if (first_time) {
            sensor_groups = data.sensor_groups;
        }
    
        for (var i=0; i < sensor_groups.length; i++) {
            alert("on sensor number: " + i);
            group_week_average = 0;
            group_month_average = 0;
            missed_week_average = false;
            missed_month_average = false;
            group_id = sensor_groups[i][0];
    
            for (var j=0; j < sensor_groups[i][3].length; j++) {
                sensor_id = sensor_groups[i][3][j][0];

                // update the per-sensor table averages, if appropriate
                if (sensor_groups[i][3].length > 1) {
                    if (sensor_id in data.week_averages) {
                        $('#WeeklyS' + sensor_id).empty();
                        $('#WeeklyS' + sensor_id).append(rnd(
                            data.week_averages[sensor_id]));
                    } else {
                        missed_week_average = true;
                    }
                    if (sensor_id in data.month_averages) {
                        $('#MonthlyS' + sensor_id).empty();
                        $('#MonthlyS' + sensor_id).append(rnd(
                            data.month_averages[sensor_id]));
                    } else {
                        missed_month_average = true;
                    }
                }
    
                // Add sensor averages to the sensor group averages...
                if (sensor_id in data.week_averages) {
                    group_week_average += data.week_averages[sensor_id];
                }
                if (sensor_id in data.month_averages) {
                    group_month_average += data.month_averages[sensor_id];
                }
            }
    
            // Now update table averages for this sensor group
            if (! missed_week_average) {
                $('#WeeklySG' + group_id).empty();
                $('#WeeklySG' + group_id).append(
                    rnd(group_week_average));
            }
            if (! missed_month_average) {
                $('#MonthlySG' + group_id).empty();
                $('#MonthlySG' + group_id).append(
                    rnd(group_month_average));
            }
        }
    
        if (first_time) {
            first_time = false;
        }
    
        setTimeout(refreshdata, 10000);
  }

  function refreshdata() 
  {
    $.getJSON(data_url, refreshdata_json_cb);
  }

  // Start getting data!
  refreshdata();

})();