%#template to generate a HTML table from a list of tuples (or list of lists, or tuple of tuples or ...)
<html>
<head>

<!-- JQUERY -->
<script type="text/javascript" src="https://ajax.googleapis.com/ajax/libs/jquery/1.6.2/jquery.js"></script> 

<!-- JQUERY UI -->
<link href="http://ajax.googleapis.com/ajax/libs/jqueryui/1.8/themes/base/jquery-ui.css" rel="stylesheet" type="text/css"/>
<script src="http://ajax.googleapis.com/ajax/libs/jqueryui/1.8/jquery-ui.js"></script>

<!-- JQUERY TEMPLATES -->
<script src="http://ajax.microsoft.com/ajax/jquery.templates/beta1/jquery.tmpl.js"></script>
  

<!-- JQUERY FLOT -->
<script type="text/javascript" src="/static/jquery.flot.js"></script>
<script type="text/javascript" src="/static/jquery.flot.selection.js"></script>

<!-- TEMPLATES -->
<script id="legendEntryTemplate" type="text/x-jquery-tmpl">
    <input type="checkbox" id="legend-label-${index}" checked/>
    <label for="legend-label-${index}" id="${label}">
        <div>
            <div class="legend-color" style="background-color:${color};"></div>
            <div class="legend-text" style="float:left;">${label}</div>
        </div>
    </label>
</script>

<script id="tooltipTemplate" type="text/x-jquery-tmpl">
    <div id="tooltip">
        <div id="tooltip-label">${label}</div>: ${value}
    </div>
</script>

<!-- LOGIC -->
<script type="text/javascript">
    var events = {{json_events}};
    
    /*var showTooltip = function(x, y, label, value) {
        $('<div id="tooltip">' + contents + '</div>').css( {
            position: 'absolute',
            display: 'none',
            top: y + 5,
            left: x + 5,
            border: '1px solid #fdd',
            padding: '2px',
            'background-color': '#fee',
            opacity: 0.80,
            "text-overflow": "ellipsis",
            overflow: "hidden",
            "white-space": "nowrap",
            "max-width": "100px",
        }).appendTo("body").fadeIn(200);
    }*/
    var showTooltip = function(x, y, label, value) {
        $("#tooltipTemplate").tmpl({label: label, value: value}).css({
            top: y + 5,
            left: x + 5,
        }).appendTo("body").fadeIn(200);
    }

    for(var i = 0; i < events.length; i++) {
        events[i].color = i;
    }

    $(document).ready(function() {
        var placeholder = $("#placeholder");        
        var options = {
                xaxis: { 
                    mode: "time" ,
                    minTickSize: [15, "day"],
                    autoscaleMargin: 0.05,
                },
                yaxis: {
                },
                series: {
                    lines: { show: true },
                    points: { show: true }
                },
                selection: { 
                    mode: "x"
                },
                grid: {
                    hoverable: true,
                    clickable: true,  
                },
                legend: {
                    show: false,
                }
        };

        var plot = $.plot(
            placeholder, 
            events, 
            options);

        // Save the original zoom
        var zoomed = plot.getAxes();
        
        placeholder.bind("plotselected", function (event, ranges) {
            plot = $.plot(
                        placeholder, events,
                        $.extend(
                            true, 
                            {},
                            options,
                            {
                              xaxis: { min: ranges.xaxis.from, max: ranges.xaxis.to }
                            }
                        )
                    );
        });
 
        $("#clearSelection").click(function () {
            plot.setSelection({xaxis: {from: zoomed.xaxis.min, to: zoomed.xaxis.max }});
        });

        var previousPoint = null;
        $("#placeholder").bind("plothover", function (event, pos, item) {
            if (item) {
                if (previousPoint != item.dataIndex) {
                    previousPoint = item.dataIndex;
                    
                    $("#tooltip").remove();
                    var label = item.series.label;
                    var count = item.datapoint[1];

                    showTooltip(item.pageX, item.pageY, label, count);
                }
            }
            else {
                $("#tooltip").remove();
                previousPoint = null;            
            }
        });

        var data = plot.getData();
        var legend = $("#legend");
        console.log(data);

        for(var i = 0; i < data.length; i++) {
            var label = data[i].label;
            var color = data[i].color;
            $("#legendEntryTemplate").tmpl({index: i, label: label, color: color}).appendTo(legend);
            /*legend.append('<input type="checkbox" id="legend-label-'+i+'" checked/>'
            +'<label for="legend-label-'+i+'" id="'+label+'">'
                + '<div>'
                    + '<div class="legend-color" style="background-color:'+color+';"></div>'
                    + '<div class="legend-text" style="float:left;">' + label + '</div>'
                + '</div>'
            + '</label>');*/
        }

        $("#legend").buttonset();
        $("#legend").click(function() {
            var newData = [];
            $('#legend').find('label.ui-state-active').each(function() {
                label = $(this).attr("id");
                
                for(var i = 0; i < events.length; i++) {
                    if (events[i].label.trim() === label) {
                        newData.push(events[i]);
                    }
                }
            }); 

            plot.setData(newData);
            plot.draw();
        });
    });
</script>
<style>
body {
    width: 90%;
    margin: 0px auto;
}
.event-table {
    width: 100%;
    margin-top: 30px;
    display: table;
    cellspacing: 0;
    border-collapse: collapse;
    border: 1px solid gainsboro;
}
.table-head {
    background-color: transparent;
    display: table-row;
    border: 0;
    margin: 0;
    padding: 0;
}
.table-head-cell {
    padding: 10px 15px;
    color: white;
    text-shadow: 0px 1px 1px #555;
    font-weight: bold;
    border-width: 0px 0px;
    border-color: #1E304D;
    border-style: solid;
    text-align: right;
    background: -webkit-gradient(linear, left top, left bottom, from(#5D80AA), to(#416491));
    background: -moz-linear-gradient(top, #5D80AA, #416491);
    filter: progid:DXImageTransform.Microsoft.gradient(startColorstr="#5D80AA", endColorstr="#416491");
    box-shadow: 0 1px 0 rgba(255, 255, 255, 0.4) inset;
    -moz-box-shadow: 0 1px 0 rgba(255, 255, 255, 0.4) inset;
    -webkit-box-shadow: 0 1px 0 rgba(255, 255, 255, 0.4) inset;
    -khtml-box-shadow: 0 1px 0 rgba(255, 255, 255, 0.4) inset;
    -o-box-shadow: 0 1px 0 rgba(255, 255, 255, 0.4) inset;
}
.event-name-cell {
    padding: 5px 15px;
    cursor: pointer;
    border-bottom: 1px solid gainsboro;
    border-right: 1px solid gainsboro;
    background: -webkit-gradient(linear, left top, left bottom, from(#E7E7E7), to(#EBEBEB));   
    background: -moz-linear-gradient(top, #E7E7E7, #EBEBEB);   
    filter: progid:DXImageTransform.Microsoft.gradient(startColorstr="#E7E7E7", endColorstr="#EBEBEB");
    background-repeat: repeat-y;
    font-family: 'lucida grande', arial, tahoma, verdana, sans-serif;
    font-size: 12px;
    font-style: normal;
    font-variant: normal;
    font-weight: normal;
}
.event-table-cell {
    padding: 5px 15px;
    text-align: right;
    background-color: white;
    border-bottom: 1px solid gainsboro;
    border-right: 1px solid gainsboro;
}
.graph {
    margin-top: 30px;
}
.left {
    float: left;
}
.right {
    float: right;
}
.center {
    text-align: center;
}
.clear {
    clear: both;
}
.uppercase {
    text-transform:uppercase;
}
a, a:visited {
    text-decoration: none;
    outline: 0;
}
a:hover {
    text-decoration: underline;
}
.event-name-cell a {
    color: #416590;
}
.graph {
    width: 95%;
    height: 400px;
    margin: 0px auto;
    margin-top: 10px;
}

#graph-and-legend {
    border: 1px solid #565656;
    margin-top: 10px;
}

#legend {
    width: 90%;
    margin: 0px auto;
    margin-top: 10px;
    margin-bottom: 10px;
    border: 1px solid black;
    -moz-border-radius: 5px;
    -webkit-border-radius: 5px;
    -khtml-border-radius: 5px;
    border-radius: 5px;
}

.legend-text {
    text-overflow: ellipsis;
    overflow: hidden !important;
    white-space: nowrap !important;
    width: 100%;
    margin-left: 2px;
    margin-top: 5px;
    font-size: 12px;
    display: block;
}

.ui-button {
    width: 23%;
    margin: 5px 5px 5px 5px !important;
    border: 0px;
    height: 30px;
}

.ui-state-default {
    background: white !important;
    color: #DADADA !important;
}
.ui-state-active {
    background: white !important;
    color: black !important;
}

label.ui-widget[aria-pressed=false] .legend-color {
    background-color: #DADADA !important;
}

.legend-color {
    display: block;
    width: 100%;
    height: 5px;
}

#tooltip {
    position: absolute;
    display: none;
    border: 1px solid #fdd;
    padding: 2px;
    background-color: #fee;
    opacity: 0.8;
}

#tooltip #tooltip-label {
    text-overflow: ellipsis !important;
    overflow: hidden !important;
    white-space: nowrap !important;
    max-width: 150px !important;
    float: left;
}

.gray-gradient-box {
    border: 1px solid #CFCFCF;
    background: #F2F2F2;
    filter: progid:DXImageTransform.Microsoft.gradient(startColorstr='white',endColorstr='#E4E4E4');
    background: -webkit-gradient(linear,left top,left bottom,from(white),to(#E4E4E4));
    background: -moz-linear-gradient(top,white,#E4E4E4);
}
.big-title {
    color: #4E74A1;
    font-size: 16pt;
    font-weight: bold;
    line-height: 18px;
    margin: 5px;
}
.mini-title {
    color: #4E74A1;
    font-size: 14pt;
    margin-left: 20px;
}
div.mini-title sup {
   font-size: 8pt;
}
.arrows {
    font-size: 8pt;
}
</style>
</head>

<body>
<div id="header" class="gray-gradient-box">
    <div id="app-title" class="big-title uppercase">
        {{application_name}}
    </div>
%if event_name:
    <div id="event-title" class="mini-title">
        <span class="arrows">&gt;&gt;</span> 
        {{ event_name }} 
        <sup>[<a href="{{application_name}}">clear</a>]</sup>
    </div>
%if property_name:
    <div id="property-title" class="mini-title">
        <span class="arrows">&gt;&gt;</span> 
        {{ property_name }} 
        <sup>[<a href="{{application_name}}?event_name={{event_name}}">clear</a>]</sup>
    </div>
%end
%end
</div>
<div id="graph-and-legend">
    <div id="placeholder" class="graph"></div> 
    <div id="legend"></div>
</div>
<input id="clearSelection" type="button" value="Default Zoom" /> 

%if event_name:
<table class="event-table">
<tr class="table-head">
    <th class="table-head-cell center">Property Name</th>
    <th class="table-head-cell center">Property Count</th>
</tr>
%for property in properties:
  <tr class="event-table-row">
    <td class="event-name-cell"><a href='{{application_name}}?event_name={{event_name}}&property={{property["name"]}}'>{{property["name"]}}</a></td>
    <td class="event-table-cell">{{property["count"]}}</td>
  </tr>
%end
</table>
%end

<table class="event-table">
<tr class="table-head">
    <th class="table-head-cell center">Event Name</th>
    <th class="table-head-cell center">Event Count</th>
</tr>
%for event in events:
  <tr class="event-table-row">
    <td class="event-name-cell"><a href='{{application_name}}?event_name={{event["name"]}}'>{{event["name"]}}</a></td>
    <td class="event-table-cell">{{event["count"]}}</td>
  </tr>
%end
</table>
</body>
</html>