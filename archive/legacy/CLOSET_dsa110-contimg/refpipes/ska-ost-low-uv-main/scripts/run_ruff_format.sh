#!/usr/bin/env bash
#cd ..;
ruff check --select I --fix
ruff format --respect-gitignore --preview --line-length 112

