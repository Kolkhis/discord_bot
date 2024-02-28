#!/bin/bash
# shellcheck disable=SC1090,SC2034

trap "[[ -f ./lavalink_pipe ]] && rm ./lavalink_pipe && exit 0 || exit 0" SIGINT

declare LAVALINK_DIR
declare VENV_ACTIVATION_SCRIPT
VENV_ACTIVATION_SCRIPT=$(find . -name 'activate')


case $TERM in
    (*-256color)
        RED=$'\e[38;5;196m';
        GREEN=$'\e[38;5;82m';
        ;;
    (*)
        RED=$'\e[31m';
        GREEN=$'\e[32m';
        ;;
esac


check_vars() {
    [[ -z "$XDG_CONFIG_HOME" ]] && XDG_CONFIG_HOME="$HOME/.config"

    if [[ ! -s "$XDG_CONFIG_HOME/discord/OWNER_ID" ]]; then
        printf >&2 "No Discord Owner ID provided.\n \
            Please provide an Owner ID in %s\n" \
            "$XDG_CONFIG_HOME/discord/OWNER_ID"
        return 1
    fi

    if [[ ! -s "$XDG_CONFIG_HOME/discord/LAVALINK_PASS" ]]; then
        printf >&2 "\nNo Lavalink Password provided.\n \
            Please provide a Lavalink Password in %s\n\
            It should also be specified in ./Lavalink/application.yml.\n" \
            "$XDG_CONFIG_HOME/discord/LAVALINK_PASS"
        return 1
    fi

    if [[ ! -s "$XDG_CONFIG_HOME/discord/BOT_TOKEN" ]]; then
        printf >&2 "\nNo Discord Bot Token provided.\n \
            Please provide a Discord Bot Token in %s\n" \
            "$XDG_CONFIG_HOME/discord/BOT_TOKEN"
        return 1
    fi
    return 0
}


check_activation_script() {
    VENV_ACTIVATION_SCRIPT=$(find . -name 'activate')
    if ! [[ -f "$VENV_ACTIVATION_SCRIPT" ]]; then
        printf "No virtual environment found. Creating one...\n"
        if ! python3 -m venv venv; then
            printf >&2 "%sThere was a problem creating the virtual environment.\n\e[0m" "${RED}"
            printf >&2 "Make sure you have %s and %s installed!\n" \
                "python3-pip" \
                "python3.10-venv (or later)"
            return 1
        fi

        VENV_ACTIVATION_SCRIPT=$(find . -name 'activate' -path './venv/bin/*')
        if ! source "$VENV_ACTIVATION_SCRIPT"; then
            printf >&2 "%sThere was a problem activating the virutal environment!\n\e[0m" "${RED}"
            return 1
        fi
        if ! pip install -r requirements.txt; then
            printf >&2 "%sThere was a problem installing the dependencies!\n\e[0m" "${RED}"
            return 1
        fi
        printf "Setting up the activation script with the environment variables...\n"
        cat <<- '_end_var_fix'  >> ./venv/bin/activate

			BOT_TOKEN="$(head -1 "$HOME/.config/discord/BOT_TOKEN")"
			LAVALINK_PASS="$(head -1 "$HOME/.config/discord/LAVALINK_PASS")"
			OWNER_ID="$(head -1 "$HOME/.config/discord/OWNER_ID")"
_end_var_fix
        printf "%sDone!\n\e[0m" "${GREEN}"

    elif ! grep -q -E "BOT_TOKEN|LAVALINK_PASS|OWNER_ID" "$VENV_ACTIVATION_SCRIPT" 2>/dev/null; then
        printf "Setting up the activation script with the environment variables...\n"
        cat <<- '_end_var_fix' >> ./venv/bin/activate

			BOT_TOKEN="$(head -1 "$HOME/.config/discord/BOT_TOKEN")"
			LAVALINK_PASS="$(head -1 "$HOME/.config/discord/LAVALINK_PASS")"
			OWNER_ID="$(head -1 "$HOME/.config/discord/OWNER_ID")"
_end_var_fix
    fi

    return $?;
}


start_lavalink() {
    if ! [[ -d "$LAVALINK_DIR" ]]; then
        printf "Couldn't find the Lavalink directory in %s!\n" "$LAVALINK_DIR"
        return 1
    fi
    mkfifo lavalink_pipe
    pipe=$(realpath lavalink_pipe)
    (cd "$LAVALINK_DIR" && java -jar ./Lavalink.jar > "$pipe" 2>&1 &) 
    printf "Waiting for Lavalink to be ready...\n"
    while IFS= read -r line; do
        if printf "%s" "$line" | grep 'Lavalink is ready to accept connections.' > /dev/null 2>&1; then
            printf "%sLavalink is ready to accept connections!\nLaunching Kolbot...\e[0m\n" "${GREEN}"
            break
        fi
    done < lavalink_pipe
    rm lavalink_pipe
}



while [[ -n "$1" ]]; do
    case "$1" in
        (-h|--help)
            printf "Usage: %s [-h] [-l /path/to/Lavalink]\n" "$0";
            printf "Options:\n"
            printf "    -h, --help    \t\t\t Show this help message\n";
            printf "    -l, --lavalink\t\t\t Path to Lavalink directory. If no directory\n";
            printf "                  \t\t\t is specified, './Lavalink/' is used.\n"
            exit 0;
            ;;
        (-l|--lavalink)
            shift;
            LAVALINK_DIR="$1";
            [[ -d "$LAVALINK_DIR" ]] ||
                printf >&2 "%sInvalid Lavalink directory!\n\e[0m" "${RED}" && exit 1;
            [[ -f "${LAVALINK_DIR}/Lavalink.jar" ]] ||
                printf >&2 "%sNo Lavalink.jar found in %s!\n\e[0m" "${RED}" "$LAVALINK_DIR" && exit 1;
            printf "Using Lavalink directory: %s\n" "$LAVALINK_DIR"
            shift;
            exit 0;
            ;;
    esac
done
if [[ -z "$LAVALINK_DIR" ]]; then LAVALINK_DIR="./Lavalink"; fi


if [[ ! -d "$LAVALINK_DIR" ]] && ! mkdir -p "$LAVALINK_DIR"; then
    printf >&2 "%sLavalink directory %s does not exist!\n\e[0m" "${RED}" "$LAVALINK_DIR"
    printf >&2 "%sFailed to create Lavalink directory!\n\e[0m" "${RED}"
        exit 1
fi

if [[ ! -f "$LAVALINK_DIR/Lavalink.jar" ]]; then
    printf >&2 "%sCouldn't find Lavalink.jar in %s!\n\n\e[0m" "${RED}" "$LAVALINK_DIR"
    printf "\tManually download Lavalink.jar from:\n"
    printf "\thttps://github.com/lavalink-devs/Lavalink/releases/download/4.0.3/Lavalink.jar\n\n"
    printf "The file needs to be downloaded manually and placed in %s.\n" "$LAVALINK_DIR"
    printf "Note: Do not change the name of the file Lavalink.jar!\n"
    exit 1
fi

if [[ ! -f "$LAVALINK_DIR/application.yml" ]]; then
    printf >&2 "%sCouldn't find application.yml (Lavalink config) in %s!\n\e[0m" "${RED}" "$LAVALINK_DIR"
    printf "Attempting to download a default Lavalink config...\n"
    if ! curl -fSsLo ./Lavalink/application.yml \
        https://raw.githubusercontent.com/topi314/LavaSrc/master/application.example.yml
        then
            printf >&2 "%sFailed to download Lavalink config!\n\e[0m" "${RED}"
            exit 1
    fi
fi





# Banner
{ [[ -f ./banner.txt ]] && dpkg -l | grep -q 'lolcat'; lolcat < ./banner.txt; } ||
    { [[ -f ./banner.txt ]] && cat ./banner.txt; }


if ! check_activation_script; then
    printf >&2 "%sThere was a problem setting up the virtual environment.\n\e[0m" "${RED}" && exit 1
fi

if ! check_vars; then
    printf >&2 "%sCouldn't verify essential environment variables.\n\e[0m" "${RED}" && exit 1
fi

if ! source "$VENV_ACTIVATION_SCRIPT" && ! source "$(find . -name 'activate')"; then
    printf >&2 "%sThere was a problem activating the virutal environment!\n\e[0m" "${RED}" && exit 1
fi
printf "%sVirtual environment activated!\n\e[0m" "${GREEN}"

if ! start_lavalink; then
    printf >&2 "%sThere was a problem starting Lavalink!\n\e[0m" "${RED}" && exit 1
fi

if ! [[ -d "./logs" ]] && ! mkdir ./logs; then
    printf >&2 "Couldn't create a logs directory!\n" && exit 1
fi

if ! python3 -m kolbot; then
    printf >&2 "%sKolbot encountered a problem! Exiting...\n\e[0m" "${RED}" && exit 1
fi

# TODO: Listen for "Cannot connect to host" error message and handle it:
# WARNING wavelink.websocket An unexpected error occurred while connecting Node(identifier=1FJkuhP7V1f4GujL, uri=http://0.0.0.0:2333, status=NodeStatus.CONNECTING, players=0) to Lavalink: 
# "Cannot connect to host 0.0.0.0:2333 ssl:default [Connect call failed ('0.0.0.0', 2333)]"
#   * Create a named pipe to kolbot, copying stdout and stderr to it.
#   * Listen through the named pipe (helper script? backgrounded function process?)
#   * Exit kolbot if the pipe receives the error message.
#   * Listen for "Cannot connect to host" or "Connect call failed" in the named pipe.  


