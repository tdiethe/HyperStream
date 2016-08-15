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
from base_channel import BaseChannel
from ..stream import StreamReference
from ..channel_state import ChannelState
from ..modifiers import Identity
from datetime import timedelta, datetime
from ..time_interval import TimeIntervals
import pytz
import logging


class MemoryChannel(BaseChannel):
    def __init__(self, channel_id):
        state = ChannelState(channel_id)
        super(MemoryChannel, self).__init__(can_calc=True, can_create=True, state=state)
        self.streams = {}
        self.max_stream_id = 0
    
    def repr_stream(self, stream_id):
        s = repr(self.state.id2def[stream_id])
        return s
    
    def create_stream(self, stream_def):
        """
        Must be overridden by deriving classes, must create the stream according to stream_def and return its unique
        identifier stream_id
        """
        self.max_stream_id += 1
        stream_id = self.max_stream_id
        self.streams[stream_id] = []
        return stream_id
    
    def get_params(self, x, start, end):
        if isinstance(x, (list, tuple)):
            res = []
            for x_i in x:
                res.append(self.get_params(x_i, start, end))
            if isinstance(x, list):
                return res
            else:
                return tuple(res)
        elif isinstance(x, dict):
            res = {}
            for x_i in x:
                res[x_i] = self.get_params(x[x_i], start, end)
            return res
        elif isinstance(x, StreamReference):
            return x(start=start, end=end)
        else:
            return x
    
    def get_results(self, stream_ref, args, kwargs):
        stream_id = stream_ref.stream_id
        abs_end, abs_start = self.get_absolute_start_end(kwargs, stream_ref)
        done_calc_times = self.state.stream_id_to_intervals_mapping[stream_id]
        need_to_calc_times = TimeIntervals([(abs_start, abs_end)]) - done_calc_times
        if str(need_to_calc_times) != '':
            stream_def = self.state.stream_id_to_definition_mapping[stream_id]
            writer = self.get_stream_writer(stream_id)
            tool = stream_def.tool
            for interval2 in need_to_calc_times.intervals:
                args2 = self.get_params(stream_def.args, interval2.start, interval2.end)
                kwargs2 = self.get_params(stream_def.kwargs, interval2.start, interval2.end)
                tool(stream_def, interval2.start, interval2.end, writer, *args2, **kwargs2)
                self.state.stream_id_to_intervals_mapping[stream_id] += TimeIntervals(
                    [(interval2.start, interval2.end)])
            
            done_calc_times = self.state.stream_id_to_intervals_mapping[stream_id]
            need_to_calc_times = TimeIntervals([(abs_start, abs_end)]) - done_calc_times
            logging.debug(done_calc_times)
            logging.debug(need_to_calc_times)
            assert str(need_to_calc_times) == ''
        result = []
        for (timestamp, data) in self.streams[stream_ref.stream_id]:
            if abs_start < timestamp <= abs_end:
                result.append((timestamp, data))
        result.sort(key=lambda x: x[0])
        result = stream_ref.modifier(
            (x for x in result))  # make a generator out from result and then apply the modifier
        return result
    
    def get_stream_writer(self, stream_id):
        def writer(document_collection):
            self.streams[stream_id].extend(document_collection)
        
        return writer
    
    def get_default_ref(self):
        return {'start': timedelta(0), 'end': timedelta(0), 'modifier': Identity()}


class ReadOnlyMemoryChannel(BaseChannel):
    """
    An abstract channel with a read-only set of memory-based streams.
    By default it is constructed empty with the last update at MIN_DATE.
    New streams and documents within streams are created with the update(up_to_timestamp) method,
    which ensures that the channel is up to date until up_to_timestamp.
    No documents nor streams are ever deleted.
    Any deriving class must override update_streams(up_to_timestamp) which must update self.streams to be calculated
    until up_to_timestamp exactly.
    The data structure self.streams is a dict of streams indexed by stream_id, each stream is a list of tuples
    (timestamp,data), in no specific order.
    Names and identifiers are the same in this channel.
    """
    
    def create_stream(self, stream_def):
        raise NotImplementedError("Read-only channel")
    
    def get_stream_writer(self, stream_id):
        raise NotImplementedError("Read-only channel")
    
    def __init__(self, channel_id, up_to_timestamp=datetime.min.replace(tzinfo=pytz.utc)):
        # TODO: should the up_to_timestamp parameter be up to datetime.max?
        
        state = ChannelState(channel_id)
        super(ReadOnlyMemoryChannel, self).__init__(can_calc=False, can_create=False, state=state)
        self.streams = {}
        self.up_to_timestamp = datetime.min.replace(tzinfo=pytz.utc)
        if up_to_timestamp > datetime.min.replace(tzinfo=pytz.utc):
            self.update(up_to_timestamp)
    
    def repr_stream(self, stream_id):
        return 'externally defined, memory-based, read-only stream'
    
    def update_streams(self, up_to_timestamp):
        """
        Deriving classes must override this function
        """
        raise NotImplementedError
    
    def update(self, up_to_timestamp):
        """
        Call this function to ensure that the channel is up to date at the time of timestamp.
        I.e., all the streams that have been created before or at that timestamp are calculated exactly until
        up_to_timestamp.
        """
        self.update_streams(up_to_timestamp)
        self.update_state(up_to_timestamp)
    
    def update_state(self, up_to_timestamp):
        for stream_id in self.streams.keys():
            self.state.name_to_id_mapping[stream_id] = stream_id
            intervals = TimeIntervals([(datetime.min.replace(tzinfo=pytz.utc), up_to_timestamp)])
            self.state.stream_id_to_intervals_mapping[stream_id] = intervals
        self.up_to_timestamp = up_to_timestamp
    
    def get_results(self, stream_ref, args, kwargs):
        start = stream_ref.start
        end = stream_ref.end
        if isinstance(start, timedelta) or isinstance(end, timedelta):
            raise Exception('Cannot calculate a relative stream_ref')
        if end > self.up_to_timestamp:
            raise Exception(
                'The stream is not available after ' + str(self.up_to_timestamp) + ' and cannot be calculated')
        result = []
        for (tool_info, data) in self.streams[stream_ref.stream_id]:
            if start < tool_info.timestamp <= end:
                result.append((tool_info.timestamp, data))
        result.sort(key=lambda x: x[0])
        result = stream_ref.modifier(
            (x for x in result))  # make a generator out from result and then apply the modifier
        return result
