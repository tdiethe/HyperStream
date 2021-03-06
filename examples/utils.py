from IPython.core.display import display, HTML
import random
from dateutil.parser import parse
from datetime import datetime

epoch = datetime.utcfromtimestamp(0).replace(tzinfo=None)

def unix_time_miliseconds(dt):
    return (dt.replace(tzinfo=None) - epoch).total_seconds() * 1000.0


def plot_high_chart(time, data, title="title", yax="Y", type="high_chart"):
    if len(time) != len(data):
        print "Length of time and data must agree"
        return None

    if type == "high_chart":
        type_a = "Highcharts.chart"
        type_b = "type: 'linear'"
    else:
        type_a = "Highcharts.stockChart"
        type_b = "type: 'datetime', ordinal: false"
        time = [unix_time_miliseconds(parse(dt)) for dt in time]

    r = str(random.randint(0,10000))

    # braces braces need to be doubled in the template {{ = { and }} = }
    template = """
        <html>
        <head>
        <title>{title}</title>
           <!--<script src="https://ajax.googleapis.com/ajax/libs/jquery/2.1.3/jquery.min.js"></script>-->
           <!--<script src="https://code.highcharts.com/stock/highstock.js"></script>-->
           <!--<script src="https://code.highcharts.com/stock/modules/exporting.js"></script>-->
           <script src="./scripts/jquery.min.js"></script>
           <script src="./scripts/highstock.js"></script>
           <script src="./scripts/exporting.js"></script>
        </head>
        <body>

        <div id="container{randint}" style="width: 800px; height: 600px; margin: 125 auto"></div>

        <script language="JavaScript">
               var data = {data};

            {type_a}('container{randint}', {{
                chart: {{
                    zoomType: 'x'
                }},
                title: {{
                    text: '{title}'
                }},
                xAxis: {{
                    {type_b}
                }},
                yAxis: {{
                    title: {{
                        text: '{yax}'
                    }}
                }},
                legend: {{
                    enabled: false
                }},

                series: [{{
                    type: 'spline',
                    name: '{yax}',
                    data: data
                }}]
            }});
        </script>

        </body>
        </html>
    """

    data = [[i,j] for i, j in zip(time, data)]
    data = str(data)
    f = template.format(title=title, randint=r, data=data, type_a=type_a,
                        type_b=type_b, yax=yax)

    display(HTML(f))


def plot_multiple_stock(data, time=None, names=None, htype=None, title='title', ylabel=None):
    if isinstance(data, list) and isinstance(data[0], dict):
        seriesOptions = data
    else:
        if names is not None:
            assert(len(data) == len(names))
        if htype is not None:
            if isinstance(htype, list):
                assert(len(data) == len(htype))

        seriesOptions = []
        for i, serie_data in enumerate(data):
            serie = {}
            if time is not None:
                if isinstance(time[i], list):
                    serie_time = time[i]
                else:
                    serie_time = time
                if len(serie_time) > 0 and type(serie_time[0]) is str:
                    serie_time = [unix_time_miliseconds(parse(dt)) for dt in serie_time]
                serie['data'] = [list(a) for a in zip(serie_time, serie_data)]
            else:
                print('there is no time')
                serie['data'] = serie_data
            if htype is not None:
                if isinstance(htype, list):
                    serie['type'] = htype[i]
                else:
                    serie['type'] = htype
            if names is not None:
                if len(names) > 0:
                    serie['name'] = names[i]
                else:
                    serie['name'] = names
            seriesOptions.append(serie)

    template = """
     <html>
        <head>
        <title>{title}</title>
           <script src="./scripts/jquery.min.js"></script>
           <script src="./scripts/highstock.js"></script>
           <script src="./scripts/exporting.js"></script>
        </head>
        <body>

        <div id="container{randint}" style="width: 800px; height: 600px; margin: 125 auto"></div>

        <script language="JavaScript">
            var seriesOptions = {seriesOptions};

            /**
             * Create the chart when all data is loaded
             * @returns {{undefined}}
             */
            Highcharts.stockChart('container{randint}', {{
              chart: {{
                zoomType: 'x'
              }},
              title: {{
                  text: '{title}'
              }},
              plotOptions: {{
                series: {{
                  showInNavigator: true,
                }}
              }},
                yAxis: {{
                    title: {{
                        text: '{ylabel}'
                    }}
                }},
              tooltip: {{
                pointFormat: '<span style="color:{{series.color}}">{{series.name}}</span>:<b>{{point.y}}</b>',
                valueDecimals: 2,
                split: true
              }},
              series: seriesOptions
            }});
        </script>

        </body>
        </html>
    """

    r = str(random.randint(0,10000))
    f = template.format(randint=r, seriesOptions=seriesOptions, title=title,
                        ylabel=ylabel)

    display(HTML(f))
