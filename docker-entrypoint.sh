#!/bin/bash

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


# Displays an URL and a QRCode in the console to link the current container
# with whichever Signal client will scan it
signal_link() {
    device_name=$1
    # WARNING This command works on alpine with bash installed, not tested otherwise
    signal-cli link --name "${device_name}" | tee >(head -1 | qr)
}

# Default values
opt_signal_register=
opt_bot=

# Parses the command line for options to execute before running the bot
# TODO Enhance CLI handling with getopt
#ARGS=$(getopt -l 'signal-register:' -- "$@") || usage && exit 1
#eval "set -- $ARGS"
while true; do
    case $1 in
      (--signal-register)
            opt_signal_register=$2
            shift 2;;
      (askbot|transbot)
            opt_bot=$1
            shift;;
      (*)
            # End of this script's options ; next options are for the bot
            break;;
    esac
done

# Registers the device with signal
if [ -n "${opt_signal_register}" ]; then
    signal_link "${opt_signal_register}"
fi

# Runs the right bot with the remaining args
case "${opt_bot}" in
    askbot|transbot)
        exec python3 -m "nicobot.${opt_bot}" "$@"
        ;;
    *)
        usage
        exit 1
        ;;
esac
