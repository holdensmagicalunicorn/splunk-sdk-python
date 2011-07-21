%#template to generate a HTML table from a list of tuples (or list of lists, or tuple of tuples or ...)
<html>
<head>

<!-- JQUERY -->
<script type="text/javascript" src="https://ajax.googleapis.com/ajax/libs/jquery/1.6.2/jquery.js"></script> 
<link href="http://ajax.googleapis.com/ajax/libs/jqueryui/1.8/themes/base/jquery-ui.css" rel="stylesheet" type="text/css"/>
<script src="http://ajax.googleapis.com/ajax/libs/jqueryui/1.8/jquery-ui.js"></script>
  

<!-- JQUERY FLOT -->
<script type="text/javascript" src="/static/jquery.flot.js"></script>
<script type="text/javascript" src="/static/jquery.flot.selection.js"></script>

<!-- LOGIC -->
<script type="text/javascript">
    var events = {{json_events}};
    
    var showTooltip = function(x, y, contents) {
        $('<div id="tooltip">' + contents + '</div>').css( {
            position: 'absolute',
            display: 'none',
            top: y + 5,
            left: x + 5,
            border: '1px solid #fdd',
            padding: '2px',
            'background-color': '#fee',
            opacity: 0.80
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
                    console.log(item);
                    var label = item.series.label;
                    var count = item.datapoint[1];

                    showTooltip(item.pageX, item.pageY, label + ": " + count);
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
            legend.append('<input type="checkbox" id="legend-label-'+i+'" checked/>'
            +'<label for="legend-label-'+i+'" id="'+label+'">'
                + '<div>'
                    + '<div class="legend-color" style="display:inline;background-color:'+color+';width:20px;height:20px;float:left;"></div>'
                    + '<div style="float:left;">' + label + '</div>'
                + '</div>'
            + '</label>');
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
    width: 80%;
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
    width: 100%;
    height: 400px;
}
div#legend table {
    table-layout: fixed;
    width: 90%;
    margin: 0px auto;
}
#legend {
    width: 90%;
    margin: 0px auto;
    margin-top: 10px;
}
#legend span.ui-button-text > div div {
    text-overflow: ellipsis;
    overflow: hidden !important;
    white-space: nowrap !important;
    width: 75%;
    margin-left: 5px;
}

.ui-button {
    width: 23%;
    margin: 5px 5px 5px 5px !important;
    border: 0px;
}

.ui-state-default {
    background: white !important;
    color: #DADADA !important;
}
.ui-state-active {
    background: white !important;/*#DADADA !important;*/
    color: black !important;
}

label.ui-widget[aria-pressed=false] .legend-color {
    background-color: #DADADA !important;
}

td.legendLabel {
    text-overflow: ellipsis;
    overflow: hidden !important;
    white-space: nowrap !important;
    width: 100%;
}
td.legendColorBox {
    width: 20px;
}
.gray-gradient-box {
    border: 1px solid #CFCFCF;
    background: #F2F2F2;
    filter: progid:DXImageTransform.Microsoft.gradient(startColorstr='white',endColorstr='#E4E4E4');
    background: -webkit-gradient(linear,left top,left bottom,from(white),to(#E4E4E4));
    background: -moz-linear-gradient(top,white,#E4E4E4);
}
#title {
    color: #4E74A1;
    font-size: 20px;
    font-weight: bold;
    line-height: 18px;
    margin: 5px;
}
</style>
</head>

<body>
<div id="header" class="gray-gradient-box">
    <div id="title" class="uppercase">{{application_name}}{{ " -- " if event_name else ""}}{{ event_name }} {{" -- " if property_name else ""}}{{property_name}}</div>
</div>
<div id="placeholder" class="graph"></div> 
<div id="legend"></div>
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