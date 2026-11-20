#!/bin/bash
# Start an isolated session; do not source into the login shell.
set -eu
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
exec /bin/bash "$root/scripts/start-test"
