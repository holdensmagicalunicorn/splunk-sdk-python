# Server
..discover..
..manage (CRUD)..
Server roles/workloads - indexer, forwarder, search-head

## Server Control
/services/admin/sever-control/restart
/services/server/control/restart

Authentication methods
    providers

## Server Metadata
/services/server/info
/services/server/settings

### UNDONE: What is the following?
/services/server/logger
/services/server/logger/<item-name>

## Server Topology (forwarders, indexers, search-heads)

### UNDONE: Not sure how the following works
/services/admin/deploymentclient
/services/admin/deploymentserver
/services/admin/deploymentserverclass
/services/admin/deploymenttenants
/services/admin/distsearch-peer
/services/admin/distsearch-peer/<peer-host:per-mgmt-port>

## Server Objects
    Users
        Password
        Roles
    Roles
    Capabilities

## Server Misc.
    ..backup..

# Indexes (repository?)
    _An index is a collection of events_ 
    ..input process..
        Stream:
            Character set encoding
            "SED"
            ...
        Events:
            Linebreaking (event structure)
            Timestamps
            Fields
            Segmentation (?)

        source => <strean> => 
            fileter/transform => <stream> =>
            event-extraction => <events>
            event filter/transform => <events> => index

    Properties:
        path (db, thawed, cold)
        maxsize

# Inputs
    ..sources..
    
    Input modes
        Subscribe
            monitor, tcp, udp, cron
        Load (once)
        Run (once)
        HTTP-put (insert)
            /services/receivers/simple
            /services/receivers/stream
            
            /index/<channel>?

    Transforms
        TRANSFORMS-<name>
        REPORT-<name>
        EXTRACT-<name>
        SEDCMD-<name>
        LOOKUP-<name>
        FIELDALIAS-<name>

# Search Jobs
    Enumerate, CRUD (aka Job Control)
    Retrieving results
        Notifications

# Applications (?)
    Enumerate, CRUD
    Install

Outputs (advanced?)
    ...

# Objects
Event types
Search (queries)
    query
    schedule
    lifetime
    action
Search macros (advanced search)
Search commands (advanced search)
Report (UNDONE: Whats the difference between a search and report?)
Fields
    aliases
    extractions
    transformations
    Sourcetype renaming
    Workflow actions
Lookups (file-based or "external")
    lookup table files
    lookup definitions
    automatic lookups
Tags

Presentation (aka User interface)
    Views
    Navigation (interaction? controllers?)
    PDF (scheduled)
    Time ranges ** Why is this under UI **

All configurations

Namespaces?

# *****

inputs.conf
    [fifo:...]          # ???
    [fschange:<path>]   # File system watcher
    [monitor://<path>]
    [tcp://<host>:<port>]
    [udp://<port>]
    [script://...]
    # UNDONE: Windows event sources
    # SNMP?

props.conf
    * Line breaking
    * Timestamp extraction
    * Segmentation
        SEGMENTATION = <segmenter from segmenters.conf>
    * File checksum configuration
    * Small file settings

    TRANSFORMS-<value> = <stanza in transforms.conf>
        REGEX => TRANSFORM
    REPORT-<value> = <stanza in transforms.conf>
    EXTRACT-<class> = <regex>
    SEDCMD-<class> = <sed script>
    LOOKUP-<class> = $TRANSFORM ...
    FIELDALIAS-<class> = (<orig-field> as <new_field>)+

    Sourcetype configuration

transforms.conf
    Definition of "patterns"

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

#
# Collections
# ===========
# alerts?
# app(name)/apps
# capability(name)/capabilities
# object(name)/objects          -- admin/directory
# role(name)/roles 
# user(name)/users
# config(name)/configs          -- configs
# input(name)/inputs            -- configs/inputs, data/inputs
# command(name)/commands        -- data/commands
# index(name)/indexes           -- data/indexes
# output(name)/outputs          -- data/outupts
#
# extractions                   - data/props/extractions, data/transforms/extr.
# fieldaliases                  - data/props/fieldaliases
# lookups                       - data/props/lookups, data/transforms/lookups
# sourcetype-rename             - data/props/sourcetype-rename
#
# eventtypes                    -- saved/eventtypes
# views                         -- scheduled/views
# commands                      -- search/commands
# fields                        -- search/fields
#
# searches                      -- saved/searches
# jobs                          -- search/jobs
#
# licenses                      -- licenser/licenses
#
# Configuration
# =============
# properties                    -- properties
# search/distributed/config..
# search/distributed/peers
# ...
#
# Command & control
# =================
# 
# Special
# ======
# parser                        -- search/parser
# timeparser                    -- search/timeparser
# typeahead                     -- search/typeahead

# More misc. notes

## Knowledge objects
* Apps
* Dashboards
* Event types
* Field extractions
* Fields
* Lookups
* Saved searches
* Search commands
* Tags

## Configurations
(Configurations are global)

* Users
* Roles

* Authentication
* Distributed search
* Inputs
* Outputs
* Deployment
* License
* Server settings

### Others, mentioned in the docs
Form
Navigation
Report
Search macros
Transaction
View
Workspace

## Etc

* Summary data (used to speed up subsequent searches)

# Creating an app
1. Create app workspace
2. Add configurations to app (workspace?)
3. Create objects for app
4. Set permissions
5. Build navigation
6. Add optional setup screen
7. Add optional package for distribution on Splunkbase

# sdata (Splunk Data)

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

## Example
The following is a sample Splunk atom response from a typical Splunk REST API
call. 

<ns0:feed xmlns:ns0="http://www.w3.org/2005/Atom">
  <ns0:title>users</ns0:title>
  <ns0:id>https://192.168.146.148:8089/services/admin/users</ns0:id>
  <ns0:updated>2011-02-26T16:55:59-0800</ns0:updated>
  <ns0:generator version="95725" />
  <ns0:author>
    <ns0:name>Splunk</ns0:name>
  </ns0:author>
  <ns0:link href="/services/admin/users/_new" rel="create" />
  <ns1:totalResults xmlns:ns1="http://a9.com/-/spec/opensearch/1.1/">1</ns1:totalResults>
  <ns1:itemsPerPage xmlns:ns1="http://a9.com/-/spec/opensearch/1.1/">30</ns1:itemsPerPage>
  <ns1:startIndex xmlns:ns1="http://a9.com/-/spec/opensearch/1.1/">0</ns1:startIndex>
  <ns1:messages xmlns:ns1="http://dev.splunk.com/ns/rest" />
  <ns0:entry>
    <ns0:title>admin</ns0:title>
    <ns0:id>https://192.168.146.148:8089/services/admin/users/admin</ns0:id>
    <ns0:updated>2011-02-26T16:55:59-0800</ns0:updated>
    <ns0:link href="/services/admin/users/admin" rel="alternate" />
    <ns0:author>
      <ns0:name>system</ns0:name>
    </ns0:author>
    <ns0:link href="/services/admin/users/admin" rel="list" />
    <ns0:link href="/services/admin/users/admin" rel="edit" />
    <ns0:content type="text/xml">
      <ns1:dict xmlns:ns1="http://dev.splunk.com/ns/rest">
        <ns1:key name="defaultApp">launcher</ns1:key>
        <ns1:key name="defaultAppIsUserOverride">1</ns1:key>
        <ns1:key name="defaultAppSourceRole">system</ns1:key>
        <ns1:key name="eai:acl"><ns1:dict><ns1:key name="app" /><ns1:key name="can_write">1</ns1:key><ns1:key name="modifiable">0</ns1:key><ns1:key name="owner">system</ns1:key><ns1:key name="perms"><ns1:dict><ns1:key name="read"><ns1:list><ns1:item>*</ns1:item></ns1:list></ns1:key><ns1:key name="write"><ns1:list><ns1:item>*</ns1:item></ns1:list></ns1:key></ns1:dict></ns1:key><ns1:key name="sharing">system</ns1:key></ns1:dict></ns1:key>
        <ns1:key name="email">changeme@example.com</ns1:key>
        <ns1:key name="password">********</ns1:key>
        <ns1:key name="realname">Administrator</ns1:key>
        <ns1:key name="roles"><ns1:list><ns1:item>admin</ns1:item></ns1:list></ns1:key>
        <ns1:key name="type">Splunk</ns1:key>
      </ns1:dict>
    </ns0:content>
  </ns0:entry>
</ns0:feed>

# UNDONE
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
* Unify with response handlers in api.py
* Nametable
* Schema "rules"

## splunk/api.py
* Splunk search state machine

# FEEDBACK
* Somewhat unusual convention used for creating resources (eg: _new)
* /services/search/parser response does not use namespaces
* How to read the current priority of a given job?
* /user/admin/users vs. /user/authentication/users
* DELETE /services/data/indexes/<index-name> => 404
* How do I get a list of inputs by index? (instead of pivoted by input kind)
* DELETE /services/apps/local/{name} => 500 if app 'name' does not exist 
* POST /services/authentication/capabilities name=<name> => 404 (verify)
