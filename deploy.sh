#!/bin/bash

. ./venv/bin/activate
(cd ./Lavalink && java -jar ./Lavalink.jar) &
sleep 10;
python3 -m kolbot 

