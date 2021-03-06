$(function () {
    // This function is a callback, called when the DOM is loaded

    // Buildings are defined as rectangles. 
    // Defined as xy pairs, [Top Left, Bottom Right, redirectURL, HOVER]
    // HOVER gives the center of the hover indicator, and its color in hex.

    var buildings = {
	'Olin':[[10,35],[22,75],null,
                null],
	'Beckman':[[23,45],[44,65],null,
                   null],
	'Parsons':[[48,10],[90,35],null,
                   null],
	'Sprague':[[45,45],[65,70],null,
                   null],
	'Gallileo':[[75,45],[95,65],null,
                    null],
	'Keck':[[50,80],[92,105],null,
                null],
	'TG':[[135,20],[170,40],null,
              null],
	'Kingston':[[130,65],[170,90],null,
                    null],
	'Platt':[[210,5],[255,40], null,
                 null],
	'Hoch':[[210,65],[255,100],null,
                null],
	'South':[[283,10],[320,40], south_url,
		 [[300,23],'#A63F00']],
	'West': [[283,60],[320,100], west_url,
		 [[300,80],'#000000']],
	'North':[[335,10],[370,40], north_url,
		 [[350,23],'#FF0000']],
	'East': [[335,60],[370,100], east_url,
		 [[350,80],'#B700FF']],
	'LAC': [[380,10],[425,45], null,
                null],
	'Sontag': [[450,10],[490,50], sontag_url,
		   [[468,30],'#FFDD02']],
	'Atwood': [[450,75],[488,110], atwood_url,
		   [[468,92],'#00bd39']],
	'Linde':[[538,35],[567,75], linde_url,
		 [[552,52],'#02BCFF']],
	'Case': [[508,75],[547,115], case_url,
		 [[526,96],'#D100A0']],
    };
    // To prevent repeats of renders such as building names and hover indicators
    var cur_build = null;
  
    function array_index_of(ar, x) {
        // (IE doesn't have Array.indexOf)
        for (var i=0; i < ar.length; i++) {
            if (ar[i] == x) {
                return i;
            }
        }
        return -1;
    }
    
    // This function put in because of the highlights occuring really off on the 
    // x-axis. Source of fix: 
    // http://stackoverflow.com/questions/5085689/tracking-mouse-position-in-canvas/5086147#5086147
    function findPos(obj) {
	var curleft = curtop = 0;
	if (obj.offsetParent) {
	    do {
		curleft += obj.offsetLeft;
		curtop += obj.offsetTop;
	    } while (obj = obj.offsetParent);
	    return { x: curleft, y: curtop };
	}
    }

    // source: 
    // http://snipt.net/sayanriju/get-cursor-position-of-clicked-mouse-on-a-html5-canvas/
    function getCursorPosition(e) {
	var camp_map = document.getElementById("campMap");

	var x;
	var y;
	var pos = findPos(camp_map);

	if (e.pageX != undefined && e.pageY != undefined) {

	    x = e.pageX - pos.x;
	    y = e.pageY - pos.y;
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

    function unhexify(color) {
	// Converts a hex color to rgba tuple.
	var r = parseInt(color.slice(1,3),16);
	var g = parseInt(color.slice(3,5),16);
	var b = parseInt(color.slice(5,7),16);
        // Might notice that the alpha is fixed to half transparency.
        // That is because this function is for use in making the hover
        // indicators.
	return 'rgba(' +r+ ',' +g+ ',' +b+ ',0.5)';
    }

    function draw_map(camp_map) {
	// Declare that we're using a 2d canvas.
	var context = camp_map.getContext("2d");
        // resets the map
	context.clearRect(0, 0, camp_map.width, camp_map.height);
	context.beginPath();
        // Draw the map itself
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
            // Figure out which building is being hovered over
	    if (spot[0] > dimensions[0][0]
		&& spot[0] < dimensions[1][0] 
		&& spot[1] > dimensions[0][1] 
		&& spot[1] < dimensions[1][1]) {
               
		draw = true; // Yes, we drew something!
                // Only draw the name and indicator if you haven't already
		if (cur_build != name) {
		    context.font = "bold 12px sans-serif";
		    context.fillText(name, 25, 125);

                    // If the building has hover color information...
		    if (dimensions[3] != null) {
			context.fillStyle = unhexify(dimensions[3][1]);
			context.arc(dimensions[3][0][0],dimensions[3][0][1],
				    25,0,2*Math.PI,true);
			context.fill();
		    }
		    cur_build = name;
		}
	    }
	});
        // If we aren't over a building, then clear the map
	if (draw == false) {
	    draw_map(camp_map);
	    cur_build = null;
	    context.fillStyle = '#000000';
	}
    }

    function map_click_handler(e) {
	var spot = getCursorPosition(e);
	//alert('Clicked at ' + spot[0] + ',' + spot[1]);

	// Determine which building they clicked on
	// Buildings are [topLeftCorner, bottomRightCorner, redirectURL]
	$.each(buildings, function(name,dimensions) {
	    if (spot[0] > dimensions[0][0]
		&& spot[0] < dimensions[1][0] 
		&& spot[1] > dimensions[0][1] 
		&& spot[1] < dimensions[1][1]) {
		
		// change pages if possible
		if (dimensions[2]) {
		    window.location = dimensions[2];
		} else {
		    alert(name + " doesn't have a page yet!");
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

    make_map();
});
