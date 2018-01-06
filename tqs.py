# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import os, re, sys, sqlite3, time, uuid

from tornado.gen import coroutine, sleep
from tornado.web import Application, RequestHandler, URLSpec
from tornado import httpserver
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.escape import json_decode
from tornado.options import parse_command_line, options, define
from tornado.httpserver import HTTPServer


MIN_QUEUE_NAME_LEN = 1
MAX_QUEUE_NAME_LEN = 80
QUEUE_NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-_]*[a-z0-9]+)*$", re.IGNORECASE)

def validate_queue_name(v):
    return type(v) == str and len(v) >= MIN_QUEUE_NAME_LEN and len(v) <= MAX_QUEUE_NAME_LEN and QUEUE_NAME_RE.match(v) is not None


LEASE_NAME_RE = re.compile(r"^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$")

def validate_lease_name(v):
    return type(v) == str and LEASE_NAME_RE.match(v) is not None


DEFAULT_VISIBILITY_TIMEOUT = 30
MIN_VISIBILITY_TIMEOUT = 5
MAX_VISIBILITY_TIMEOUT = 43200

def validate_visibility_timeout(v):
    return type(v) == int and v >= MIN_VISIBILITY_TIMEOUT and v <= MAX_VISIBILITY_TIMEOUT

DEFAULT_MESSAGE_DELAY = 0
MIN_MESSAGE_DELAY = 0
MAX_MESSAGE_DELAY = 900

def validate_message_delay(v):
    return type(v) == int and v >= MIN_MESSAGE_DELAY and v <= MAX_MESSAGE_DELAY


DEFAULT_MESSAGE_RETENTION = (4 * 24 * 60 * 60)
MIN_MESSAGE_RETENTION = 60
MAX_MESSAGE_RETENTION = (14 * 24 * 60 * 60)

def validate_message_retention(v):
    return type(v) == int and v >= MIN_MESSAGE_RETENTION and v <= MAX_MESSAGE_RETENTION


DEFAULT_MESSAGE_COUNT = 1
MIN_MESSAGE_COUNT = 1
MAX_MESSAGE_COUNT = 100

def validate_message_count(v):
    return type(v) == int and v >= MIN_MESSAGE_COUNT and v <= MAX_MESSAGE_COUNT


MAX_BODY_LEN = 4096

def validate_message_body(v):
    return type(v) == str and len(v) <= MAX_BODY_LEN


DEFAULT_BODY_TYPE = "text/plain"
VALID_BODY_TYPES = ["text/plain", "application/json", "application/octet-stream"]

def validate_message_type(v):
    return type(v) == str and v in VALID_BODY_TYPES


DEFAULT_DELETE = False

def validate_delete(v):
    return v in ("1", "true", "yes")


DEFAULT_WAIT_TIME = 0
MIN_WAIT_TIME = 0
MAX_WAIT_TIME = 60

def validate_wait_time(v):
    return type(v) == int and v >= MIN_WAIT_TIME and v <= MAX_WAIT_TIME


#
# HomeHandler
#

class HomeHandler(RequestHandler):

    def get(self):
        self.write("<h1>Hello, world!</h1>")


#
# VersionHandler
#

class VersionHandler(RequestHandler):

    def get(self):
        self.write({"branch": "", "tag": "", "commit": ""})

#
# BaseHandler
#

class BaseHandler(RequestHandler):
    def prepare(self):
        if self.application.api_token and self.request.headers.get("Authentication") != "token " + self.application.api_token:
            self.send_error(401)


#
# QueuesHandler
#

class QueuesHandler(BaseHandler):

    #
    # Get a list of all available queues
    #

    def get(self):
        c = self.application.db.cursor()
        c.execute("select name, create_date, insert_count, delete_count, expire_count from queues order by create_date")
        queues = [{"name": queue["name"],
                   "create_date": queue["create_date"],
                   "insert_count": queue["insert_count"],
                   "delete_count": queue["delete_count"],
                   "expire_count": queue["expire_count"]}
                  for queue in c.fetchall()]
        self.write({"queues": queues})

    #
    # Create a new queue
    #

    def post(self):
        try:
            if not self.request.body:
                self.send_error(400)
                return
            data = json_decode(self.request.body)
            if type(data) != dict or "name" not in data or not validate_queue_name(data["name"]):
                self.send_error(400)
                return
        except Exception as e:
            self.send_error(400)
            return

        try:
            with self.application.db:
                c = self.application.db.cursor()
                c.execute("insert into queues (create_date, name) values (?, ?)", [time.time(), data["name"]])
                self.write("{}")
        except sqlite3.IntegrityError as e:
            self.send_error(409)

#
# Queue API
#

class QueueHandler(BaseHandler):

    def prepare(self):
        super().prepare()
        with self.application.db as db:
            c = db.cursor()
            c.execute("select id, name from queues where name = ?", [self.path_args[0]])
            self.queue = c.fetchone()
            if not self.queue:
                self.send_error(404)

    @coroutine
    def get(self, queue_name):
        with self.application.db:
            c = self.application.db.cursor()

            # Parse parameters (message_count, visibility_timeout)
            delete = self.get_argument("delete", DEFAULT_DELETE) # TODO Why do we have validate_delete?
            message_count = min(int(self.get_argument("message_count", DEFAULT_MESSAGE_COUNT)), MAX_MESSAGE_COUNT)
            visibility_timeout = min(int(self.get_argument("visibilty_timeout", DEFAULT_VISIBILITY_TIMEOUT)), MAX_VISIBILITY_TIMEOUT)
            wait_time = min(int(self.get_argument("wait_time", DEFAULT_WAIT_TIME)), MAX_WAIT_TIME)

            # Select messages that we can return

            rows = []
            deadline = time.time() + wait_time

            while True:
                now = time.time()
                c.execute("select id from messages where queue_id = ? and lease_date is null and visible_date <= ? and expire_date >= ? order by create_date asc limit ?",
                          (self.queue["id"], now, now, message_count))
                rows = c.fetchall() # TODO Another case of this api being too smart
                if now > deadline or rows:
                    break
                if wait_time != 0:
                    yield sleep(0.25)

            if not rows:
                self.write({"messages": []})
                return

            message_ids = [row["id"] for row in rows]

            # Update the lease for these messages
            if not delete:
                for message_id in message_ids:
                    lease_uuid = str(uuid.uuid4())
                    c.execute("update messages set lease_date = ?, lease_uuid = ?, lease_timeout = ? where id = ?",
                              [time.time(), lease_uuid, visibility_timeout, message_id])

            # Return messages
            if not delete:
                c.execute("select id, create_date, body, type, lease_date, expire_date, lease_uuid, lease_timeout from messages where id in (%s)" % ",".join("?" * len(message_ids)), message_ids)
                messages = [{"id": message["id"],
                             "create_date": message["create_date"],
                             "visible_date": message["create_date"],
                             "expire_date": message["expire_date"],
                             "body": message["body"],
                             "type": message["type"],
                             "lease_date": message["lease_date"],
                             "lease_uuid": message["lease_uuid"],
                             "lease_timeout": message["lease_timeout"]}
                            for message in c.fetchall()]
            else:
                c.execute("select id, create_date, body, type, expire_date from messages where id in (%s)" % ",".join("?" * len(message_ids)), message_ids)
                messages = [{"id": message["id"],
                             "create_date": message["create_date"],
                             "visible_date": message["create_date"],
                             "expire_date": message["expire_date"],
                             "body": message["body"],
                             "type": message["type"]}
                            for message in c.fetchall()]
                c.execute("delete from messages where id in (%s)" % ",".join("?" * len(message_ids)), message_ids)

            self.write({"messages": messages})

    #
    # Add messages to a queue
    #
    # { "messages": [{"body": "", "delay": 5}, ...] }
    #

    def post(self, queue_name):
        with self.application.db as db:
            # Verify incoming data
            try:
                data = json_decode(self.request.body)
                if type(data) != dict or "messages" not in data or type(data["messages"]) != list:
                    self.send_error(400) # TODO Explain
                    return
                for message in data["messages"]:
                    if type(message) != dict:
                        self.send_error(400) # TODO Explain
                        return
                    if "body" not in message or type(message["body"]) != str or not validate_message_body(message["body"]):
                        self.send_error(400) # TODO Explain
                        return
                    if "type" in message:
                        if type(message["type"]) != str or not validate_message_type(message["type"]):
                            self.send_error(400) # TODO Explain
                            return
                    if "delay" in message and not validate_message_delay(message["delay"]):
                        self.send_error(400) # TODO Explain
                        return
                    if "retention" in message and not validate_message_retention(message["retention"]):
                        self.send_error(400) # TODO Explain
                        return
            except Exception as e:
                self.send_error(400) # TODO Explain
                return

            # No messages is not considered an error
            if len(data["messages"]) == 0:
                self.write({})
                return

            # Push all messages into the queue
            for message in data["messages"]:
                now = time.time()
                delay = message.get("delay", DEFAULT_MESSAGE_DELAY)
                retention = message.get("retention", DEFAULT_MESSAGE_RETENTION)
                db.execute("insert into messages (create_date, visible_date, expire_date, queue_id, body, type) values (?, ?, ?, ?, ?, ?)",
                           [now, now + delay, now + retention, self.queue["id"], message["body"], message.get("type", DEFAULT_BODY_TYPE)])

            # Increment the count
            db.execute("update queues set insert_count = insert_count + ? where id = ?", [len(data["messages"]), self.queue["id"]])
            self.write({}) # TODO What is useful to return here?

    #
    # Delete a queue and all its messages. We depend on cascading
    # deletes so deleting just the queue is enough here.
    #

    def delete(self, queue_name):
        with self.application.db:
            cursor = self.application.db.cursor()
            cursor.execute("delete from queues where name = ?", (queue_name,))
            if cursor.rowcount == 0:
                self.send_error(404)
                return
            self.write("{}")


class LeasesHandler(BaseHandler):

    def prepare(self):
        super().prepare()
        with self.application.db as db:
            c = db.cursor()
            c.execute("select id, name from queues where name = ?", (self.path_args[0],))
            self.queue = c.fetchone()
            if not self.queue:
                self.send_error(404)

    def delete(self, queue_name, lease_uuid):
        with self.application.db as db:
            c = db.cursor()
            c.execute("delete from messages where queue_id = ? and lease_uuid = ?", [self.queue["id"], lease_uuid])
            if c.rowcount == 0:
                self.send_error(404)
                return
            self.write("{}")


class TinyQueueServiceApplication(Application):

    def __init__(self, db, api_token):
        self.db = db
        self.api_token = api_token
        handlers = [
            # TODO Make regexps below more strict
            URLSpec(r"/", HomeHandler),
            URLSpec(r"/version", VersionHandler),
            URLSpec(r"/queues", QueuesHandler),
            URLSpec(r"/queues/([a-zA-Z0-9](?:[a-zA-Z0-9-_]*[a-zA-Z0-9]+)*)/leases/([a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12})", LeasesHandler),
            URLSpec(r"/queues/([a-zA-Z0-9](?:[a-zA-Z0-9-_]*[a-zA-Z0-9]+)*)", QueueHandler),
        ]
        settings = {
            "template_path": os.path.join(os.path.dirname(__file__), "templates"),
            "static_path": os.path.join(os.path.dirname(__file__), "static")
        }
        Application.__init__(self, handlers, **settings)


#
# ExpireLeasesCallback
#

class ExpireLeasesCallback:

    def __init__(self, db):
        self.db = db

    def __call__(self):
        with self.db:
            self.db.execute("update messages set lease_date = null, lease_uuid = null, lease_timeout = null where (lease_date + lease_timeout) < ?", [time.time()])


#
# ExpireMessagesCallback runs periodically to delete expired messages.
#

class ExpireMessagesCallback:

    def __init__(self, db):
        self.db = db

    def __call__(self):
        with self.db:
            self.db.execute("delete from messages where lease_date is null and expire_date < ?", [time.time()])


define("port", default=os.getenv("TQS_PORT", "8080"), help="run on the given port", type=int)
define("database", default=os.getenv("TQS_DATABASE", "/data/tqs/tqs.sqlite3"), help="database path", type=str)
define("api-token", default=os.getenv("TQS_API_TOKEN", None), help="api token", type=str)


if __name__ == "__main__":
    parse_command_line()

    db = sqlite3.connect(options.database)
    db.row_factory = sqlite3.Row
    with open("tqs.sql", "r") as f:
        sql = f.read()
        db.executescript(sql)

    app = TinyQueueServiceApplication(db, options.api_token)

    server = HTTPServer(app)
    server.listen(options.port)

    # These do not have to be super accurate
    PeriodicCallback(ExpireLeasesCallback(db), 2500).start()
    PeriodicCallback(ExpireMessagesCallback(db), 15000).start()

    IOLoop.current().start()
