# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import json
import pytest
from test_api import app


@pytest.mark.gen_test
def test_create_queue(http_client, base_url):
    response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 409


@pytest.mark.gen_test
def test_create_queue_validation(http_client, base_url):
    for body in ("", "cheese", "123", "{}", "[]", '{"name": 42}', '{"name": []}', '{"name": {}}', '{"name": null}', '{"name": ""}', "null"):
        response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="POST", body=body)
        assert response.code == 400
    for queue_name in ("", "-cheese-", "cheese-", "-cheese", "Foo%$"):
        response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="POST", body=json.dumps({"name": queue_name}))
        assert response.code == 400


@pytest.mark.gen_test
def test_list_queues(http_client, base_url):
    # Create two queues
    for queue_name in ("foo", "bar"):
        response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="POST", body=json.dumps({"name": queue_name}))
        assert response.code == 200
    # Make sure we have two queues
    response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert "queues" in j
    assert len(j["queues"]) == 2
    assert j["queues"][0]["name"] == "foo"
    assert "create_date" in j["queues"][0]
    assert j["queues"][1]["name"] == "bar"
    assert "create_date" in j["queues"][1]


@pytest.mark.gen_test
def test_delete_queue(http_client, base_url):
    # Create a queue
    response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Make sure we have one queue
    response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert "queues" in j
    assert len(j["queues"]) == 1
    # Delete the queue
    response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="DELETE")
    assert response.code == 200
    # Make sure we have no queues
    response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    assert "queues" in j
    assert len(j["queues"]) == 0
    # Try to delete it again
    response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="DELETE")
    assert response.code == 404


@pytest.mark.gen_test
def test_delete_queue_404(http_client, base_url):
    response = yield http_client.fetch(base_url + "/queues/doesnotexist", raise_error=False, method="DELETE")
    assert response.code == 404
