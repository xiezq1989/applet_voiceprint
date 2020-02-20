#!/bin/sh

#virtualenv-3 .venv
#source .venv/bin/activate
#pip3 install flask
pm2 start -s --name=xiaocx_xvector xiaocx_xvector_v3.py
