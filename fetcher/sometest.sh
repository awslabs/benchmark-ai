#!/bin/bash

trap 'echo "Caught SIGUSR1"' SIGUSR1

echo "Sleeping.  Pid=$$"
while :
do
   sleep 60 &
   wait $!
   echo "Sleep over"
done