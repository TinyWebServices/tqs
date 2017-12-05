

import json
import pytest


from test_api import app


@pytest.mark.gen_test(timeout=10)
def test_delete_lease(http_client, base_url):
    # Create a queue
    response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Put a message in it
    response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [{"body": "hello"}]}))
    assert response.code == 200
    # Get the message
    response = yield http_client.fetch(base_url + "/queues/test", raise_error=False, method="GET")
    assert response.code == 200
    j = json.loads(response.body.decode())
    lease_uuid = j["messages"][0]["lease_uuid"]
    # Delete the message
    response = yield http_client.fetch(base_url + "/queues/test/leases/%s" % lease_uuid, raise_error=False, method="DELETE")
    assert response.code == 200
    # Delete the message again
    response = yield http_client.fetch(base_url + "/queues/test/leases/%s" % lease_uuid, raise_error=False, method="DELETE")
    assert response.code == 404


@pytest.mark.gen_test(timeout=10)
def test_delete_lease_404(http_client, base_url):
    # Create a queue
    response = yield http_client.fetch(base_url + "/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Delete a lease - lease does not exist
    response = yield http_client.fetch(base_url + "/queues/test/leases/4b0ea786-838a-4b40-a928-6e146758789b", raise_error=False, method="DELETE")
    assert response.code == 404
    # Delete a lease - queue does not exist
    response = yield http_client.fetch(base_url + "/queues/doesnotexist/leases/4b0ea786-838a-4b40-a928-6e146758789b", raise_error=False, method="DELETE")
    assert response.code == 404
