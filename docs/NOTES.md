# Outline

System
    Info & Settings
    Licensing
    Deployment (Topology: Forwarders, Indexers, Search-heads)
        Outputs
    Users (Password & Profile)
    Access Control (Roles & Capabilities)
    Monitoring (Logs, Messages)
    ..discovery?..

Applications

Indexes
    Inputs

Input
    inputs.conf
    props!sourcetype

    # Enables processing of binary files (true)
    props!NO_BINARY_CHECK = <bool>

    # File 'checksum' method
    props!CHECK_METHOD = <endpoint_md5|entire_md5|modtime>

Source classification

    Sourcetype classification:
        Assigned in inputs.conf or props.conf

        props!source::<regex>
            sourcetype = <sourcetype>
        props!rule::<name>
        props!delayedrule::<name>
            sourcetype = <sourcetype>
            props!MORE_THAN*
            props!LESS_THAN*

    UNDONE: Transactions?

Source-class rules

    # Encoding (byte* => char*)
    props!CHARSET = <?>

    # Event structure (char* => event*)
    props!TRUNCATE = <uint>
    props!LINE_BREAKER = <regex>
    props!LINE_BREAKER_LOOKBEHIND = <int>
    props!SHOULD_LINEMERGE = <bool>
        props!BREAK_ONLY_BEFORE_DATE = <bool>
        props!BREAK_ONLY_BEFORE = <regex>
        props!MUST_BREAK_AFTER = <regex>
        props!MUST_NOT_BREAK_AFTER = <regex>
        props!MUST_NOT_BREAK_BEFORE = <regex>
        props!MAX_EVENTS = <int>

    # Date/time rules
    props!DATETIME_CONFIG = <filename>
    props!TIME_PREFIX = <regex>
    props!MAX_TIMESTAMP_LOOKAHEAD = <int>
    props!TIME_FORMAT = <strptime-style format>
    props!TZ = <timezone identifier>
    props!MAX_DAYS_AGO = <int>
    props!MAX_DAYS_HENCE = <int>
    props!MAX_DIFF_SECS_AGO = <int>
    props!MAX_DIFF_SECS_HENCE = <int>
        
    props!SEDCMD-<class> = <sed script> (event => event)

    props!TRANSFORMS-<value> = <stanza in transforms.conf> (UNDONE)
    props!CHECK_FOR_HEADER = <bool>

    Auditing (event => event)
        Event signing (audit.conf)

    Fields (fields.conf)
        INDEXED = <bool>
        INDEXED_VALUE = <bool>
        TOKENIZER = <?>

    Indexing rules
        indexes.conf
        props!SEGMENTATION = <segmenter from segmenters.conf>
            segmeters.conf

        UNDONE: Summary indexing

    Projection rules
        props!EXTRACT-<class> = <rex> | <transforms.conf stanza> 
        props!REPORT-<value> = <rex> | <stanza in transforms.conf>
            transforms!Extractions
        props!LOOKUP-<class> = $TRANSFORM ...
            ..lookup related things..
        props!KV_MODE=none # Disables automatic search time field extraction
        props!FIELDALIAS-<class> = (<orig-field> as <new_field>)+
        props!Sourcetype-rename

        lookup files in lookups folders
        lookup scripts in bin folder
        eventtypes.conf
        tags.conf

        Saved searches
        search scripts in bin folder
        commands.conf (?)
        alert_actions.conf
        macros.conf

        transactiontypes.conf
        multikv.conf

    Schema rules (used by both Extractiosn and Projections)
        REGEX or DELIMS/FIELDS (alternative to REGEX)
        FORMAT (optional, with REGEX)
        SOURCE_KEY (default=_raw)
        MV_ADD (default=false)
        CLEAN_KEYS (default=true)
        KEEP_EMPTY_VALS (default=false)
        CAN_OPTIMIZE (default=true)

Runtime
    Queries (aka SavedSearches)
    Commands
    Macros
    Parser
    Export
    Jobs
    Alerts

Presentation (aka User interface)
    Views
    Navigation (interaction? controllers?)
    PDF (scheduled)
    Time ranges ** Why is this under UI **

##
## props.conf
##
## Sourcetype classification & Sourceclass rules
##

# Input rules
NO_BINARY_CHECK = <bool>
CHECK_METHOD = endpoint_md5 | entire_md5 | modtime

# Preprocessor
invalid_cause = <empty> | archive | <log-string>    # [<sourcetype>]
unarchive_cmd = <string>
unarchive_sourcetype = <string>

# Processing Instructions (PIs) -- handling of ***SPLUNK*** input headers
HEADER_MODE = <empty> | always | firstline | none

# Encoding
CHARSET = <encoding> | AUTO, default = ASCII # Sourcetype or Source classes

# Sourcetype classification
sourcetype = <string>                               # [source::...] 
rename = <string>                                   # [<sourcetype>]
LEARN_SOURCETYPE = <bool>                           # [source::...]
LEARN_MODEL = <bool>
maxDist = <int>
PREFIX_SOURCETYPE = <bool>      # Sets sourcetype for too-small files

## Sourcetype classification rules
[rule::<rule-name>] and [delayedrule::<rule-name>]
    MORE_THAN* = <regex>
    LESS_THAN* = <regex>

# Line breaking (event grammar)
TRUNCATE = <uint>
LINE_BREAKER = <regex>
LINE_BREAKER_LOOKBEHIND = <int>
SHOULD_LINEMERGE = <bool>
    BREAK_ONLY_BEFORE_DATE = <bool>
    BREAK_ONLY_BEFORE = <regex>
    MUST_BREAK_AFTER = <regex>
    MUST_NOT_BREAK_AFTER = <regex>
    MUST_NOT_BREAK_BEFORE = <regex>
    MAX_EVENTS = <int>

# Input transformation (fuzzing, etc)
SEDCMD-<name> = <sed-script>

# Timestamp extraction (timestamp grammar)
DATETIME_CONFIG = <filename>
TIME_PREFIX = <regex>
MAX_TIMESTAMP_LOOKAHEAD = <int>
TIME_FORMAT = <strptime-style format>
TZ = <timezone identifier>
MAX_DAYS_AGO = <int>
MAX_DAYS_HENCE = <int>
MAX_DIFF_SECS_AGO = <int>
MAX_DIFF_SECS_HENCE = <int>

# Extraction rules
TRANSFORMS-<name> = <transforms!stanza>[, <transforms!stanza>]*
ANNOTATE_PUNCT = <bool> # Special punct::... field

# Indexing rules
SEGMENTATION = <segmenter>

# Projection rules
LOOKUP-<name> = ...
FIELDALIAS-<class> = (<original-field> AS <new-field>)+
REPORT-<name> = <transforms!stanza>[, <transforms!stanza>]*
EXTRACT-<name> = <regex> | <regex> in <source-field>
KV_MODE = none | auto | multi, default=auto

# *****

inputs.conf
    [fifo:...]          # ???
    [fschange:<path>]   # File system watcher
    [monitor://<path>]
    [tcp://<host>:<port>]
    [udp://<port>]
    [script://...]
    # UNDONE: Windows event sources

## Search

# Synchronous, "oneshot"
# NOTE: exec_mode=oneshot will block until results are ready and then will
# return in response body. A post to /services/search/jobs/export will
# begin streaming results (including preview) immediately
search(query, ...) => stream

# Async search
jobs.create(query, ...) => Job(id)

### Endpoints
* search.log
* events: <source>
* results: <source>
* results_preview
* timeline
* summary

streaming?
exec_mode = normal | blocking | oneshot
output_mode = csv | json | xml | raw
search_mode = normal | realtime

cn.jobs.create(query, **kwargs) => job(id)
    buckets: <int>
    label: <str>
    range: <timespan>
    ttl: <timespan>

job.id
job.label       # user defined job label
job.status      # job status (queued, parsing, running, finalizing, done|failed)
job.query       # the query string
job.age         # running time
job.ttl         # time-to-live
job.progress    # 1..10

job.priority(<0-10>)    # get/set
job.pause() 
job.resume()            # unpause (idempotent)
job.finalize()          # finish?
job.cancel()
job.touch() 
job.delete()            # DELETE /services/search/job/<sid>
job.save()

events: <source>
    count
    available
    get(...)
results: <source>
preview: <source>
timeline: <...>
summary: <source>
log: stream

## SPL

FIELDALIAS (keeps original field)

    /original_field::value, .../ { new_field::value, ... }

/source::<regex>/ =>
    /regex/ # Implicit format
    /regex/ { format } 
    /field::value,.../ { fieldalias::value }

    schema 
        field1 index::index

## Etc

# Tasks
* Create an alert
* CRUD an application

* Summary data (used to speed up subsequent searches)

# Creating an app
1. Create app workspace
2. Add configurations to app (workspace?)
3. Create objects for app
4. Set permissions
5. Build navigation
6. Add optional setup screen
7. Add optional package for distribution on Splunkbase

# Splunk Data (sdata)

## Objectives:
* Render XML (and JSON) data as a native Python data structure
* Keys should have friendly names in the vast majority of cases where
  namespaces arent needed to disambiguate
* Can serialize as XML or JSON
    - Will not necessarrily round-trip XML (without extra processing)

Issue: is it a requirement to preserve attribute-ness?
- This adds complexity
- We could support round-trip serialization of XML elements & attributes
  if provided a schema at serialization time.

Issue: is it a requirement to round-trip namespace names?
- May introduce too much complexity

Issue: support for fragment level scoping of namespaces names?
* Does enable composition of fragments in a single document, but the
  feature adds a lot of complexity

## Additional features
* Recognize certain well know eleemnts and transform into corresponding
  Python structure, eg: <dict> and <list>

## Schema
'{xxx}yyy': int
'{xxx}yyy': str
'{xxx}yyy': {} # Element (singleton)
'{xxx}yyy': [] # Element list

Config system
=============

# System
distsearch.conf, Configuration of distributed search
literals.conf, System strings (I think) (internal?)
outputs.conf, Configure forwarders
pubsub.conf, Configure pub/sub broker (deprecated?)
restmap.conf, Configure custom endpoints
server.conf, Configure Splunk server
web.conf, Configure Splunk web

## Access control
authentication.conf, Configure authentication method
authorize.conf, Define roles and assign capabilities to roles
default.meta.conf, Access controls for splunk objects
user-seed.conf, Configures initial username & password

## Deployment server
deploymentclient.conf, Configuration of deployment client (deprecated?)
serverclass.conf, Configuration info used by deployment server
serverclass.seed.xml.conf
tenants.conf

## Applications (what is an app?)
app.conf, Maintains the state and configuration of a Splunk app
<credentail store> - app.conf and admin/passwords

# Indexes
indexes.conf, Configure indexes
segmenters.conf (UNDONE)

# Inputs (data sources) (? => byte*)
crawl.conf, Configure the crawler
inputs.conf, Configure inputs & forwarders

## Windows
admon.conf, Configure Windows Active Directory monitoring
perfmon.conf, Configure Window Performance Monitor
procmon-filters.conf, Configure Windows Process Monitor
regmon-filters.conf, Configure Windows Registry Monitor
sysmon.conf, Configure Windows monitoring
wmi.conf, Configure WMI for use as data source

# <Input pipeline>
audit.conf, Configure event signing
eventdiscoverer.conf, Configure the eventtype learner (?)
eventtypes.conf, Configure eventtype classifications
fields.conf, Field metadata - multivalued fields & field/value indexing
multikv.conf - Event rules for table-like inputs
props.conf
source-classifier.conf (UNDONE)
sourcetypes.conf (UNDONE, machine generated)
tags.conf, Configure event tagging
transforms.conf

# Runitme (search)
alert_actions.conf, Configure global saved search actions
commands.conf, Configure custom search commands
limits.conf, Configure limits for search 
macros.conf, Define search macros
savedsearch.conf
transactiontypes.conf (UNDONE)
workflow_actions.conf (UNDONE)

# Presentation
event_renderers.conf, Associates template with eventtype
pdf_server.conf
report_server.conf
searchbnf.conf, Used by the search-assistant (read-only)
setup.xml.conf, Something having todo with app setup UI
times.conf
viewstates.conf

UNDONE
======
UNDONE: Convert the following to Jira items

# Misc
* Search model

## tools/
* Cleaup and standardize cmdline processor
* Support for optional params as environment variables
* Prompt for username/password if not supplied

## splunk/http.py
* Implement remaining HTTP verbs
* Unclear if current support for timeouts actually works

## splunk/data.py
* Investigate use of ElementTree.iterparse, et al
* Nametable
* Schema "rules"

## splunk/api.py
* Splunk search state machine

# METADATA
* No reliable way to query the signature of an endpoint
    GET <path> = 200 => get
        /link[@rel='create'] => item, create
            <path>/_new = 200 && eai:attributes... => args
        ** How do we determine if an endpoint supports DELETE?

? How do I determine if an endpoint is a read-only collection? ie: doesnt
  support create, but does support item - aka how do I distinguish between
  an entity and a read-only collection
? How do I determine the collection key
? How do I determine if a collection supports delete
? How can I discover the sig of a member of a collection if the collection
  is empty (could solve by supporting some form of wildcarding on the path)

# QUESTIONS
* How to read the current priority of a given job?

# FEEDBACK
* No way to delete an index: DELETE /services/data/indexes/{name} => 404
* No way to get a listing of all inputs, or all inputs/index
* POST /services/authentication/capabilities name=<name> => 404 (verify)
    Is there really no way to dynamically create/delete capabilities?
* search/tags and search/fields/{name}/tags use an 'older' collection
  protocol, would be nice to unify all collection protocols in a future
  version of the API
# search/fields - values are not returned as "entities" - names are returned
  and a get on that name returns the conf file value as text.

# BUGS
* /services/search/parser response does not use namespaces
* GET /services/authentication/auth-tokens/_new => 500
* DELETE /services/apps/local/{name} => 500 if app 'name' does not exist 
* POST /services/configs/inputs name=foo => 500 (Internal Server Error)
# DELETE /services/configs/inputs/SSL => 500 (Internal Server Error)
* Set invalid role on user => 400, Set multiple roles incuding invalid roles
  (if at least 1 valid) will ignore invalid and => 200.
