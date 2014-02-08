app

.constant('ratingConfig', {
  max: 5,
})

.directive('rating', ['ratingConfig', function(ratingConfig) {
    return {
        restrict: 'EA',
        replace: true,
        scope: {
            value: '=',
        },
        template: '<span ng-mouseleave="reset()"><i ng-repeat="number in range" ng-mouseenter="enter(number)" ng-click="assign(number)" ng-class="{\'icon-star\': number <= val, \'icon-star-empty\': number > val}"></i></span>',
        link: function(scope, element, attrs) {
            var maxRange = angular.isDefined(attrs.max) ? scope.$eval(attrs.max) : ratingConfig.max;

            scope.range = [];
            for(var i = 1; i <= maxRange; i++ ) {
                scope.range.push(i);
            }

            scope.$watch('value', function(value) {
                scope.val = value;
            });

            scope.assign = function(value) {
                scope.value = value;
            }

            scope.enter = function(value) {
                scope.val = value;
            }

            scope.reset = function() {
                scope.val = angular.copy(scope.value);
            }
            scope.reset();

        }
    };
}]);