// Heavily modified version of Chart JS plugin https://github.com/AlbinoDrought/chartjs-plugin-downsample which in turn
// is based on https://github.com/sveinn-steinarsson/flot-downsample. This has been modified to remove Chart JS feature
// so the chart can just call the downsample method directly as handling updates was getting tricky.
var floor = Math.floor,
	abs = Math.abs;

function downsample(data, threshold) {
	// this function is from flot-downsample (MIT), with modifications

	var dataLength = data.length;
	if (threshold >= dataLength || threshold <= 0) {
		return data; // nothing to do
	}

	var sampled = [],
		sampledIndex = 0;

	// bucket size, leave room for start and end data points
	var every = (dataLength - 2) / (threshold - 2);

	var a = 0,  // initially a is the first point in the triangle
		maxAreaPoint,
		maxArea,
		area,
		nextA;

	// always add the first point
	sampled[sampledIndex++] = data[a];

	for (var i = 0; i < threshold - 2; i++) {
		// Calculate point average for next bucket (containing c)
		var avgX = 0,
			avgY = 0,
			avgRangeStart = floor(( i + 1 ) * every) + 1,
			avgRangeEnd = floor(( i + 2 ) * every) + 1;
		avgRangeEnd = avgRangeEnd < dataLength ? avgRangeEnd : dataLength;

		var avgRangeLength = avgRangeEnd - avgRangeStart;

		for (; avgRangeStart < avgRangeEnd; avgRangeStart++) {
			avgX += new Date(data[avgRangeStart].x).getTime(); // original code doesn't handle ISO8601 date strings at all
			avgY += data[avgRangeStart].y * 1;
		}
		avgX /= avgRangeLength;
		avgY /= avgRangeLength;

		// Get the range for this bucket
		var rangeOffs = floor((i + 0) * every) + 1,
			rangeTo = floor((i + 1) * every) + 1;

		// Point a
		var pointAX = new Date(data[a].x).getTime(), // original code doesn't handle ISO8601 date strings at all
			pointAY = data[a].y * 1;

		maxArea = area = -1;

		for (; rangeOffs < rangeTo; rangeOffs++) {
			// Calculate triangle area over three buckets
			area = abs(( pointAX - avgX ) * ( data[rangeOffs].y - pointAY ) -
					( pointAX - (new Date(data[rangeOffs].x).getTime()) ) * ( avgY - pointAY ) // handle ISO8601 string
				) * 0.5;
			if (area > maxArea) {
				maxArea = area;
				maxAreaPoint = data[rangeOffs];
				nextA = rangeOffs; // Next a is this b
			}
		}

		sampled[sampledIndex++] = maxAreaPoint; // Pick this point from the bucket
		a = nextA; // This a is the next a (chosen b)
	}

	sampled[sampledIndex] = data[dataLength - 1]; // Always add last

	return sampled;
}
