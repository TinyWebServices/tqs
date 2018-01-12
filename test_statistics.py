# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import json
import pytest

from test_api import app


@pytest.mark.gen_test
def test_statistics(http_client, base_url):
    # Create some queues
    for queue_name in ("foo", "foo-jobs", "foo-results"):
        r = yield http_client.fetch(base_url + "/queues", raise_error=False, method="POST", body=json.dumps({"name": queue_name}))
        assert r.code == 200
    # Get the statistics
    r = yield http_client.fetch(base_url + "/statistics", raise_error=False, method="GET")
    assert r.code == 200
    j = json.loads(r.body.decode())
    # Make sure all the queues are in there
    for queue_name in ("foo", "foo-jobs", "foo-results"):
        assert queue_name in j
        # Make sure all the stats are in there
        for f in ("visible", "leased", "delayed"):
            assert f in j[queue_name]
            assert type(j[queue_name][f]) == int

@pytest.mark.gen_test
def test_queue_statistics(http_client, base_url):
    # Create some queues
    for queue_name in ("foo", "foo-jobs", "foo-results"):
        r = yield http_client.fetch(base_url + "/queues", raise_error=False, method="POST", body=json.dumps({"name": queue_name}))
        assert r.code == 200
    # Get the statistics
    for queue_name in ("foo", "foo-jobs", "foo-results"):
        r = yield http_client.fetch(base_url + "/queues/" + queue_name + "/statistics", raise_error=False, method="GET")
        assert r.code == 200
        j = json.loads(r.body.decode())
        # Make sure all the stats are in there
        for f in ("visible", "leased", "delayed"):
            assert f in j
            assert type(j[f]) == int
