$(function () {
    // This function is a callback, called when the DOM is loaded

    // Buildings are defined as rectangles. 
    // Defined as xy pairs, [Top Left, Bottom Right]
    var buildings = {
	'Olin':[[15,90],[30,125],null,null],
	'Beckman':[[35,100],[50,115],null,null],
	'Parsons':[[58,60],[100,85],null,null],
	'Sprague':[[55,100],[75,120],null,null],
	'Gallileo':[[85,100],[105,115],null,null],
	'Keck':[[60,130],[105,155],null,null],
	'TG':[[140,70],[180,90],null,null],
	'Kingston':[[140,120],[180,140],null,null],
	'Platt':[[215,55],[270,90], null,null],
	'Hoch':[[215,115],[270,150],null,null],
	'South':[[290,60],[325,90], south_url,
		 [[272,0],MEDIA_URL + 'img/south.png']],
	'West': [[290,115],[325,150], west_url,
		 [[270,54],MEDIA_URL + 'img/west.png']],
	'North':[[345,60],[380,90], north_url,
		 [[323,0],MEDIA_URL + 'img/north.png']],
	'East': [[345,115],[380,150], east_url,
		 [[323,57],MEDIA_URL + 'img/east.png']],
	'LAC': [[390,60],[435,90], null,null],
	'Sontag': [[460,65],[495,95], sontag_url,
		   [[441,5],MEDIA_URL + 'img/sontag.png']],
	'Atwood': [[460,125],[500,160], atwood_url,
		   [[438,65],MEDIA_URL + 'img/atwood.png']],
	'Linde':[[545,85],[580,125], linde_url,
		 [[525,23],MEDIA_URL + 'img/linde.png']],
	'Case': [[515,130],[555,170], case_url,
		 [[494,68],MEDIA_URL + 'img/case.png']],
    };
    
  
    function array_index_of(ar, x) {
        // (IE doesn't have Array.indexOf)
        for (var i=0; i < ar.length; i++) {
            if (ar[i] == x) {
                return i;
            }
        }
        return -1;
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
//	alert('Clicked at ' + spot[0] + ',' + spot[1]);

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

    make_map();
});
