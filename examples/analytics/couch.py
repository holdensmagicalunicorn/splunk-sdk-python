#!/usr/bin/env python
import couchdb
import datetime
import sys
import utils
from input import AnalyticsTracker

COUCH_SERVER = "http://pandabits:pandabits@209.20.66.59:5984/"

def process(tracker, dbname):
    server = couchdb.Server(COUCH_SERVER)
    db = server['error_tracking$%s' % dbname]
        
    count = 0
    skipped = 0
    for rowId in db:
        row = db[rowId]

        if row.has_key("received_on"):
            message = str(row.get("message", ""))
            message = message if message else ""
            stack = row.get("stack", "")
            stack = stack if stack else ""

            try:
                tracker.track(row.get("type", "error"),
                            time=row["received_on"],
                            version=row.get("version", "1.0.0.0"),
                            message=message,
                            stack=stack)
            except:
                skipped += 1
        else:
            skipped += 1

        count += 1
        if (count % 100) == 0:
            print "Submitted %d events (%d skipped) to %s" % (count, skipped, dbname)
    


def main():
    usage = ""

    argv = sys.argv[1:]

    opts = utils.parse(argv, {}, ".splunkrc", usage=usage)
    
    for dbname in opts.args:
        tracker = AnalyticsTracker(dbname, opts.kwargs)
        process(tracker, dbname)

if __name__ == "__main__":
    main()