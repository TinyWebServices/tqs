# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import json, sqlite3, time
import tqs
import pytest
import tornado.gen, tornado.ioloop


#
# Test Fixtures
#

@pytest.fixture
def app(tmpdir):
    # TODO Would be nice to factor this out so that we can just call something in tqs instead
    db = sqlite3.connect(str(tmpdir.join("test.db")))
    db.row_factory = sqlite3.Row
    with open("tqs.sql", "r") as f:
        sql = f.read()
        db.executescript(sql)
    tornado.ioloop.PeriodicCallback(tqs.ExpireLeasesCallback(db), 1000).start() # TODO Is this ok to do here?
    tornado.ioloop.PeriodicCallback(tqs.ExpireMessagesCallback(db), 1000).start() # TODO Is this ok to do here?
    return tqs.TinyQueueServiceApplication(db, None)


#
# Endpoint tests
#

async def test_home(http_server_client):
    response = await http_server_client.fetch("/")
    assert response.code == 200


async def test_version(http_server_client):
    response = await http_server_client.fetch("/version")
    assert response.code == 200
    j = json.loads(response.body.decode())
    for key in ("tag", "branch", "commit"):
        assert key in j




#
# Make sure message order is maintained.
#

async def test_queue_message_order(http_server_client):
    # Create a queue
    response = await http_server_client.fetch("/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Put some message in it
    for n in range(7):
        response = await http_server_client.fetch("/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": str(n)}]}))
        assert response.code == 200
    # Get all messages, see if they come back in same order
    for n in range(7):
        response = await http_server_client.fetch("/queues/test", raise_error=False, method="GET")
        assert response.code == 200
        j = json.loads(response.body.decode())
        assert j["messages"][0]["body"] == str(n)


async def test_authentication(http_server_client, app):
    """Make sure all endpoints are returning a 401"""
    app.api_token = "s3cr3t"
    # GET /queues
    response = await http_server_client.fetch("/queues", raise_error=False, method="GET")
    assert response.code == 401
    # POST /queues
    response = await http_server_client.fetch("/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 401
    # GET /queues/test
    response = await http_server_client.fetch("/queues/test", raise_error=False, method="GET")
    assert response.code == 401
    # DELETE /queues/test
    response = await http_server_client.fetch("/queues/test", raise_error=False, method="DELETE")
    assert response.code == 401
    # POST /queues/test
    response = await http_server_client.fetch("/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": 42}]}))
    assert response.code == 401
    # DELETE /queues/test/leases/36f4d210-a943-4599-b530-7f6ac3e7612e
    response = await http_server_client.fetch("/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": 42}]}))
    assert response.code == 401
