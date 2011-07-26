# The Splunk Software Development Kit for Python

*Welcome to the Splunk SDK for Python!*

This SDK contains library code and examples designed to enable developers to
build applications using Splunk.

Splunk is a search engine and analytic environment that uses a distributed
map-reduce architecture to efficiently index, search and process large 
time-varying data sets.

The Splunk product is popular with system administrators for aggregation and
monitoring of IT machine data, security, compliance and a wide variety of other
scenarios that share a requirement to efficiently index, search, analyze and
generate real-time notifications from large volumes of time series data.

The Splunk developer platform enables developers to take advantage of the same
technology used by the Splunk product to build exciting new applications that
are enabled by Splunk's unique capabilities.

You can learn more about the Splunk developer platform at http://dev.splunk.com

* UNDONE: Note on the preview status of the SDK

## License

The Splunk Software Development Kit for Python is licensed under the Apache
License 2.0. Details can be found in the file LICENSE.

## Getting Started

In order to use the SDK you are going to need a copy of Splunk. If you don't 
already have a copy you can download one from http://www.splunk.com/download.

You can get a copy of the SDK by cloning into the repository with git:

    git clone git@github.com:splunk/splunk-sdk-python.git

#### Installing

You can install the Splunk SDK libraries by running:

    [sudo] python setup.py install

However, it's not necessarry to install the libraries in order to run the
examples and unit tests from the SDK.

#### Requirements

The SDK requires Python 2.6+. 

#### Running the examples and units

In order to run the Splunk examples and unit tests, you must put the root of
the SDK on your PYTHONPATH.

The SDK command line examples require a common set of command line arguments
that specify things like the Splunk host and port and login credentials. You
can get a full list of command line arguments by typing `--help` as an argument
to any of the command line examples. 

#### .splunkrc

The examples and units are also desigend to receive arguments from an optional
`.splunkrc` file located in your home directory. The format of the file is
simply a list of key=value pairs, same as the options that are taken on the
command line, for example:

    host=localhost
    username=admin
    password=changeme

The `.splunkrc` file is a feature of the SDK examples and unit tests and not
the Splunk platform or SDK libraries and is indended simply as convenience for
developers using the SDK. 

The `.splunkrc` file should not be used for storing user credentials for apps
built on Splunk and should not be used if you are concerned about the security
of the credentails used in your development environment.

## Overview

The Splunk developer platform consists of two primary components: `splunkd`, 
the engine and `splunkweb` the app framework that sits on top of the engine
and is used to build the Splunk application.

This SDK enables developers to target `splunkd` by making calls against the
engine's REST API and by accessing the various `splunkd` extension points such
as custom search commands, lookup functions, scripted inputs and custom REST
handlers.

You can find additional information about building applications using the
'splunkweb' framework on the Splunk developer portal at http://dev.splunk.com.

### Hello Splunk

The Splunk library included in this SDK consists of two layers of API that 
can be used to interact with splunkd. The lower layer is referred to as the
_binding_ layer. It is a thin wrapper around low-level HTTP capabilities, 
including:

* A pluggable HTTP component that can be user-supplied.
* Handles authentication and namespace URL management
* Accessible low-level HTTP interface for use by developers who want
    to be close to the wire.

You can see an example use of the library here:

    import splunk.binding as binding

    # host defaults to localhost and port defaults to 8089
    context = binding.connect(username="admin", password="changeme")

    response = context.get('/services/authentication/users')

    print "Status: %s" % response.status
    print response.body.read()

The second layer is referred to as the _client_ layer and builds on the 
_binding_ layer to provide a friendlier interface to Splunk that abstracts away
some of the lower level details of the _binding_ layer.

    from pprint import pprint

    import splunk.client as client

    # host defaults to localhost and port defaults to 8089
    service = client.connect(username="admin", password="changeme")

    for user in service.users:
        pprint(user())

### Unit tests

The SDK contains a small but growing collection of unit tests. Running the
tests is simple and rewarding:

    cd tests
    ./runtests.py

Alternatively, you can read more about our testing "framework" [here](https://github.com/splunk/splunk-sdk-python/tree/master/tests).

### Layout of the repository

<dl>
<dt>./docs</dt>
<dd>Contains a few detailed notes specific to the SDK. In general documentation
    about developing on Splunk can be found on dev.splunk.com.</dd>
<dt>./examples</dt>
<dd>Contains s variety of Splunk samples demonstrating the various library
    modules.</dd>
<dt>./splunk</dt>
<dd>The Splunk library modules.</dd>
<dt>./tests</dt>
<dd>The SDK unit tests.</dd>
<dt>./utils</dt>
<dd>Generic utility code shared by the examples and unit tests.</dd>
</dl>

## Resources

You can find anything having to do with developing on Splunk at the Splunk
developer portal:

* http://dev.splunk.com

Splunk REST API reference documentation: 

* UNDONE

For a gentle introduction to the Splunk product and some of its capabilities:

* http://www.innovato.com/splunk/

## Community

* UNDONE: Mailing list
* UNDONE: Issues
* UNDONE: Answers
* UNDONE: Blog
* UNDONE: Twitter (@splunkdev?)

### How to contribute

We need you to submit a [contributor agreement form] before we can accept your
contributions. The agreement allows us to .. UNDONE

### Support

* UNDONE: no support
* UNDONE: issues should be filed on GitHub Issues 
    (https://github.com/splunk/splunk-sdk-python/issues)

