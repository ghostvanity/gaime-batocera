#!/bin/bash

FLAG="/tmp/gaime_game_running"

case "$1" in

    gameStart)
        touch "$FLAG"
        ;;

    gameStop)
        rm -f "$FLAG"
        ;;

esac

exit 0
