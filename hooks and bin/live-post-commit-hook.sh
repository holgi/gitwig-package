#!/bin/sh

echo
echo "**** pushing changes to bare [Lives's post-commit hook]"
echo

git push /Users/holgerfrey/Developer/gitwig/site-repositories/bare.git master

echo "starting website rendering, have a look at gitwig.log"
nohup gitwig-update > gitiwg.log 2>&1 &
