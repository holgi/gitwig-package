#!/bin/sh

echo
echo "**** pushing changes to bare [Lives's post-commit hook]"
echo

git push <path to hub repository> master

echo "starting website rendering, have a look at gitwig.log"
nohup gitwig-update > gitiwg.log 2>&1 &
