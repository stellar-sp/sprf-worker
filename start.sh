#!/bin/bash

export $(cat .env | xargs)

python3 new_worker.py
