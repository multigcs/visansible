#!/usr/bin/python3
#
#


class HtmlPage():

	def __init__(self, title = "Visansible", subtitle = "", subtitle2 = "", embed = ""):
		self.title = title
		self.subtitle = subtitle
		if self.subtitle == "":
			self.subtitle = title
		self.html = """<!DOCTYPE html>
<html lang='en'>
 <head>
  <title>""" + title + """</title>
  <meta charset='utf-8'>
  <link rel='stylesheet' type='text/css' href='assets/vis/vis.min.css' />
  <link rel='stylesheet' type='text/css' href='assets/bootstrap/css/bootstrap.css'>
  <link rel='stylesheet' type='text/css' href='assets/material-design-iconic-font/dist/css/material-design-iconic-font.min.css'>
  <link rel='stylesheet' type='text/css' href='assets/animate.css/animate.min.css'>
  <script type='text/javascript' src='assets/jquery/jquery.min.js'></script>
  <script type='text/javascript' src='assets/vis/vis.min.js'></script>
  <script type='text/javascript' src='assets/bootstrap/js/bootstrap.min.js'></script>
  <script type='text/javascript' src='assets/chart/Chart.min.js'></script>
  <script type='text/javascript' src='assets/d3/d3.min.js'></script>
  <script type='text/javascript' src='assets/d3/d3pie.min.js'></script>
  <style>
.main-content {
  padding-top: 15px;
  padding-bottom: 15px;
  padding-left: 25px;
  padding-right: 25px;
}

body {
  overflow-x: hidden;
}

#sidebar-wrapper {
  min-height: 100vh;
  margin-left: -15rem;
  -webkit-transition: margin .25s ease-out;
  -moz-transition: margin .25s ease-out;
  -o-transition: margin .25s ease-out;
  transition: margin .25s ease-out;
}

#sidebar-wrapper .sidebar-heading {
  padding: 0.875rem 1.25rem;
  font-size: 1.2rem;
}

#sidebar-wrapper .list-group {
  width: 15rem;
}

#page-content-wrapper {
  min-width: 100vw;
}

#wrapper.toggled #sidebar-wrapper {
  margin-left: 0;
}

@media (min-width: 768px) {
  #sidebar-wrapper {
    margin-left: 0;
  }

  #page-content-wrapper {
    min-width: 0;
    width: 100%;
  }

  #wrapper.toggled #sidebar-wrapper {
    margin-left: -15rem;
  }
}
td {
    margin: 0;
    padding: 0;
}
.modal-dialog {
    max-width: 72%;
}

   .col-1, .col-2, .col-3, .col-4, .col-5, .col-6, .col-7, .col-8, .col-9, .col-10, .col-11, .col-12, .col, .col-auto, .col-sm-1, .col-sm-2, .col-sm-3, .col-sm-4, .col-sm-5, .col-sm-6, .col-sm-7, .col-sm-8, .col-sm-9, .col-sm-10, .col-sm-11, .col-sm-12, .col-sm, .col-sm-auto, .col-md-1, .col-md-2, .col-md-3, .col-md-4, .col-md-5, .col-md-6, .col-md-7, .col-md-8, .col-md-9, .col-md-10, .col-md-11, .col-md-12, .col-md, .col-md-auto, .col-lg-1, .col-lg-2, .col-lg-3, .col-lg-4, .col-lg-5, .col-lg-6, .col-lg-7, .col-lg-8, .col-lg-9, .col-lg-10, .col-lg-11, .col-lg-12, .col-lg, .col-lg-auto, .col-xl-1, .col-xl-2, .col-xl-3, .col-xl-4, .col-xl-5, .col-xl-6, .col-xl-7, .col-xl-8, .col-xl-9, .col-xl-10, .col-xl-11, .col-xl-12, .col-xl, .col-xl-auto {
	padding-bottom: 14px;
	padding-right: 7px;
	padding-left: 7px;
   }
   .card {
	height: 100%;
	box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2), 0 6px 20px 0 rgba(0, 0, 0, 0.19);
   }
   .card-header {
	padding: 0.15rem 0.5rem;
   }
   body {
	font-size: 0.8rem;
   }
   td {
	vertical-align: top;
   }
   .wrapper {
	display: flex;
	width: 100%;
	align-items: stretch;
   }
  </style>
 </head>
 <body>
   <div class="d-flex" id="wrapper">
    <div class="bg-light border-right" id="sidebar-wrapper">
     <div class="sidebar-heading">""" + title + """</div>
     <div class="list-group list-group-flush">
      <a href="hosts" class="list-group-item list-group-item-action bg-light">Hosts</a>
      <a href="network" class="list-group-item list-group-item-action bg-light">Network</a>
      <a href="groups" class="list-group-item list-group-item-action bg-light">Groups</a>
      <a href="stats" class="list-group-item list-group-item-action bg-light">Stats</a>
      <a href="inventory" class="list-group-item list-group-item-action bg-light">Inventory-File</a>
      <a href="rescan" class="list-group-item list-group-item-action bg-light">Rescan</a>
      <a target="_blank" href="csv" class="list-group-item list-group-item-action bg-light">CSV</a>
     </div>
""" + embed + """
    </div>
    <div id="page-content-wrapper">
      <nav class="navbar navbar-expand-lg navbar-light bg-light border-bottom">
        <img id="menu-toggle" src="assets/MaterialDesignIcons/menu-left-outline.svg" />
        <button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbarSupportedContent" aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
         <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarSupportedContent">
         <b>""" + subtitle + """</b>
         <ul class="navbar-nav ml-auto mt-2 mt-lg-0">
          <li class="nav-item active">
           <a class="nav-link" href="#">""" + subtitle2 + """</a>
          </li>
         </ul>
        </div>
      </nav>
      <div class="container-fluid main-content">
"""

	def add(self, html):
		self.html += str(html)

	def end(self):
		self.html += """
    </div><!--/main-content-->
   </div>
  </div>
  <script>
   $("#menu-toggle").click(function(e) {
     e.preventDefault();
     $("#wrapper").toggleClass("toggled");
   });
  </script>
 </body>
</html>
"""
		return self.html

