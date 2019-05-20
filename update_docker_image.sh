#!/bin/bash
read -p 'This will update the docker image on docker hub, are you sure? (y/N) ' execflag
if [[ $execflag == y* || $execflag == Y* ]]
then
    echo Preparing to push OME image to docker hub
    docker image build -t oegupm/ome:latest -f Dockerfile.base .
    docker image push oegupm/ome:latest
else
    echo The docker image will not be updated in docker hub
fi
#echo Your answer is $execflag
