# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import json, time
import pytest
import tornado.gen, tornado.ioloop

import tqs
from test_api import app


@pytest.mark.gen_test
def test_post_message(http_client, base_url):
    response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": "hello"}]}))
    assert response.code == 200
    response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": []}))
    assert response.code == 200

@pytest.mark.gen_test
def test_post_message_400(http_client, base_url):
    response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    for body in ("", "null", "[]", "{}"):
        response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="POST", body=body)
        assert response.code == 400
    for body in ('{"messages":null}', '{"messages":[1]}', '{"messages":[{}]}', '{"messages":[{"body": null}]}'):
        response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="POST", body=body)
        assert response.code == 400
    for body in ('{"messages":[{"body": "cheese", "delay": null}]}', '{"messages":[{"body": "cheese", "retention": null}]}'):
        response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="POST", body=body)
        assert response.code == 400


@pytest.mark.gen_test
def test_get_message_404(http_client, base_url):
    response = yield http_client.fetch(base_url + "/queues/test", raise_error=False)
    assert response.code == 404


@pytest.mark.gen_test(timeout=10)
def test_message_count(http_client, base_url):
    # Create a queue
    response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Put a number of messages in it
    for n in range(17):
        response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": str(n)}]}))
        assert response.code == 200
    # Get messages
    response = yield http_client.fetch(base_url + "/queues/test?message_count=10", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 10
    # Get remaining messages
    response = yield http_client.fetch(base_url + "/queues/test?message_count=5", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 5
    # Get remaining messages
    response = yield http_client.fetch(base_url + "/queues/test?message_count=5", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 2


@pytest.mark.gen_test(timeout=10)
def test_max_number_of_messages_limit(http_client, base_url):
    # Create a queue
    response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Put a number of messages in it
    for n in range(15):
        response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": str(n)}]}))
        assert response.code == 200
    # Get messages
    response = yield http_client.fetch(base_url + "/queues/test?message_count=20", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 10
    # Get remaining messages
    response = yield http_client.fetch(base_url + "/queues/test?message_count=20", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 5


@pytest.mark.gen_test(timeout=45)
def test_message_delay(http_client, base_url):
    # Create a queue
    response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Put a delayed message in it
    response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": "hello", "delay": 7}]}))
    assert response.code == 200
    # Get the message - should not show up
    response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 0
    # Wait for timeout
    time.sleep(7)
    # Get the message - should be available
    response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 1
    # Let the lease expire
    time.sleep(tqs.DEFAULT_VISIBILITY_TIMEOUT+1)
    # Get the message - should be there, not using delay
    response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 1

@pytest.mark.gen_test(timeout=90)
def test_message_retention(http_client, base_url):
    # Create a queue
    response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Put a message in it in with a 60 second retention
    response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": "hello", "retention": 60}]}))
    assert response.code == 200
    # Wait for the message to expire
    time.sleep(tqs.MIN_MESSAGE_RETENTION)
    # Get the message - should not show up
    response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 0


@pytest.mark.gen_test(timeout=45)
def test_visibility_timeout(http_client, base_url):
    # Create a queue
    response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Put a message in it
    response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": "cheese"}]}))
    assert response.code == 200
    # Get a message
    response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 1
    # Get a message again
    response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 0
    # Let the lease expire
    yield tornado.gen.sleep(tqs.DEFAULT_VISIBILITY_TIMEOUT + 1)
    # Get a message again
    response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 1

@pytest.mark.gen_test(timeout=45)
def test_message_delete_immediately(http_client, base_url, app):
    # Create a queue
    response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Put a message in it
    response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": "cheese"}]}))
    assert response.code == 200
    # Get a message
    response = yield http_client.fetch(base_url + "/queues/test?delete=1", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 1
    # Get a message again
    response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 0
    # Let the lease expire
    yield tornado.gen.sleep(tqs.DEFAULT_VISIBILITY_TIMEOUT + 1)
    # Get a message again - should not be there, even though we did not delete the lease
    response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert len(j["messages"]) == 0


@pytest.mark.gen_test(timeout=10)
def test_message_body_types(http_client, base_url, app):
    # Create a queue
    response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Try to queue messages with an invalid body
    for body in (list(), dict(), float(), int()):
        # Put a message in it
        response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": body}]}))
        assert response.code == 400

@pytest.mark.gen_test(timeout=10)
def test_message_body_type(http_client, base_url, app):
    for i, body_type in enumerate(tqs.VALID_BODY_TYPES):
        # Create a queue
        response = yield http_client.fetch(f"{base_url}/queues", raise_error=False, method="POST",
                                           body=json.dumps({"name": f"test{i}"}))
        assert response.code == 200
        # Put a message in it
        response = yield http_client.fetch(f"{base_url}/queues/test{i}", raise_error=False, method="POST",
                                           body=json.dumps({"messages": [{"body": "cheese", "type": body_type}]}))
        assert response.code == 200
        # Get a message
        response = yield http_client.fetch(f"{base_url}/queues/test{i}", raise_error=False, method="GET")
        assert response.code == 200
        j = json.loads(response.body.decode())
        print(j)
        assert len(j["messages"]) == 1
        assert j["messages"][0]["body"] == "cheese"
        assert j["messages"][0]["type"] == body_type


@pytest.mark.gen_test(timeout=10)
def test_message_body_encoding(http_client, base_url, app):
    # Create a queue
    response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Push a message
    for body in (json.dumps({"foo": "bar"}), "-this-is-not-json-", "multiple\nlines\nare\ncool\n"):
        response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": body}]}))
        assert response.code == 200
        response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="GET")
        assert response.code == 200
        j = json.loads(response.body.decode())
        assert len(j["messages"]) == 1
        assert j["messages"][0]["body"] == body
