$(function () {
    // This function is a callback, called when the DOM is loaded

    // Buildings are defined as rectangles. 
    // Defined as xy pairs, [Top Left, Bottom Right, redirectURL, HOVER]
    // HOVER gives the top left corner of the hover image, and its URL.
    var buildings = {
	'Olin':[[10,75],[22,105],null,null],
	'Beckman':[[23,84],[44,100],null,null],
	'Parsons':[[48,45],[90,75],null,null],
	'Sprague':[[45,80],[65,100],null,null],
	'Gallileo':[[75,80],[95,100],null,null],
	'Keck':[[50,115],[92,145],null,null],
	'TG':[[135,55],[170,75],null,null],
	'Kingston':[[130,100],[170,125],null,null],
	'Platt':[[210,42],[255,75], null,null],
	'Hoch':[[210,100],[255,135],null,null],
	'South':[[283,45],[320,75], null,
		 [[272,0],MEDIA_URL + 'img/south.png']],
	'West': [[283,105],[320,132], null,
		 [[270,54],MEDIA_URL + 'img/west.png']],
	'North':[[335,45],[370,75], null,
		 [[323,0],MEDIA_URL + 'img/north.png']],
	'East': [[335,105],[370,132], null,
		 [[323,57],MEDIA_URL + 'img/east.png']],
	'LAC': [[380,45],[425,75], null,null],
	'Sontag': [[450,50],[490,85], null,
		   [[441,5],MEDIA_URL + 'img/sontag.png']],
	'Atwood': [[450,110],[488,148], null,
		   [[438,65],MEDIA_URL + 'img/atwood.png']],
	'Linde':[[538,70],[567,107], null,
		 [[525,23],MEDIA_URL + 'img/linde.png']],
	'Case': [[508,115],[547,155], null,
		 [[494,68],MEDIA_URL + 'img/case.png']],
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
	var context = camp_map.getContext("2d");
        // resets the map
	context.width = context.width; 
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
	    if (spot[0] > dimensions[0][0]
		&& spot[0] < dimensions[1][0] 
		&& spot[1] > dimensions[0][1] 
		&& spot[1] < dimensions[1][1]) {

		context.font = "bold 12px sans-serif";
		context.fillText(name, 25, 125);
		draw = true;
		if (dimensions[3] != null) {
		    var img = new Image();
		    img.src =  dimensions[3][1]
		    img.onload = function() {
			context.drawImage(img,
					  dimensions[3][0][0],
					  dimensions[3][0][1]);
		    };
		}
	    }
	});
	if (draw == false) {
	    draw_map(camp_map);
	}
    }

    function map_click_handler(e) {
	var spot = getCursorPosition(e);
	alert('Clicked at ' + spot[0] + ',' + spot[1]);

	// Determine which building they clicked on
	// Buildings are [topLeftCorner, bottomRightCorner, redirectURL]
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
