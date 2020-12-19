$('select').dropdown();
$('.ui.dropdown').dropdown();

//Objects with respect to storing final output values for the report.
//metaDataObj and neuron -> Responsible for storing all the UI selections.
//results -> group related report data
//pvecResults -> pvec related report data
//morphoResults -> morpho related report data
var metaDataObj = {}, neuron = {}, results = [], pvecResults = [], morphoResults = [],
	selectedDownloadValue = "0", viewClick = true;

new ClipboardJS('.btn');

//Incase of switching between any DBs.
$('#db').click(function () {
	if ($(this).text() == "NeuMO") {
		$(this).text("nmdbDev");
	}
	else {
		$(this).text("NeuMO");
	}
});

//main point of control for hits button.
$('#hits').click(function () {
	getCount();
});

//main point of control for reset button.
$('#reset').click(function () {
	window.location.reload();
});

//not in use today, can be used if necessary.
$('#generateQuery').click(function () {
	var metaDataQuery = JSON.stringify(getMetaData());
	var db = $('#db').text();
	$('#query').text('"' + metaDataQuery.replace(/"/g, "\\\"") + '&dbValue=' + 'nmdbDev' + '"');
	$('#showQuery').modal('show');
});

$('#typeButton').click(function () {
	return false;
});

//View button responsible for viewing the report.
$('#view').click(function () {
	$("#view").html('Processing...');
	selectedDownloadValue = document.querySelector("#typeButton > div > div.text").innerText
	viewClick = true
	gethits();
	$('#viewTable').modal({
		centered: false
	}).modal('show');
	$('#groupTable').show();
	$('#viewTable').modal({
		centered: false
	}).modal('hide');
});

//Download table responsible for downloading the report;if we reach here through the view option.
$('.download-table').click(function () {
	$("#download").html('Processing...');
	selectedDownloadValue = document.querySelector("#typeButton > div > div.text").innerText
	viewClick = false
	gethits();
	return false;
});

//Convert viewable data to csv.
var tableToExcel = (function () {
	var uri = 'data:application/vnd.ms-excel;base64,'
		, template = '<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40"><head><!--[if gte mso 9]><xml><x:ExcelWorkbook><x:ExcelWorksheets><x:ExcelWorksheet><x:Name>{worksheet}</x:Name><x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions></x:ExcelWorksheet></x:ExcelWorksheets></x:ExcelWorkbook></xml><![endif]--></head><body><table>{table}</table></body></html>'
		, base64 = function (s) { return window.btoa(unescape(encodeURIComponent(s))) }
		, format = function (s, c) { return s.replace(/{(\w+)}/g, function (m, p) { return c[p]; }) }
	return function (table, name, filename) {
		if (!table.nodeType) table = document.getElementById(table)
		var ctx = { worksheet: name || 'Worksheet', table: table.innerHTML }

		if (navigator.msSaveBlob) {
			navigator.msSaveBlob(new Blob([uri + format(template, ctx)], {
				type: "application/csv;charset=utf-8;"
			}), filename);
		}
		else {
			document.getElementById("dlink").href = uri + base64(format(template, ctx));
			document.getElementById("dlink").download = filename;
			document.getElementById("dlink").click();
		}

	}
})()

//Constructions of metaDataObj from UI selections.
function getMetaData() {
	$('#type_of_data').prop('selectedIndex', 0)
	var metaDataObj = {}, neuron = {};
	$('select').each(function () {
		if (($('#' + this.id).dropdown('get value')).length > 0) {
			if (this.id != "type_of_data") {
				if (this.id === "upload_date" || this.id === "deposition_date") {
					var temp = [];
					$($('#' + this.id).dropdown('get value')).each(function () {
						temp.push(this + "T00:00:00Z");
					});
					neuron[this.id] = temp;
				}
				else {
					tempArr = []
					$('#' + this.id).find("option:selected").each(function (index, sel) {
                       tempArr.push($(sel).text());
                    });
					if (this.id === "Physical_Integrity") {
						neuron["physical_integrity"] = tempArr
					}
					else if (this.id === "reference_pmid") {
						neuron["pmid"] = tempArr
					}
					else if (this.id === "attributes"){
						neuron["morphological_attributes"] = tempArr
					}
					else{
						neuron[this.id] = tempArr;
					}
				}
			}
		}

	});
	metaDataObj["neuron"] = neuron;
	metaDataObj["ageWeightOperators"] = {};
	metaDataObj["ageWeightOperations"] = {};
	return metaDataObj;
}

//Gets the total count for the number of neurons that match the criteria selected from UI.
var getCount = function () {

	metaDataObj = getMetaData();

	$.ajax({
		url: 'http://cng.gmu.edu:8080/searchServiceReview/metadata/count',
		error: function () {
			$('#info').html('<p>An error has occurred<div class="scrolling content"></p>');
		},
		async: false,
		dataType: "json",
		contentType: 'application/json',
		data: JSON.stringify(metaDataObj),
		success: function (data) {
			$('#count').text(data + " neurons found.");
			$('#hitsResult').modal('show');
		},
		type: 'POST'
	});
}

//Actual retrieval of data from searchServiceReview endpoint.
var gethits = function () {

	metaDataObj = getMetaData();

	results = [];
	$('select').each(function () {
		if (($('#' + this.id).dropdown('get value')).length > 0) {
			if (this.id != "type_of_data") {
				if (this.id === "upload_date" || this.id === "deposition_date") {
					var temp = [];
					$($('#' + this.id).dropdown('get value')).each(function () {
						temp.push(this + "T00:00:00Z");
					});
					neuron[this.id] = temp;
				}
				else {
					tempArr = []
					$('#' + this.id).find("option:selected").each(function (index, sel) {
		               tempArr.push($(sel).text());
		            });
					if (this.id === "Physical_Integrity") {
						neuron["physical_integrity"] = tempArr
					}
					else if (this.id === "reference_pmid") {
						neuron["pmid"] = tempArr
					}
					else if (this.id === "attributes"){
						neuron["morphological_attributes"] = tempArr
					}
					else{
						neuron[this.id] = tempArr;
					}
				}
			}
		}
	});

	var date = new Date();
	var timestamp = date.getTime().toString();

	metaDataObj["neuron"] = neuron;
	metaDataObj["ageWeightOperators"] = {};
	metaDataObj["ageWeightOperations"] = {};
	metaDataObj["typeOfData"] = selectedDownloadValue;
	metaDataObj["fileName"] = timestamp;

	if (viewClick) {
		$.ajax({
			url: 'http://cng.gmu.edu:8080/searchServiceReview/metadata/neuronIds',
			error: function () {
				$('#info').html('<p>An error has occurred<div class="scrolling content"></p>');
			},
			async: false,
			dataType: "json",
			contentType: 'application/json',
			data: JSON.stringify(metaDataObj),
			success: function (data) {
				var i, j, temp, chunk = 50;
				for (i = 0, j = 50; i < j; i += chunk) {
					temp = data.slice(i, i + chunk);
					if (selectedDownloadValue == "Groups")
						getNeurons(stringifyIds(temp));
					else if (selectedDownloadValue == "Morphometrics")
						getMorphoForNeurons(stringifyIds(temp))
					else if (selectedDownloadValue == "Persistence Vectors")
						getPvecForNeurons(stringifyIds(temp))
				}
				if (selectedDownloadValue == "Groups") {
					var finalGroupsResult = groupBy(results, function (item) {
						return [item.archive, item.gender, item.age_scale, item.reference_pmid, item.reference_doi, item.age_classification, item.brain_region, item.cell_type, item.species, item.strain, item.scientific_name, item.stain, item.experiment_condition, item.protocol, item.slicing_direction, item.reconstruction_software, item.objective_type, item.original_format, item.magnification, item.upload_date, item.deposition_date, item.shrinkage_reported, item.shrinkage_corrected, item.reported_value, item.reported_xy, item.reported_z, item.corrected_value, item.corrected_xy, item.corrected_z, item.slicing_thickness, item.min_age, item.max_age, item.min_weight, item.max_weight, item.physical_Integrity];
					});

					var csv = createCSV(finalGroupsResult);

				}
				else if (selectedDownloadValue == "Morphometrics") {
					var finalMorphoResult = groupBy(morphoResults, function (item) {
						return [item.neuron_id, item.neuron_name, item.surface, item.volume, item.soma_Surface, item.n_stems, item.n_bifs, item.n_branch, item.width, item.height, item.depth, item.diameter, item.eucDistance, item.pathDistance, item.branch_Order, item.contraction, item.fragmentation, item.partition_asymmetry, item.pk_classic, item.bif_ampl_local, item.fractal_Dim, item.bif_ampl_remote, item.length];
					});

					var csv = createMorphoCSV(finalMorphoResult);

				}
				else if (selectedDownloadValue == "Persistence Vectors") {
					var finalPvecResult = groupBy(pvecResults, function (item) {
						return [item.neuron_id, item.scaling_factor, item.distance, item.coefficients];
					});

					var csv = createPvecCSV(finalPvecResult);
				}
				$("#view").html('View');
			},
			type: 'POST'
		});
	}

	else {
		
		//End-point for generating report - deployed in a docker container
		var promise = $.ajax({
			url: 'http://129.174.10.74/genRepNew/generateReport',
			dataType: "json",
			contentType: 'application/json',
			type: 'GET',
			timeout: 0,
			headers: {
				payload: JSON.stringify(metaDataObj)
			},
			error: function (xhr, status, errorThrown) {
				alert("Server down for maintenance. Please check after some time.")
				$("#download").html('Download');
				$("#view").html('View');
			}


		})

		//Retrieve the report based on the option selected - groups, morpho or pvec.
		promise.then(function (data) {
			if (selectedDownloadValue == "Groups")
				window.location = 'http://129.174.10.74/genRepNew/generateReport/download/groups_' + timestamp + '.csv'
			else if (selectedDownloadValue == "Morphometrics")
				window.location = 'http://129.174.10.74/genRepNew/generateReport/download/morpho_' + timestamp + '.csv'
			else if (selectedDownloadValue == "Persistence Vectors")
				window.location = 'http://129.174.10.74/genRepNew/generateReport/download/pvec_' + timestamp + '.csv'
			else if (selectedDownloadValue == "All")
				window.location = 'http://129.174.10.74/genRepNew/generateReport/download/all_' + timestamp + '.zip'

			$("#download").html('Download');

		})

	}

	viewClick = false
}

//Create csv structure to be displayed in the view option.
function createCSV(data) {

	keys = ["archive", "species", "strain", "min_age", "max_age", "age_scale", "min_weight", "max_weight", "age_classification", "gender", "brain_region", "cell_type", "original_format", "protocol", "slicing_thickness", "slicing_direction", "stain", "magnification", "objective_type", "reconstruction_software", "note", "experiment_condition", "deposition_date", "upload_date", "reference_pmid", "reference_doi", "shrinkage_reported", "shrinkage_corrected", "reported_value", "reported_xy", "reported_z", "corrected_value", "corrected_xy", "corrected_z", "physical_Integrity"];


	var result = '<table class="ui definition table" id="groupTable" style="display: none"><thead><tr>';

	result += "<th>Title</th>";
	for (var i = 0; i < data.length; i++) {
		result = result + "<th>" + parseInt(i + 1) + "</th>";
	}
	result += "</tr></thead><tbody><tr>";


	result += "<td>numOfNeurons</td>";
	for (var i = 0; i < data.length; i++) {
		result = result + "<td>" + data[i].length + "</td>";
	}
	result += "</tr>";


	for (var j = 0; j < keys.length; j++) {
		result += "<tr>";
		result = result + "<td>" + keys[j]; + "</td>";
		for (var i = 0; i < data.length; i++) {
			result = result + "<td>" + data[i][0][keys[j]] + "</td>";
		}
		result += "</tr>";
	}

	document.getElementById('tablePrint').innerHTML = result;
}

//Create the pvec structure to be displayed in the html table.
function createPvecCSV(data) {

	keys = ["neuron_id", "scaling_factor", "distance", "coeff00", "coeff01", "coeff02", "coeff03", "coeff04", "coeff05", "coeff06", "coeff07", "coeff08", "coeff09", "coeff10", "coeff11", "coeff12", "coeff13", "coeff14", "coeff15", "coeff16", "coeff17", "coeff18", "coeff19", "coeff20", "coeff21", "coeff22", "coeff23", "coeff24", "coeff25", "coeff26", "coeff27", "coeff28", "coeff29", "coeff30", "coeff31", "coeff32", "coeff33", "coeff34", "coeff35", "coeff36", "coeff37", "coeff38", "coeff39", "coeff40", "coeff41", "coeff42", "coeff43", "coeff44", "coeff45", "coeff46", "coeff47", "coeff48", "coeff49", "coeff50", "coeff51", "coeff52", "coeff53", "coeff54", "coeff55", "coeff56", "coeff57", "coeff58", "coeff59", "coeff60", "coeff61", "coeff62", "coeff63", "coeff64", "coeff65", "coeff66", "coeff67", "coeff68", "coeff69", "coeff70", "coeff71", "coeff72", "coeff73", "coeff74", "coeff75", "coeff76", "coeff77", "coeff78", "coeff79", "coeff80", "coeff81", "coeff82", "coeff83", "coeff84", "coeff85", "coeff86", "coeff87", "coeff88", "coeff89", "coeff90", "coeff91", "coeff92", "coeff93", "coeff94", "coeff95", "coeff96", "coeff97", "coeff98", "coeff99"];

	var result = '<table class="ui definition table" id="groupTable" style="display: none"><thead><tr>';

	for (var i = 0; i < keys.length; i++) {
		result = result + "<th>" + keys[i] + "</th>";
	}
	result += "</tr></thead><tbody><tr>";

	for (var j = 0; j < data.length; j++) {
		result += "<tr>";
		for (var i = 0; i < keys.length; i++) {
			keyVal = keys[i];
			if (keyVal.indexOf("coeff") > -1) {
				temp = parseInt(keyVal[keyVal.length - 1]);
				keyVal = "coefficients"
				result = result + "<td>" + data[j][0][keyVal][temp] + "</td>";
			}
			else {
				result = result + "<td>" + data[j][0][keyVal] + "</td>";
			}
		}
		result += "</tr>";
	}

	document.getElementById('tablePrint').innerHTML = result;
}

//Create the morpho structure to be displayed in the html table.
function createMorphoCSV(data) {

	keys = ["neuron_id", "neuron_name", "surface", "volume", "soma_Surface", "n_stems", "n_bifs", "n_branch",
		"width", "height", "depth", "diameter", "eucDistance", "pathDistance", "branch_Order", "contraction", "fragmentation", "partition_asymmetry",
		"pk_classic", "bif_ampl_local", "fractal_Dim", "bif_ampl_remote", "length"];

	var result = '<table class="ui definition table" id="groupTable" style="display: none"><thead><tr>';

	result += "<th>Title</th>";
	for (var i = 0; i < data.length; i++) {
		result = result + "<th>" + parseInt(i + 1) + "</th>";
	}
	result += "</tr></thead><tbody><tr>";

	console.log(data.length);
	for (var j = 0; j < keys.length; j++) {
		result += "<tr>";
		result = result + "<td>" + keys[j]; + "</td>";
		for (var i = 0; i < data.length; i++) {
			result = result + "<td>" + data[i][0][keys[j]] + "</td>";
		}
		result += "</tr>";
	}

	document.getElementById('tablePrint').innerHTML = result;
}

//Group by neurons for displaying neurons in view option.
function groupBy(array, f) {
	var groups = {};
	array.forEach(function (o) {
		var group = JSON.stringify(f(o));
		groups[group] = groups[group] || [];
		groups[group].push(o);
	});
	return Object.keys(groups).map(function (group) {
		return groups[group];
	})
}


//create comma separated values for the neuron ids retrieved.
function stringifyIds(data) {
	var ids = "";
	$(data).each(function () {
		ids = ids + this + ",";
	});
	return (ids.slice(0, -1));
}

//Get neurons for displaying in view option.
function getNeurons(ids) {
	$.ajax({
		url: 'http://neuromorpho.org/api/neuron/select?q=neuron_id:' + ids + '&page=0&size=500',
		async: false,
		error: function () {
			$('#info').html('<p>An error has occurred</p>');
		},
		success: function (data) {
			$(data._embedded.neuronResources).each(function () {
				results.push(this);
			});
		},
		type: 'GET'
	});
}

//Get pvec data for displaying in view option.
function getPvecForNeurons(ids) {
	$.ajax({
		url: 'http://cng.gmu.edu:8080/api/pvec/select?q=neuron_id:' + ids + '&page=0&size=500',
		async: false,
		error: function () {
			$('#info').html('<p>An error has occurred</p>');
		},
		success: function (data) {
			$(data._embedded.pvecs).each(function () {
				pvecResults.push(this);
			});
		},
		type: 'GET'
	});
}

//Get morpho data for displaying in view option.
function getMorphoForNeurons(ids) {
	$.ajax({
		url: 'http://cng.gmu.edu:8080/api/morphometry/select?q=Neuron_id:' + ids + '&page=0&size=500',
		async: false,
		error: function () {
			$('#info').html('<p>An error has occurred</p>');
		},
		success: function (data) {
			$(data._embedded.measurements).each(function () {
				morphoResults.push(this);
			});
		},
		type: 'GET'
	});
}

var fieldvals = {};
function generatefieldvalues() {
	$.ajax({
		url: 'http://cng-nmo-main.orc.gmu.edu/metaproxy/',
		error: function () {
			$('#info').html('<p>An error has occurred</p>');
		},
		success: function (data) {
			fieldvals = JSON.parse(data);
			var datakeys = Object.keys(fieldvals);			
			for (var i = 0; i < datakeys.length; i++) {
				var doc = document.getElementById(datakeys[i]);
				arr = fieldvals[datakeys[i]].fields
				for (var j = 0; j < arr.length; j++) {
					var option = document.createElement("option");
					option.text = arr[j];
					option.value = arr[j];
					doc.appendChild(option);
				}
			}
		},
		type: 'GET'
	});
}

generatefieldvalues();

//Retrieve additional field values other than brain_region and cell types.
/* function retrieveFieldValues(field) {
	$.ajax({
		url: 'http://neuromorpho.org/api/neuron/fields/' + field,
		error: function () {
			$('#info').html('<p>An error has occurred</p>');
		},
		success: function (data) {
			var arr = data.fields;
			var doc = document.getElementById(field);
			for (var i = 0; i < arr.length; i++) {
				var option = document.createElement("option");
				option.text = arr[i];
				option.value = arr[i];
				doc.appendChild(option);
			}
		},
		type: 'GET'
	});
} 


$(".retrieve-fields").each(function () {
	retrieveFieldValues(this.firstChild.id);
});*/
document.getElementById("loader").style.display = "none";

//Retrieve additional field values for brain_region and cell types.
/* function retrieveBrainRegionCellTypeValues(field) {
	$.ajax({
		url: "http://neuromorpho.org/api/neuron/fields/" + field,
		error: function () {
			$('#info').html('<p>An error has occurred</p>');
		},
		success: function (data) {
			var arr = data.fields;
			var doc = document.getElementById(field);

			for (var i = 0; i < arr.length; i++) {
				var option = document.createElement("option");
				option.text = arr[i];
				option.value = arr[i];
				doc.appendChild(option);
			}
		},
		type: 'GET'
	});
}

retrieveBrainRegionCellTypeValues("brain_region_1");
retrieveBrainRegionCellTypeValues("cell_type_1");

retrieveBrainRegionCellTypeValues("brain_region_2");
retrieveBrainRegionCellTypeValues("cell_type_2");

retrieveBrainRegionCellTypeValues("brain_region_3");
retrieveBrainRegionCellTypeValues("cell_type_3"); */

