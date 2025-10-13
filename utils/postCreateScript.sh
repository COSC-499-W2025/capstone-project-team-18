#!/usr/bin/env bash

# This file will be run when the devcontainer is created for the first time, and never again.

# Update pip and install all package dependencies
pip install --upgrade pip
pip install -r requirements.txt
