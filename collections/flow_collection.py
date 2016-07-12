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
import os
import simplejson as json
import logging
from sphere_connector_package.sphere_connector.utils import Printable
from ..flow import Flow


class FlowCollection(Printable):
    flows = []

    def __init__(self, stream_collection, path):
        for filename in os.listdir(os.path.join(path, "active")):
            if filename.endswith(".json") and filename != "skeleton.json":
                try:
                    logging.info('Reading ' + filename)
                    with open(os.path.join(path, "active", filename), 'r') as f:
                        flow_definition = json.load(f)
                        flow = Flow(stream_collection, **flow_definition)
                        self.flows.append(flow)
                except (OSError, IOError) as e:
                    logging.error(str(filename) + ' error: ' + str(e))

    def execute_all(self, clients, configs):
        for flow in self.flows:
            flow.execute(clients, configs)
