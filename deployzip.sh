#!/bin/bash

set -e

export DOT_ENV_FILE_PATH=/etc/folderr/appconfig.env
export POETRY_BIN=/home/ubuntu/.local/bin/poetry

sudo systemctl stop folderr
sudo systemctl stop folderr-celery
rm -rf folderr
unzip *.zip
rm -f *.zip
mv folderr-folderr-backend* folderr
sudo cp folderr/command-runners/* /usr/bin
sudo chmod +x /usr/bin/folderr*.sh
sudo cp folderr/systemd/* /etc/systemd/system/
sudo systemctl daemon-reload

cd folderr
$POETRY_BIN env use /home/ubuntu/.pyenv/versions/3.11.4/bin/python
$POETRY_BIN install --with prod
cd app
$POETRY_BIN run python manage.py migrate
$POETRY_BIN run python manage.py collectstatic
sudo systemctl start folderr
sudo systemctl start folderr-celery

unset DOT_ENV_FILE_PATH
