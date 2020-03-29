import json
import pytest

from test_api import app


async def test_message_priority_sorting(http_server_client):
    # Create a queue
    response = await http_server_client.fetch("/queues", raise_error=False, method="POST", body=json.dumps({"name": "test"}))
    assert response.code == 200
    # Push messages
    for i, priority in enumerate([None, 25, 15, 75, 85, 5, 25, 85, None], start=1):
        message = {"body": str(i)}
        if priority:
            message["priority"] = priority
        response = await http_server_client.fetch("/queues/test", raise_error=False, method="POST", body=json.dumps({"messages": [message]}))
        assert response.code == 200
    # Check if we got them back in the right order
    for body in ("6", "3", "2", "7", "1", "9", "4", "5", "8"):
        response = await http_server_client.fetch("/queues/test", raise_error=False, method="GET")
        assert response.code == 200
        j = json.loads(response.body.decode())
        assert j["messages"][0]["body"] == body
