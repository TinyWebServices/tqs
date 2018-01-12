# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import tqs


def test_lease_name():
    assert tqs.validate_lease_name("") == False
    assert tqs.validate_lease_name("f7e35c26-c2aa-49a0-93b6-bf5a6ad6a16c") == True
    assert tqs.validate_lease_name("F7E35C26-C2AA-49A0-93B6-BF5A6AD6A16C") == False

def test_validate_queue_name():
    assert tqs.validate_queue_name("") == False
    assert tqs.validate_queue_name("a" * tqs.MIN_QUEUE_NAME_LEN) == True
    assert tqs.validate_queue_name("a" * (tqs.MIN_QUEUE_NAME_LEN-1)) == False
    assert tqs.validate_queue_name("a" * tqs.MAX_QUEUE_NAME_LEN) == True
    assert tqs.validate_queue_name("a" * (tqs.MAX_QUEUE_NAME_LEN+1)) == False
    assert tqs.validate_queue_name("a-a-a")
    assert tqs.validate_queue_name("a_a_a")
    assert tqs.validate_queue_name("-aa_aa_aa") == False
    assert tqs.validate_queue_name("aa_aa_aa-") == False
    assert tqs.validate_queue_name("_aa_aa_aa") == False
    assert tqs.validate_queue_name("aa_aa_aa_") == False

def test_validate_visibility_timeout():
    assert tqs.validate_visibility_timeout("10") == False
    assert tqs.validate_visibility_timeout(10.0) == False
    assert tqs.validate_visibility_timeout(tqs.MIN_VISIBILITY_TIMEOUT) == True
    assert tqs.validate_visibility_timeout(tqs.MIN_VISIBILITY_TIMEOUT - 1) == False
    assert tqs.validate_visibility_timeout(tqs.MAX_VISIBILITY_TIMEOUT) == True
    assert tqs.validate_visibility_timeout(tqs.MAX_VISIBILITY_TIMEOUT + 1) == False
    assert tqs.validate_visibility_timeout(tqs.DEFAULT_VISIBILITY_TIMEOUT) == True
    assert tqs.validate_visibility_timeout(10) == True
    assert tqs.validate_visibility_timeout(-10) == False

def test_validate_message_count():
    assert tqs.validate_message_count("5") == False
    assert tqs.validate_message_count(5.0) == False
    assert tqs.validate_message_count(tqs.MIN_MESSAGE_COUNT) == True
    assert tqs.validate_message_count(tqs.MIN_MESSAGE_COUNT - 1) == False
    assert tqs.validate_message_count(tqs.MAX_MESSAGE_COUNT) == True
    assert tqs.validate_message_count(tqs.MAX_MESSAGE_COUNT + 1) == False
    assert tqs.validate_message_count(5) == True
    assert tqs.validate_message_count(-5) == False

def test_validate_message_delay():
    assert tqs.validate_message_delay("5") == False
    assert tqs.validate_message_delay(5.0) == False
    assert tqs.validate_message_delay(tqs.MIN_MESSAGE_DELAY) == True
    assert tqs.validate_message_delay(tqs.MIN_MESSAGE_DELAY - 1) == False
    assert tqs.validate_message_delay(tqs.MAX_MESSAGE_DELAY) == True
    assert tqs.validate_message_delay(tqs.MAX_MESSAGE_DELAY + 1) == False
    assert tqs.validate_message_delay(tqs.DEFAULT_MESSAGE_DELAY) == True
    assert tqs.validate_message_delay(tqs.DEFAULT_MESSAGE_DELAY + 1) == True
    assert tqs.validate_message_delay(5) == True
    assert tqs.validate_message_delay(-5) == False

def test_validate_message_retention():
    assert tqs.validate_message_retention("5") == False
    assert tqs.validate_message_retention(5.0) == False
    assert tqs.validate_message_retention(tqs.MIN_MESSAGE_RETENTION) == True
    assert tqs.validate_message_retention(tqs.MIN_MESSAGE_RETENTION - 1) == False
    assert tqs.validate_message_retention(tqs.MAX_MESSAGE_RETENTION) == True
    assert tqs.validate_message_retention(tqs.MAX_MESSAGE_RETENTION + 1) == False
    assert tqs.validate_message_retention(tqs.DEFAULT_MESSAGE_RETENTION) == True
    assert tqs.validate_message_retention(tqs.DEFAULT_MESSAGE_RETENTION+1) == True
    assert tqs.validate_message_retention(-5) == False

def test_validate_message_body():
    assert tqs.validate_message_body("") == True
    assert tqs.validate_message_body("X" * tqs.MAX_BODY_LEN) == True
    assert tqs.validate_message_body("X" * (tqs.MAX_BODY_LEN+1)) == False
    assert tqs.validate_message_body(10) == False
    assert tqs.validate_message_body(10.0) == False
    assert tqs.validate_message_body([]) == False
    assert tqs.validate_message_body({}) == False

def test_validate_message_type():
    for message_type in (None, "", "foo", 1, 3.14, [], {}):
        assert tqs.validate_message_type(message_type) == False
    for message_type in tqs.VALID_BODY_TYPES:
        assert tqs.validate_message_type(message_type) == True

def test_validate_message_piority():
    assert tqs.validate_message_priority("5") == False
    assert tqs.validate_message_priority(5.0) == False
    assert tqs.validate_message_priority(tqs.MIN_MESSAGE_PRIORITY) == True
    assert tqs.validate_message_priority(tqs.MIN_MESSAGE_PRIORITY - 1) == False
    assert tqs.validate_message_priority(tqs.MAX_MESSAGE_PRIORITY) == True
    assert tqs.validate_message_priority(tqs.MAX_MESSAGE_PRIORITY + 1) == False
    assert tqs.validate_message_priority(tqs.DEFAULT_MESSAGE_PRIORITY) == True
    assert tqs.validate_message_priority(tqs.DEFAULT_MESSAGE_PRIORITY+1) == True
    assert tqs.validate_message_priority(-5) == False
