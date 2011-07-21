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

import sqlite3, sys, json
from bottle import route, run, debug, template, static_file, request
from output import AnalyticsRetriever
import utils
from time import strptime, mktime

splunk_opts = None
retrievers = {}

def get_retriever(name):
    global retrievers
    retriever = None
    if retrievers.has_key(name):
        retriever = retrievers[name]
    else:
        retriever = AnalyticsRetriever(name, splunk_opts)
        retrievers[name] = retriever

    return retriever

@route('/static/:file')
def help(file):
    raise static_file(file, root='/Users/itay/Work/splunk-sdk-python/examples/analytics')

@route('/todo')
def todo_list():
    conn = sqlite3.connect('todo.db')
    c = conn.cursor()
    c.execute("SELECT id, task FROM todo WHERE status LIKE '1'")
    result = c.fetchall()
    c.close()
    output = template('templates/make_table', rows=result)
    return output

@route('/applications')
def applications():
    retriever = get_retriever("")
    applications = retriever.applications()
    
    output = template('templates/applications', applications=applications)
    return output

@route('/application/:name')
def application(name):
    retriever = get_retriever(name)
    events = retriever.events()
    event_name = request.GET.get("event_name", "")
    property_name = request.GET.get("property", "")

    events_over_time = []
    properties = []
    if not event_name:
        events_over_time = retriever.events_over_time()
    else:
        events_over_time = retriever.event_over_time(event_name, property=property_name)  
        properties = retriever.properties(event_name) 

    # We need to format the events to something the graphing library can handle
    data = []
    for name, ticks in events_over_time.iteritems():
        event_ticks = []
        for tick in ticks:
            time = strptime(tick["time"][:-6] ,'%Y-%m-%dT%H:%M:%S.%f')
            count = tick["count"]
            event_ticks.append([int(mktime(time)*1000),count])
        
        data.append({
            "label": name,
            "data": event_ticks,
        })

    json_events = json.dumps(data, sort_keys = True, indent = 2)

    output = template('templates/application', 
                events=events,
                event_name=event_name,
                application_name=retriever.application_name, 
                properties=properties,
                json_events=json_events,
                property_name=property_name)

    return output

def main():
    argv = sys.argv[1:]

    opts = utils.parse(argv, {}, ".splunkrc")
    global splunk_opts
    splunk_opts = opts.kwargs

    debug(True)
    run(reloader=True)

if __name__ == "__main__":
    main()
