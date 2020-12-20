#!/bin/sh

usage()
{
cat << EOF
Usage : $0 [bot's name] [bot's arguments]

Available bots :
- askbot
- transbot

E.g. '$0 transbot -h' to get a more specific help for 'transbot'
EOF
}

# It's not needed to repeat the commands for each bot but it's clearer
bot=$1
case $bot in
    transbot)
        shift
        exec python -m "nicobot.$bot" "$@"
        ;;
    askbot)
        shift
        exec python -m "nicobot.$bot" "$@"
        ;;
    *)
        usage
        exit 1
        ;;
esac
