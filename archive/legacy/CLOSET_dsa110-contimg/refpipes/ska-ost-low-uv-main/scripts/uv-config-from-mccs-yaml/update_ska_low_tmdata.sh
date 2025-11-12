# This script pulls any changes from MCCS station YAML
GITDIR='ska-low-tmdata'

if [ -d $GITDIR ]; then
    cd $GITDIR;
    git pull origin main;
else
   git clone https://gitlab.com/ska-telescope/ska-low-tmdata;
fi
