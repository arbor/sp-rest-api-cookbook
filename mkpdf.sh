#!/bin/bash

DOCKER_CMD='docker'
DOCKER_DIR='./render'
DOCKER_IMAGE_NAME='cookbook-render'
INPUT_FILE='sp-rest-api-tutorial.txt'

IS_IMAGE=`$DOCKER_CMD images | grep $DOCKER_IMAGE_NAME | wc -l`

if [ $IS_IMAGE -gt 0 ] ; then
    echo "Using existing image ($DOCKER_IMAGE_NAME)"
else
    echo "Building new docker image, this will take a bit"
    if [ ! -d $DOCKER_DIR ] ; then
        echo "Can't find the directory $DOCKER_DIR so can't proceed"
        exit 1
    fi
    $DOCKER_CMD build -t $DOCKER_IMAGE_NAME $DOCKER_DIR > /dev/null 2>&1
fi

if [ ! -f $INPUT_FILE ] ; then
    echo "Can't find $INPUT_FILE; make sure you are in the correct directory"
    exit 1
fi

$DOCKER_CMD run -v `pwd`:/source --rm $DOCKER_IMAGE_NAME $INPUT_FILE
