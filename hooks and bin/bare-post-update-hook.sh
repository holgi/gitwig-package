#!/bin/sh

echo
echo "**** Pulling changes into Live [Bares's post-update hook]"
echo

cd /Users/holgerfrey/Developer/gitwig/site-repositories/live || exit
unset GIT_DIR
git pull /Users/holgerfrey/Developer/gitwig/site-repositories/bare.git master
