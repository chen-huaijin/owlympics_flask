$(document).ready(function() {
	
	$("#navigate a").click(function() {

		// Get the category of this image
		var category = $(this).attr("name");
		/*
		switch (category)
		{
		case 'owl':
			var total = $("#owl_box img").length;
			var imgwidth = $("#owl_box #img1").width();
			var box_left = $("#owl_box").css("left");
			break;
		case 'glasses':
			var total = $("#glasses_box img").length;
			var imgwidth = $("#glasses_box #img1").width();
			var box_left = $("#glasses_box").css("left");
			break;
		}
		*/
		var total = $("#"+category+"_box img").length;
		var imgwidth = $("#"+category+"_box #img1").width();
		var box_left = $("#"+category+"_box").css("left");

		if (box_left == 'auto') {
			box_left = 0;
		} else {
			box_left = parseInt(box_left.replace("px", ""));
		}

		var move, imgnumber;
		var el_id = $(this).attr("id");
		if (el_id == 'linkprev') {
			if ((box_left - imgwidth) == -(imgwidth)) { // If first image
				//move = -(imgwidth * (total - 1)); // Circular move
				move = 0;
			} else {
				move = box_left + imgwidth;
			}
			imgnumber = -(box_left / imgwidth);
			if (imgnumber == 0) {
				imgnumber = total;
			}
		} else if (el_id == 'linknext') {
			if (-(box_left) == (imgwidth * (total - 1))) { // If last image
				//move = 0; // Circular move
				move = -(imgwidth * (total - 1));
			} else {
				move = box_left - imgwidth;
			}
			imgnumber = Math.abs((box_left / imgwidth)) + 2;
			if (imgnumber == (total + 1)) {
				imgnumber = 1;
			}
		} else if (el_id == 'linkfirst') {
			move = 0;
			imgnumber = 1;
		} else if (el_id == 'linklast') {
			move = -(imgwidth * (total - 1));
			imgnumber = total;
		}
		
		// Move to the selected image and set the image id
		/*
		switch (category)
		{
		case 'owl':
			$("#owl_box").animate({left: move+'px'}, 500);
			break;
		case 'glasses':
			$("#glasses_box").animate({left: move+'px'}, 500);
			break;
		}
		*/
		set_img_num(category+"_img_num", imgnumber);
		var imgwidth_big = $("#"+category+"_box_big #img1").width();
		var move_big = move * (imgwidth_big / imgwidth);
		$("#"+category+"_box").animate({left: move+'px'}, 500);
		$("#"+category+"_box_big").animate({left: move_big+'px'}, 500);
		//$("#"+category+"_img_num").value = imgnumber;
		
		return false;
	});
});
