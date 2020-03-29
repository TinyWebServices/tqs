# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import json, time
import pytest
import tornado.gen, tornado.ioloop

import tqs
from test_api import app


async def test_post_message(http_server_client):
    response = await http_server_client.fetch("/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    response = await http_server_client.fetch("/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": "hello"}]}))
    assert response.code == 200
    response = await http_server_client.fetch("/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": []}))
    assert response.code == 200

async def test_post_message_400(http_server_client):
    response = await http_server_client.fetch("/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    for body in ("", "null", "[]", "{}"):
        response = await http_server_client.fetch("/queues/test", raise_error=False, method="POST", body=body)
        assert response.code == 400
    for body in ('{"messages":null}', '{"messages":[1]}', '{"messages":[{}]}', '{"messages":[{"body": null}]}'):
        response = await http_server_client.fetch("/queues/test", raise_error=False, method="POST", body=body)
        assert response.code == 400
    for body in ('{"messages":[{"body": "cheese", "delay": null}]}', '{"messages":[{"body": "cheese", "retention": null}]}'):
        response = await http_server_client.fetch("/queues/test", raise_error=False, method="POST", body=body)
        assert response.code == 400


async def test_get_message_404(http_server_client):
    response = await http_server_client.fetch("/queues/test", raise_error=False)
    assert response.code == 404


async def test_message_count(http_server_client):
    # Create a queue
    response = await http_server_client.fetch("/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Put a number of messages in it
    for n in range(17):
        response = await http_server_client.fetch("/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": str(n)}]}))
        assert response.code == 200
    # Get messages
    response = await http_server_client.fetch("/queues/test?message_count=10", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 10
    # Get remaining messages
    response = await http_server_client.fetch("/queues/test?message_count=5", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 5
    # Get remaining messages
    response = await http_server_client.fetch("/queues/test?message_count=5", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 2


async def test_max_number_of_messages_limit(http_server_client):
    # Create a queue
    response = await http_server_client.fetch("/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Put a number of messages in it
    for n in range(tqs.MAX_MESSAGE_COUNT+1):
        response = await http_server_client.fetch("/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": str(n)}]}))
        assert response.code == 200
    # Get messages
    count = tqs.MAX_MESSAGE_COUNT+1
    response = await http_server_client.fetch("/queues/test?message_count=%d" % count, raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == tqs.MAX_MESSAGE_COUNT
    # Get remaining messages
    count = tqs.MAX_MESSAGE_COUNT
    response = await http_server_client.fetch("/queues/test?message_count=%d" % count, raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 1


async def test_message_delay(http_server_client):
    # Create a queue
    response = await http_server_client.fetch("/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Put a delayed message in it
    response = await http_server_client.fetch("/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": "hello", "delay": 7}]}))
    assert response.code == 200
    # Get the message - should not show up
    response = await http_server_client.fetch("/queues/test", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 0
    # Wait for timeout
    time.sleep(7)
    # Get the message - should be available
    response = await http_server_client.fetch("/queues/test", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 1
    # Let the lease expire
    time.sleep(tqs.DEFAULT_VISIBILITY_TIMEOUT+1)
    # Get the message - should be there, not using delay
    response = await http_server_client.fetch("/queues/test", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 1

async def test_message_retention(http_server_client):
    # Create a queue
    response = await http_server_client.fetch("/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Put a message in it in with a 60 second retention
    response = await http_server_client.fetch("/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": "hello", "retention": 60}]}))
    assert response.code == 200
    # Wait for the message to expire
    time.sleep(tqs.MIN_MESSAGE_RETENTION)
    # Get the message - should not show up
    response = await http_server_client.fetch("/queues/test", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 0


async def test_visibility_timeout(http_server_client):
    # Create a queue
    response = await http_server_client.fetch("/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Put a message in it
    response = await http_server_client.fetch("/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": "cheese"}]}))
    assert response.code == 200
    # Get a message
    response = await http_server_client.fetch("/queues/test", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 1
    # Get a message again
    response = await http_server_client.fetch("/queues/test", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 0
    # Let the lease expire
    await tornado.gen.sleep(tqs.DEFAULT_VISIBILITY_TIMEOUT + 1)
    # Get a message again
    response = await http_server_client.fetch("/queues/test", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 1

async def test_message_delete_immediately(http_server_client, app):
    # Create a queue
    response = await http_server_client.fetch("/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Put a message in it
    response = await http_server_client.fetch("/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": "cheese"}]}))
    assert response.code == 200
    # Get a message
    response = await http_server_client.fetch("/queues/test?delete=1", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 1
    # Get a message again
    response = await http_server_client.fetch("/queues/test", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 0
    # Let the lease expire
    await tornado.gen.sleep(tqs.DEFAULT_VISIBILITY_TIMEOUT + 1)
    # Get a message again - should not be there, even though we did not delete the lease
    response = await http_server_client.fetch("/queues/test", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 0


async def test_message_body_types(http_server_client, app):
    # Create a queue
    response = await http_server_client.fetch("/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Try to queue messages with an invalid body
    for body in (list(), dict(), float(), int()):
        # Put a message in it
        response = await http_server_client.fetch("/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": body}]}))
        assert response.code == 400

async def test_message_body_type(http_server_client, app):
    for i, body_type in enumerate(tqs.VALID_BODY_TYPES):
        # Create a queue
        response = await http_server_client.fetch("/queues", raise_error=False, method="POST",
                                           body=json.dumps({"name": f"test{i}"}))
        assert response.code == 200
        # Put a message in it
        response = await http_server_client.fetch(f"/queues/test{i}", raise_error=False, method="POST",
                                           body=json.dumps({"messages": [{"body": "cheese", "type": body_type}]}))
        assert response.code == 200
        # Get a message
        response = await http_server_client.fetch(f"/queues/test{i}", raise_error=False, method="GET")
        assert response.code == 200
        j = json.loads(response.body.decode())
        print(j)
        assert len(j["messages"]) == 1
        assert j["messages"][0]["body"] == "cheese"
        assert j["messages"][0]["type"] == body_type


async def test_message_body_encoding(http_server_client, app):
    # Create a queue
    response = await http_server_client.fetch("/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Push a message
    for body in (json.dumps({"foo": "bar"}), "-this-is-not-json-", "multiple\nlines\nare\ncool\n"):
        response = await http_server_client.fetch("/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": body}]}))
        assert response.code == 200
        response = await http_server_client.fetch("/queues/test", raise_error=False, method="GET")
        assert response.code == 200
        j = json.loads(response.body.decode())
        assert len(j["messages"]) == 1
        assert j["messages"][0]["body"] == body
