#!/bin/bash

usage() {
cat << EOF
Usage : docker run [...] nicolabs/nicobot:<tag> <bot's name>
              [--signal-register <device name>]
              [--qrcode-options <qr options>]
              [bot's regular arguments]

Arguments :

<bot's name>                      One of 'askbot' or 'transbot'.

--signal-register <device name>   Will display a QR Code to scan & register with
                                  an existing Signal account. <device name> is a
                                  string to identify the docker container as a
                                  signal device.

--qrcode-options <qr options>     Additional options (in one string) to the 'qr'
                                  command. The QR Code can be printed directly
                                  to the console without using this argument but
                                  make sure to pass '-it' to 'docker run'.
                                  See github.com/lincolnloop/python-qrcode.

[bot's regular arguments]         All arguments that can be passed to the bot.
                                  See github.com/nicolabs/nicobot.

E.g. '$0 transbot -h' to get a more specific help for 'transbot'
EOF
}


# Default values
opt_signal_register=
opt_qrcode_options=
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
      (--qrcode-options)
            opt_qrcode_options=$2
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
    # Displays an URL and a QRCode in the console to link the current container
    # with whichever Signal client will scan it.
    # NOTES :
    # - This syntax requires bash.
    # - It seems this command does not return a 0 status even when the operation succeeded
    signal-cli link --name "${opt_signal_register}" | tee >(head -1 | qr ${opt_qrcode_options})
fi

# Runs the right bot with the remaining args
case "${opt_bot}" in
    askbot|transbot)
        #exec python3 -m "nicobot.${opt_bot}" "$@"
        exec "${opt_bot}" "$@"
        ;;
    *)
        echo "Unknown bot : '*{opt_bot}'" >2
        usage
        exit 1
        ;;
esac
