%#template to generate a HTML table from a list of tuples (or list of lists, or tuple of tuples or ...)
<html>
<head>

<!-- JQUERY -->
<script type="text/javascript" src="https://ajax.googleapis.com/ajax/libs/jquery/1.6.2/jquery.js"></script>
<style>
body {
    width: 50%;
}
.application-info {
    margin-bottom: 6px;
    background: #aaa;
    border: 1px solid #DBDBDB;
    font-weight: bold;
    height: 44px;
    line-height: 44px;
    padding-left: 20px;

    background: -webkit-gradient(linear,left top,left bottom,from(white),to(#EEE));
    background: -moz-linear-gradient(top,white,#EEE);
    filter: progid:DXImageTransform.Microsoft.gradient(startColorstr='white',endColorstr='#EEE');

}
.application-name {
    font-size: 14px;
    padding-left: 10px;
}
.application-event-count {
    font-size: 14px;
    padding-right: 10px;
}
.application-info a {
    color: #416590;
}
a, a:visited {
    text-decoration: none;
    outline: 0;
}
a:hover {
    text-decoration: underline;
}
.left {
    float: left;
}
.right {
    float: right;
}
.clear {
    clear: both;
}
.uppercase {
    text-transform:uppercase;
}
</style>
<title>APPLICATIONS</title>
</head>
<body>
<div id="applications">
%for application in applications:
    <div class="application-info">
        <div class="application-name left uppercase">
            <a href='application/{{application["name"]}}'>{{application["name"]}}</a>
        </div>
        <div class="application-event-count right uppercase">
            {{application["count"]}} events
        </div>
    </div>
%end
</div>
</body>
</html>