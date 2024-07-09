#!/bin/bash

export DOT_ENV_FILE_PATH=/etc/folderr/appconfig.env

export APP_DIR=/home/ubuntu/folderr/app

/home/ubuntu/.local/bin/poetry run python $APP_DIR/manage.py update_user_membership
