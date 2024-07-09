#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

# python manage.py flush --no-input
python manage.py migrate --no-input
python manage.py collectstatic --no-input --clear
# python manage.py loaddata core/fixtures/superuser.json --app core.user
# python manage.py loaddata filemanager/fixtures/FolderType.json --app filemanager.foldertype

exec "$@"