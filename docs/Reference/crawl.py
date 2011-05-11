import sys
import csv
import os

try:
    os.mkdir('endpointdocs')
except:
    pass

csvr = csv.reader(sys.stdin)
for line in csvr:
    endpoint = line[0]

    if endpoint.startswith('/services/'):
        endpoint = endpoint[len('/services/'):]

    if endpoint.startswith('#') or endpoint.startswith('search'):
        continue

    if '{' in endpoint:
        continue

    dest_file = 'endpointdocs/' + endpoint.replace("/", ".")

    if not endpoint.startswith('/'):
        endpoint = '/services/' + endpoint

    print "processing %s" % endpoint
    os.system("splunkd rest GET '%s/_doc?pot=%s'" % (endpoint, dest_file))
    os.system("msginit -i %s -o %s.po --no-translator" % (dest_file, dest_file))
