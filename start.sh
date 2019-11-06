#!/bin/bash

if [ -f ".env" ]; then
    export $(cat .env | xargs)
fi

python3 new_worker.py
