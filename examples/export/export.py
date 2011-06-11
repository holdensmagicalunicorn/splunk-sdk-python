#!/usr/bin/env python
#
# Copyright 2011 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
This software exports a splunk index using the streaming export endpoint
using a parameterized chunking mechanism.
"""

# installation support files
from optparse import OptionParser
import sys
import operator
import time
import os

# splunk support files
import splunk.binding as binding
from splunk.binding import connect

from utils import cmdopts

# hidden file
RESTART_FILE = "./.export_restart_log"

def parse_args():
    """ parse cli arguments """

    opt = OptionParser("usage: <TBD>", version="0.0")

    ## dynamically build the cli args
    opt.add_option("-i", "--index", 
              default="*",
              help="Index to export (default is all indexes)",
              dest="index")

    opt.add_option("-p", "--progress", 
              default=False,
              help="display bucket processing progress",
              dest="progress")

    opt.add_option("-s", "--starttime", 
              default=0,
              help="Start time of export (default is start of index)",
              dest="start")

    opt.add_option("-e", "--endtime", 
              default=0,
              help="End time of export (default is end of index)",
              dest="end")

    opt.add_option("-o", "--output", 
              default="export.out",
              help="export output file (defaults to export.out)",
              dest="output")

    opt.add_option("-f", "--format", 
              default="csv",
              help="export output format (defaults to csv)",
              dest="format")

    opt.add_option("-l", "--limit", 
              default="20000",
              help="Number of events to limit per chunk (defaults to 20000)",
              dest="limit")

    opt.add_option("-r", "--restart", 
              default=False,
              help="restart an existing export that was prematurely ended",
              dest="restart")

    return opt.parse_args()

def query(context, start, end, span, index):
    """ query the server for a specific range of events """

    # generate a search
    squery = "search * index=%s " % index
    squery = squery + "timeformat=%s "

    # if start/end specified, use them
    if start != 0:
        squery = squery + "starttime=%d " % start
    if end != 0:
        squery = squery + "endtime=%d " % end

    # span is in seconds for buckets
    squery = squery + "| timechart "

    if span == 86400:
        # force splunk into 12:00:00AM start time for buckets.
        squery = squery + "span=1d "
    else:
        squery = squery + "span=%ds " % span

    squery = squery + "count"

    result = context.get('search/jobs/export', search=squery, output_mode="csv")
    if result.status != 200:
        print "Failed to collect summary event buckets"
        return []

    # generate a list of lines from teh csv return data
    lines = result.body.read().splitlines()
    if len(lines) == 0:
        return []

    return lines

def get_buckets(context, start, end, index, limit, span):
    """ generate an export to splunkd for the index
        elememnts within the given time range """

    # time downsampling ratio day:hour, hour:minute, minute:second
    # the initial time span is 1 day (86400 seconds) -- if the number
    # of events is too large, break down the day into hours, repeat
    # as necessary to minutes and then to seconds.
    #
    # We do this to make a reasonable amount of data transfer for each
    # request when we export the data. It allows for fine grained 
    # restart on errors
    # 
    # also because splunk "snaps" events based on the span size, this
    # behavior requires span and start/end times to be fully in phase
    # (i.e. modulo 0)
    downsample = { 86400 : 3600, 3600 : 60, 60 : 1 }

    # trace/debug
    #print 'start=%d, end=%d, index=%s, maxevents=%d, timespan=%d' % \
    #      (start, end, index, limit, span)

    lines = query(context, start, end, span, index)
    if len(lines) == 0:
        return []

    # strip out line 0: Line 0 is the header info
    # which contains the text: 
    #     count,"_time","_span", ["_spandays"]
    lines.remove(lines[0])

    buckets = []

    # parse the lines returned from splunk. They are in the form
    # eventcount,starttime,timequantum
    for line in lines:
        elements = line.split(",")
       
        # extract the element components
        enumevents = int(elements[0])
        estarttime = int(elements[1])
        espan = int(elements[2])

        # if the numnber of events in this bucket is larger than
        # our limit, we need to break them up (cut in half)
        if enumevents > limit:
            # only split down to one second
            if span > 1:
                # get next smaller chunk
                newspan = downsample[span]

                # make smaller buckets, recurse with smaller span
                endtime = estarttime + span
                expanded = get_buckets(context, estarttime, endtime, 
                                       index, limit, newspan)
                # flatten list and put into current list
                for bucket in expanded:
                    buckets.append(bucket)
            else:
                # can't get any smaller than 1 second interval
                buckets.append((enumevents, estarttime, espan))
        else:
            # add to our list
            buckets.append((enumevents, estarttime, espan))

    return buckets

def normalize_export_buckets(options, context):
    """ query splunk to get the buckets of events and attempt to normalize """

    # TODO: figure out time conversion format for user-friendliness,
    # but for now, for now use seconds -- start/end time should also
    # start on a day boundary for the downsampling chunking to work
    # properly

    # start with a bucket size of one day: 86400 seconds
    buckets = get_buckets(context, int(options.start), int(options.end), 
                          options.index, int(options.limit), 86400)

    # sort on start time: tuples are (events, starttime, quantum)
    # necessary? probably not
    buckets = sorted(buckets, key=operator.itemgetter(1)) 

    return buckets

def sanitize_restart_bucket_list(options, bucket_list):
    """ clean up bucket list for an export already in progress """

    sane = True

    # run through the entries we have already processed found in the restart
    # file and remove them from the live bucket list.
    # 
    # NOTE: we will also check for corroboration between live and processed
    # lists

    # read restart file into a new list
    rfd = open(RESTART_FILE, "r")
    rslist = []
    for line in rfd:
        line = line[:-1].split(",")
        rslist.append((int(line[0]), int(line[1]), int(line[2])))
    rfd.close()

    fslist_final = []

    for entry in rslist:
        # throw away empty buckets, until a non-empty bucket
        while bucket_list[0][0] == 0:
            bucket_list.pop(0)

        if bucket_list[0] != entry:
            print "Warning: live list contains: %s, restart list contains: %s" \
                 % (str(bucket_list[0]), str(rslist[0]))
            sane = False

        if options.progress:
            print "restart skipping already handled bucket: %s" % str(entry)
        bucket_list.pop(0)

    return (bucket_list, sane)

def report_banner(bucket_list):
    """ output banner for export operation """

    eventcount = 0
    requests = 0

    for bucket in bucket_list:
        if bucket[0] > 0:
            requests += 1
        eventcount += bucket[0]

    print "Events exported: %d, requiring %d splunk fetches" % \
                                            (eventcount, requests)

def export(options, context, bucket_list):
    """ given the buckets, export the events """

    header = False

    if options.restart:
        (bucket_list, sane) = sanitize_restart_bucket_list(options, bucket_list)
        if not sane:
            print "Mismatch between restart and live event list, exiting"
            sys.exit(1)

    report_banner(bucket_list)

    # (re)open restart file appending to the end if it exists
    rfd = open(RESTART_FILE, "a")

    for bucket in bucket_list:
        if bucket[0] == 0:
            if options.progress:
                print "SKIPPING BUCKET:-------- %s" % str(bucket)
        else:
            success = False
            while not success:
                if options.progress:
                    print "PROCESSING BUCKET:-------- %s" % str(bucket)
                # generate a search
                squery = "search * index=%s " % options.index
                squery = squery + "timeformat=%s "

                start = bucket[1]
                quantum = bucket[2]

                squery = squery + "starttime=%d " % start
                squery = squery + "endtime=%d " % (start+quantum)
    
                # issue query to splunkd
                # max_count=0 overrides the maximum number of events
                # returned (normally 50K) regardless of what the .conf
                # file for splunkd says. Note that this is only effective
                # on the export endpoint
                result = context.get('search/jobs/export', 
                                 search=squery, 
                                 output_mode=options.format,
                                 max_count=int(bucket[0])+1)

                #result = context.post('/services/search/jobs/oneshot',
                #                  search=squery,
                #                  output_mode=options.format)
    
                if result.status != 200:
                    # TODO: retry on failure, sleep and retry?
                    # at sme point, maybe give up... and the user can
                    # attempt a restart export
                    print "HTTP status: %d, sleep and retry..." % \
                          result.status
                    time.sleep(10)
                else:
                    success = True

            # write export file 
            # N.B.: atomic writes in python don't seem to exist. In order
            # *really* make this robust, we need to atomically write the 
            # body of the event returned AND update the restart file and
            # guarantee both committed.

            # atomic write start
            # TODO: post process results before writing?

            data = result.body.read()
            data = data.splitlines()
            if len(data) > 0:
                firstline = data[0]
                data.pop(0)

                if not header:
                    options.fd.write(firstline)
                    options.fd.write("\n")
                    header = True

                for line in data:
                    options.fd.write(line)
                    options.fd.write("\n")

                options.fd.flush()

            rfd.write(str(bucket).strip("(").strip(")").replace(" ",""))
            rfd.write("\n")
            rfd.flush()
            # atomic write commit

    return True

def main():
    """ main entry """


    # perform idempotent login/connect -- get login creds from ~/.splunkrc
    # TODO: allow for credential supplied via CLI args
    opts = cmdopts.parse([], {}, ".splunkrc")
    connection = connect(**opts.kwargs)

    # get lower level context
    context = binding.connect( host=connection.host, 
                               username=connection.username,
                               password=connection.password)
    # check for extraneous cli arguments
    (options, args) = parse_args()
    if args:
        print "Unknown argument found: %s" % args
        sys.exit(1)

    # open output file
    try:
        options.fd = open(options.output, "w")
    except IOError:
        print "Failed to open output file %s for writing" % options.output
        sys.exit(1)

    # open restart file
    rfd = None
    try:
        rfd = open(RESTART_FILE, "r")
    except IOError:
        pass

    # check request and environment for sanity
    if options.restart is not False and rfd is None:
        print "Failed to open restart file %s for reading" % RESTART_FILE
        sys.exit(1)
    elif options.restart is False and rfd is not None:
        print "Warning: restart file %s exists." % RESTART_FILE
        print "         manually remove this file to continue complete export"
        sys.exit(1)
    else:
        pass

    # close restart file 
    if rfd is not None:
        rfd.close()

    # normalize buckets to contain no more than "limit" events per bucket
    # however, there may be a situation where there will be more events in 
    # our smallest bucket (one second) -- but there is not much we are going
    # to do about it
    bucket_list = normalize_export_buckets(options, context)

    # chunk through each bucket, and on success, remove the restart file
    if export(options, context, bucket_list) is True:
        os.remove(RESTART_FILE)

if __name__ == '__main__':
    main()
