var rating = (function () {
    
    var rating = {
        init: function(el) {
            el.addEventListener("change", function(e) { ratingSwap(e); }, false);
        },
    };
    
    /*** PRIVATE FUNCTIONS ***/
    function ratingSwap(e) {
        e.target.className = "active rating" + e.target.value;
    }

    return rating;
	
}());

new rating.init(document.getElementById("rating-1234"));