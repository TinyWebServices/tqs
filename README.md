# Tiny Queue Service (Server)

_Stefan Arentz, December 2017_

![Build & Test](https://github.com/TinyWebServices/tqs-server/workflows/.github/workflows/main.yml/badge.svg) ![Publish](https://github.com/TinyWebServices/tqs-server/workflows/.github/workflows/publish.yml/badge.svg) [![codecov](https://codecov.io/gh/st3fan/tqs-server/branch/master/graph/badge.svg)](https://codecov.io/gh/st3fan/tqs-server) [![Lintly](https://lintly.com/gh/st3fan/tqs-server/badge.svg)](https://lintly.com/gh/st3fan/tqs-server/)

Tiny Queue Service (TQS) is a small pragmatic queue service with
modest performance that you can self host.

If the following sounds good to you then this project may be
compatible with your needs:

- Very easy to deploy via Docker
- Most operations take a few milliseconds on modest hardware, so a single instance can usually handle hundreds of queue operations per second
- Simple REST API that lets you GET and POST messages
- (Optional) Simple authentication via pre configured API keys
- Zero configuration. Run and go.
- No broker topology, no redundancy, no enterprise features.

This project was inspired by Redis and Amazon's Simple Queue Service.

## Two Minute Demo

TODO Python Code TODO

## Installation via Docker

Either pull the latest stable version from the Docker Hub:

```
docker pull tqs-server:latest
```

Or build your own copy from source:

```
git clone https://github.com/st3fan/tqs-server.git
cd tqs-server
docker build -t tqs-server:latest .
```

If you want to see how this works, run it in the foreground with the database in `/tmp/tqs` and no authentication:

```
docker run --rm -v /tmp/tqs:/data/tqs  -p 8080:8080 tqs-server:latest
```

To start an instance in the background:

```
docker run -d -v /var/lib/tqs:/data/tqs -e API_TOKEN=YourSecretToken -p 8080:8080 tqs-server:latest
```

This will make a TQS instance available on host port 8080 and store
the database file in `var/lib/tqs`.

If you expose TQS publicly (or even via say an internal Digital Ocean
or AWS address), it is highly recommended that you set an
`TQS_API_TOKEN` and put an SSL enabled server like Caddy in front of
it.

## Development

Basically the following:

```
git clone https://github.com/st3fan/tqs-server.git
cd tqs-server
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
python tqs.py --logging=debug
```

Tornado auto reloads the code on change so you can hack away and see your changes on save.

### Running tests

```
source env/bin/activate
pip install pytest pytest-tornasync
pytest
```

## Design Notes

This service is built in Python on top of Tornado and SQLite. Tornado
and SQLite are a good match; because of Tornado's asynchronous single
thread model, there is a strong guarantee that all database operations
are executed serially. This is a speed compromise to get a simple
design.

Speed, other than "reasonable", was never a goal for this project. If
you need to go crazy fast then this may not be the right project for
you. Redis may then be a better solution.

## Benchmarks

Here are some performance numbers for the available API endpoints:

TODO Some Numbers TODO

These tests were run on a small Digital Ocean instance (512 MB).

Note that I do not have numbers to compare against. I simply do not
care about that. This project was created because I was unable to find
something simple to fit my needs and not to compete with other solutions.
