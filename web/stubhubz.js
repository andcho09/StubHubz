function renderPriceHistory(eventId, chartTitle){
	$.ajax({
		url: '/price_history/' + eventId + '.js',
		dataType: 'json'
	}).done(function(response){
		config.data.datasets = response;
		config.options.title.text = chartTitle;
		for(var i = 0; i < response.length; i++){
			var dataset = response[i];
			dataset.label = dataset.zone;
			dataset.borderColor = window.chartColors[i];
			dataset.backgroundColor = window.chartColors[i];
			dataset.fill = false;
			dataset.data = downsample(dataset.data, 300);
		}
		if (window.myLine == undefined){
			var ctx = document.getElementById('canvas').getContext('2d');
			window.myLine = new Chart(ctx, config);
		}else{
			window.myLine.update();
		}
	});
}

function handleEventResponse(response){
	eventArray = [];
	response.events.forEach(function(event) {
		if (event.eventStatus == "" && event.scrapeStatus == ""){
			return;//skip this bad event
		}
		var venue = event.venueName;
		if (event.venueCity != ''){
			if (venue == ''){
				venue = event.venueCity;
			}else{
				venue += ', ' + event.venueCity
			}
		}
		eventArray[eventArray.length] = [
			event.id,
			event.primaryPerformer,
			venue,
			formatIso8601Date(event.dateTime, false),
			formatScrapeStatus(event.scrapeStatus),
			formatIso8601Date(event.lastScrapedDateTime, true)
		];
	});
	$.fn.dataTable.moment('DD MMM YYYY HH:mmZZ', 'en');
	var eventsDataTable = $('#eventsTable').DataTable( {
		data: eventArray,
		columns: [
			{title: 'ID', visible: false},
			{title: 'Performer'},
			{title: 'Venue'},
			{title: 'Event Date'},
			{title: 'Status'},
			{title: 'Last Update Time'}
		],
		'paging': false,
		'searching': false
	});
	eventsDataTable.order([4, 'desc'], [3, 'asc']).draw();
	$('#eventsTable tbody').on('click', 'tr', function () {
		var data = eventsDataTable.row(this).data();
		renderPriceHistory(data[0], formatChartTitle(data[1], data[2]));
	});
}

function formatChartTitle(primaryPerformer, venue){
	if (primaryPerformer){
		return venue ? primaryPerformer + " (" + venue + ")" : primaryPerformer;
	}else{
		if (venue){
			return venue;
		}
	}
	return "Unknown Event";
}

// Formats an ISO8601 date string and either convert the time to local or preserve it
function formatIso8601Date(dateString, convertToLocal){
	var parsedDate = convertToLocal ? moment(dateString) : moment.parseZone(dateString);
	if(!parsedDate.isValid()){
		return dateString;
	}
	return convertToLocal ? parsedDate.format("DD MMM YYYY HH:mm") : parsedDate.format("DD MMM YYYY HH:mmZZ");
}

function formatScrapeStatus(scrapeStatus){
	if("Active" == scrapeStatus){
		return "Tracking"
	}else if("Inactive" == scrapeStatus){
		return "Not Tracking"
	}
	return "Unknown";
}

function getTooltipFooter(tooltipItems, data) {
	var footer = [];
	var point = data.datasets[tooltipItems[0].datasetIndex].data[tooltipItems[0].index];
	var isAccurate = true;
	if (point.hasOwnProperty('avgPriceAccurate'))
		isAccurate = point['avgPriceAccurate']
	if (point.hasOwnProperty('avgPrice')){
		label = isAccurate ? 'Average Price: ' : 'Approx Average Price: ';
		footer.push(label + point['avgPrice'])
	}
	if (point.hasOwnProperty('totalTickets')){
		footer.push('Total Tickets: ' + point['totalTickets'])
	}
	if (point.hasOwnProperty('totalListings')){
		footer.push('Total Listings: ' + point['totalListings'])
	}
	return footer;
}