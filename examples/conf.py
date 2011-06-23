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

"""An example that shows how to interface with the conf system via the Splunk
   REST API."""

# UNDONE: Finish this example!

import sys

from splunk.binding import *

from utils import cmdopts

def check_status(response, *args):
    """Checks that the given HTTP response is one of the expected values."""
    if response.status not in args:
        raise HTTPError(response.status, response.reason)

class Stanza:
    """Provides a CRUD interface to a .conf file stanza."""
    def __init__(self, context, filename, stanza):
        self.context = context
        self.filename = filename
        self.stanza = stanza
        self.path = "properties/%s/%s" % (filename, stanza)

    def _get(self, path):
        response = self.context.get(path)
        check_status(response, 200)
        return data.load(response.body.read())

    def _post(self, path, **kwargs):
        response = self.context.post(path, **kwargs)
        check_status(response, 200)

    def create(self, **kwargs):
        """Creates the stanza."""
        self._post("properties/%s" % self.filename, __stanza=self.stanza)
        self.update(**kwargs)
        return self

    def delete(self):
        """Deletes the stanza."""
        response = self.context.delete(self.path)
        check_status(response, 200)
        return self

    def ensure(self):
        """Creates the stanza of it does not already exist."""
        if not self.exists(): self.create()
        return self

    def exists(self):
        """Answers if the stanza exists."""
        return self.context.get(self.path).status == 200

    def read(self):
        """Returns the contents of the stanza."""
        content = self._get(self.path).entry
        return dict(
            [(item.title, item.content.get('$text', "")) for item in content])

    def update(self, **kwargs):
        """Updates the contents of the stanza with the given kwargs."""
        if len(kwargs) > 0: self._post(self.path, **kwargs)
        return self

def main(argv):
    pass

if __name__ == "__main__":
    main(sys.argv[1:])

