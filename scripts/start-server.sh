#!/bin/bash

set -ex

ARGS=$@

uvicorn app.main:app --host 0.0.0.0 --port 8000 $ARGS
