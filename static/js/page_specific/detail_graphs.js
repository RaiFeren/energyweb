$(function () {
    // This function is a callback, called when the DOM is loaded

    var first_time = true;
    var desired_first_record = null;
    var xy_pairs = {};
    var sensor_groups = null;
    var mode = 'sensors'; // Default value
    var cur_building = null;

    // Buildings are defined as rectangles. 
    // Defined as xy pairs, [Top Left, Bottom Right]
    var buildings = {
	'Olin':[[15,90],[30,125],null],
	'Beckman':[[35,100],[50,115],null],
	'Parsons':[[58,60],[100,85],null],
	'Sprague':[[55,100],[75,120],null],
	'Gallileo':[[85,100],[105,115],null],
	'Keck':[[60,130],[105,155],null],
	'TG':[[140,70],[180,90],null],
	'Kingston':[[140,120],[180,140],null],
	'Platt':[[215,55],[270,90], null],
	'Hoch':[[215,115],[270,150],null],
	'South':[[290,60],[325,90], south_url],
	'West': [[290,115],[325,150], west_url],
	'North':[[345,60],[380,90], north_url],
	'East': [[345,115],[380,150], east_url],
	'LAC': [[390,60],[435,90], null],
	'Sontag': [[460,65],[495,95], sontag_url],
	'Atwood': [[460,125],[500,160], atwood_url],
	'Linde':[[545,85],[580,125], linde_url],
	'Case': [[515,130],[555,170], case_url],
    };
    
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
    
    function rnd(x) {
        // (Used to format numbers in the table)
        if (x) {
            return x.toFixed(2);
        }
        else {
            return x;
        }
    }

    function getCursorPosition(e) {
	var camp_map = document.getElementById("campMap");

	var x;
	var y;

	if (e.pageX != undefined && e.pageY != undefined) {
	    x = e.pageX;
	    y = e.pageY;
	}
	else {
	    x = e.clientX + document.body.scrollLeft +
		document.documentElement.scrollLeft;
	    y = e.clientY + document.body.scrollTop +
		document.documentElement.scrollTop;
	}
	// correct x and y such that they are off canvas 
	// not top of page
	x -= camp_map.offsetLeft;
	y -= camp_map.offsetTop;
	return [x,y]
    }


    function draw_map(camp_map) {
	// Declare that we're using a 2d canvas.
	// ...Don't mind that there's no such thing as 3d canvas
	var context = camp_map.getContext("2d");
	context.width = context.width;
	var img = new Image();
	img.src =  MEDIA_URL + 'img/MuddMap.png';
	img.onload = function() {
	    context.drawImage(img,0,0);
	};
    }

    function map_hover_handler(e){
	var draw = false;

	var camp_map = document.getElementById("campMap");
	var context = camp_map.getContext("2d");

	var spot = getCursorPosition(e);
	$.each(buildings, function(name,dimensions) {
	    if (spot[0] > dimensions[0][0]
		&& spot[0] < dimensions[1][0] 
		&& spot[1] > dimensions[0][1] 
		&& spot[1] < dimensions[1][1]) {

		context.font = "bold 12px sans-serif";		
		cur_building = name;
		context.fillText(name, 25, 125);
		draw = true;
//		alert(name);
	    }
	});
	if (draw == false) {
	    draw_map(camp_map);
	}
    }

    function map_click_handler(e) {
	var spot = getCursorPosition(e);
	//alert('Clicked at ' + spot[0] + ',' + spot[1]);

	// Alert user when they've clicked on a building
	$.each(buildings, function(name,dimensions) {
	    if (spot[0] > dimensions[0][0]
		&& spot[0] < dimensions[1][0] 
		&& spot[1] > dimensions[0][1] 
		&& spot[1] < dimensions[1][1]) {
		
		// change pages if possible
		if (dimensions[2]) {
		    window.location = dimensions[2];
		} else {
		    alert("This building doesn't have a page yet!");
		}
	    }
	});
    }

    // Create the clickable links
    function make_map() {
	var camp_map = document.getElementById("campMap");
	draw_map(camp_map);
	camp_map.addEventListener("click", map_click_handler , false);
	camp_map.addEventListener("mousemove", map_hover_handler, false);
    }

    // Clear the graph and put the options up
    function set_mode_settings(data)
    {
        // When data is received the first time,
        // remove the graph's loading animation
        $('#graph').empty();
	
	var options = $("#mode_settings");
	options.empty();
	// Enable the form for switching resolutions
	options.append('View By:' +
		       '<form action=""><select name="period"' +
		       'OnChange="location.href=' +
		       'period.options[selectedIndex].value">' +
		       '<option value="" selected="selected">' +
		       'Select Resolution</option>' +
		       '<option value="'+ day_url +'">Day</option>' +
		       '<option value="'+ week_url +'">Week</option>' +
		       '<option value="'+ month_url +'">Month</option>' +
		       '<option value="'+ year_url +'">Year</option>' +
		       ' </select></form>');
	if (mode == 'sensors') {
	    // Enable checkbox for splitting sensors
	    options.append('<input type = "checkbox" name="'
			   + 'showSensors" id="showSensors">'
			   + '<label for "showSensors">'
			   + 'Show by Sensors' +'</label>');
	
	    $(':checkbox').click(function() {
		refreshdata();
	    });
	} else if (mode == 'cycle') {
	    var cycles = '';
	    switch (data.res)
	    {
	    case 'day':
		cycles += '<option value="1"> Previous Day </option>';
		cycles += '<option value="2"> 1 Week Ago </option>';
		cycles += '<option value="3"> 1 Month Ago </option>';
		cycles += '<option value="4"> 1 Year ago </option>';
		break;
	    case 'week':
		cycles += '<option value="1"> Previous Week </option>';
		cycles += '<option value="2"> 1 Month Ago </option>';
		cycles += '<option value="3"> 1 Year Ago </option>';
		break;
	    case 'month':
		cycles += '<option value="1"> Previous Month </option>';
		cycles += '<option value="2"> 1 Year Ago </option>';
		break;
	    case 'year':
		cycles += '<option value="1"> Previous Year </option>';
		break;
	    }	    
	    options.append('Previous Cycles:' + 
			   '<form action=""><select name="cycles"'+
			   'multiple="multiple" id="cycles">'+
			   cycles +
			   '</select></form>' );
	    $('#cycles').change(function() {
		alert('Saw a change in cycles!');
		refreshdata();
	    });
	}
    }
    
    // Interprets data from the server and updates the table
    function update_table(data) 
    {
	// We've already confirmed we have the right data
	// with the function that calls this

        // data_url gives the json dump of data transferred from database
	data_url = data.data_url;

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
        }

	var table = $('#energystats')

	$.each(data.averages, function(sensor,values) {
	    // Make the row
	    if (first_time) {
		table.append('<tr id="'+sensor+'">'+
			     '<td id="name'+sensor+'">'+
			     data.building + ' ' + sensor +
			     '</td><td id="minute'+sensor+'"></td>' +
			     '<td id="week'+sensor+'"></td>' +
			     '<td id="month'+sensor+'"></td></tr>');
	    }
	    
	    $.each(values, function(average_type,average_value) {
		$('#'+average_type+sensor).empty();
		$('#'+average_type+sensor).append( rnd(average_value) );
	    });

	});

    }
    

    function refreshdata_json_cb(data) {
        // Given new data from the server, update the page (graph and
        // table).


        // TODO: what if somehow we get no results and it's not the 
        // first time?
        if (first_time && data.no_results) {
	    alert('No data! Check connection to sensors.');
            return;
        }

	update_table(data);

        // When this function is first called, it is expected that 
        // data_url was defined previously (before loading this file).
        data_url = data.data_url;

        desired_first_record = data.desired_first_record;

        var series_opts = [];
        var series = [];
        var sensor_id,
            group_id,
            graph_opts;

	// Clear the loading animation and put up the various options
        if (first_time) {
	    set_mode_settings(data);
        }

	// get what cycles to plot
	var cycles = [];
	cycles.push(0);
	if ($("#cycles").val()){
	    //alert('Saw values of ' + $("#cycles").val());
	    cycles = cycles.concat($("#cycles").val());
	    //alert('cycles is ' + cycles);
	}

	$.each(cycles, function(index,cycleID) {
	   // alert('Now reading ' + cycleID);
	    xy_pairs[cycleID] = {};
	    if (data.graph_data[cycleID] == null) {
		alert('Do not have data old enough for cycle ' + cycleID + '!');
	    }
	    else {
		// Iterate through each sensor with data points
		$.each(data.graph_data[cycleID], 
		       function(cur_sensor,data_points) {
		    xy_pairs[cycleID][cur_sensor] = data_points;
		});
		
		$.each(xy_pairs[cycleID], function(sensor_name, data_points) {
		    if (sensor_name =='total') {
			series.push({
			    data: data_points,
			    label: data.building + ' ' + sensor_name + ' ' 
				+ cycleID,
			    color: '#' + data.building_color,
			});
		    } else if ($('#showSensors').is(':checked')) {
			series.push({
			    data: data_points,
			    label: data.building + ' ' + sensor_name,
			});
		    }
		});
	    }
	});
        // Finally, make the graph
        graph_opts = {
            series: {
                lines: {show: true},
                points: {show: false}
            },
            legend: {
                show: true, 
                position: 'ne',
                backgroundOpacity: 0.6,
                noColumns: xy_pairs.length
            },
            yaxis: {
                min: 0,
                tickFormatter: kw_tickformatter,
            },
            xaxis: {
                min: desired_first_record,
                mode: 'time',
                timeformat: '%m/%d <br> %h:%M %p',
                twelveHourClock: true
            },
            grid: {
                show: true,
                color: '#d0d0d0',
                borderColor: '#bbbbbb',
                backgroundColor: { colors: ['#dbefff', '#ffffff']}
            }
        };

        if (first_time) {
            first_time = false;
        }

        $.plot($('#graph'), series, graph_opts);
    
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
        '<img class="loading" src="' + MEDIA_URL + 'img/loading.gif" />');

    // Make the mode selector work
    $('select').change(function() {
	mode = $("select option:selected").val() ;
	first_time = true; // Set to first time such that it reloads everything.
	// Open the loading animation
	$('#graph').empty();
	$('#graph').append(
            '<img class="loading" src="' + MEDIA_URL + 'loading.gif" />');
	refreshdata();
    });
    
    make_map();
    mainloop();

    
});
