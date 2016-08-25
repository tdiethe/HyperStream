"""
The MIT License (MIT)
Copyright (c) 2014-2017 University of Bristol

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
OR OTHER DEALINGS IN THE SOFTWARE.
"""
from hyperstream.tool import Tool
from sphere_connector_package.sphere_connector import SphereConnector, DataWindow


# TODO Switch to persistent connectivity rather than connecting each time
class SphereSilhouette(Tool):
    sphere_connector = SphereConnector(config_filename='config_strauss.json', include_mongo=True, include_redcap=False)

    def __init__(self, filters):
        super(SphereSilhouette, self).__init__(filters=filters)
        self.filters = filters

    def _execute(self, input_streams, interval, writer):
        window = DataWindow(start=interval.start, end=interval.end, sphere_connector=self.sphere_connector)
        writer(window.video.get_data(elements='silhouette', filters=self.filters))
