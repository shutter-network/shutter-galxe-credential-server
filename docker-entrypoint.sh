#!/bin/sh

set -e

. /venv/bin/activate

exec gunicorn --bind 0.0.0.0:5000 --forwarded-allow-ips='*' shutter_galxe_credential_server.main:create_app\(\)
