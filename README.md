# The Splunk Software Development Kit for Python

*Welcome to the Splunk SDK for Python!*

This repository contains source code, tools, examples and documentation
designed to enable developers to build applications using the Splunk platform.

<what is Splunk?>

## Status

This project is under active development and its contents will change at will.

## Contents

* splunk: Source code for the splunk package.

* tests: Unit tests for the splunk package

* tools: Command line tools

## Getting Started

In order to run the tools and samples from their respective SDK subdirectories, 
simply place the SDK directory on your PYTHONPATH.

### Get a copy of the SDK

You can get a copy of the sdk by downloading from <here> or by using git
to clone this repository:

`git clone git://github.com/splunk/splunk-sdk-python`

### Get a copy of Splunk

If you dont already have a copy of splunk, you can download it at http://splunk.com

### Running spcmd

...

## Documentation

Proxy support: HTTPS and HTTP proxy is supported by adding proxyhost=<hostname> proxyport=<proxyport> to the CLI (or .splunkrc file) or the **kwargs in the connect API.
               host and port should still continue to address the splunkd server.

Socket timeout: Socket timeout is supported in the following manner:
               If not specified, the system default is used.
               If specified in the connect api **kwargs (timeout=<value>) the initial connection and subsequent get/post/delete/etc operations all use the timeout value.
               If specified on the connect api, individual get/post/delete can be individually overridden by adding timeout=<value>.

<outline of SDK docs and additional resources>

## Community

<how to contact us, issues, answers, etc>

<how to contribute>

