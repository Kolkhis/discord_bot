#!/bin/bash
# shellcheck disable=SC1090

trap "[[ -f ./lavalink_pipe ]] && rm ./lavalink_pipe && exit 0 || exit 0" SIGINT


declare LAVALINK_DIR
declare VENV_ACTIVATION_SCRIPT
VENV_ACTIVATION_SCRIPT=$(find . -name 'activate')

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
                >&2 printf "\e[31mInvalid Lavalink directory!\n\e[0m" && exit 1;
            [[ -f "${LAVALINK_DIR}/Lavalink.jar" ]] ||
                >&2 printf "\e[31mNo Lavalink.jar found in %s!\n\e[0m" "$LAVALINK_DIR" && exit 1;
            printf "Using Lavalink directory: %s\n" "$LAVALINK_DIR"
            shift;
            exit 0;
            ;;
    esac
done
if [[ -z "$LAVALINK_DIR" ]]; then LAVALINK_DIR="./Lavalink"; fi


if [[ ! -d $LAVALINK_DIR ]]; then
    >&2 printf "\e[31mLavalink directory %s does not exist!\n\e[0m" "$LAVALINK_DIR"
    if ! mkdir ./Lavalink; then
        >&2 printf "\e[31mFailed to create Lavalink directory!\n\e[0m"
        exit 1
    fi
fi

if [[ ! -f "$LAVALINK_DIR/Lavalink.jar" ]]; then
    >&2 printf "\e[31mCouldn't find Lavalink.jar in %s!\n\e[0m" "$LAVALINK_DIR"
    printf "Download Lavalink.jar from:\n"
    printf "https://github.com/lavalink-devs/Lavalink/releases/download/4.0.3/Lavalink.jar\n"
    exit 1
fi

if [[ ! -f "$LAVALINK_DIR/application.yml" ]]; then
    >&2 printf "\e[31mCouldn't find application.yml (Lavalink config) in %s!\n\e[0m" "$LAVALINK_DIR"
    printf "Attempting to download a default Lavalink config...\n"
    if ! curl -fSsLo ./Lavalink/application.yml \
        https://raw.githubusercontent.com/topi314/LavaSrc/master/application.example.yml
        then
            >&2 printf "\e[31mFailed to download Lavalink config!\n\e[0m"
            exit 1
    fi
fi




check_vars() {
    [[ -z "$XDG_CONFIG_HOME" ]] && XDG_CONFIG_HOME="$HOME/.config"

    if [[ ! -s "$XDG_CONFIG_HOME/discord/OWNER_ID" ]]; then
        >&2 printf "No Discord Owner ID provided.\n \
            Please provide an Owner ID in %s\n" \
            "$XDG_CONFIG_HOME/discord/OWNER_ID"
        return 1
    fi

    if [[ ! -s "$XDG_CONFIG_HOME/discord/LAVALINK_PASS" ]]; then
        >&2 printf "\nNo Lavalink Password provided.\n \
            Please provide a Lavalink Password in %s\n\
            It should also be specified in ./Lavalink/application.yml.\n" \
            "$XDG_CONFIG_HOME/discord/LAVALINK_PASS"
        return 1
    fi

    if [[ ! -s "$XDG_CONFIG_HOME/discord/BOT_TOKEN" ]]; then
        >&2 printf "\nNo Discord Bot Token provided.\n \
            Please provide a Discord Bot Token in %s\n" \
            "$XDG_CONFIG_HOME/discord/BOT_TOKEN"
        return 1
    fi
    return 0
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
        # printf "Lavalink: %s\n" "$line"
        if printf "%s" "$line" | grep 'Lavalink is ready to accept connections.' > /dev/null 2>&1; then
            printf "\e[32mLavalink is ready to accept connections!\nLaunching Kolbot...\e[0m\n"
            break
        fi
    done < lavalink_pipe
    rm lavalink_pipe
}


check_activation_script() {
    VENV_ACTIVATION_SCRIPT=$(find . -name 'activate')
    if ! [[ -f "$VENV_ACTIVATION_SCRIPT" ]]; then
        printf "No virtual environment found. Creating one...\n"
        if ! python3 -m venv venv; then
            >&2 printf "\e[31mThere was a problem creating the virtual environment.\n\e[0m"
            >&2 printf "Make sure you have %s and %s installed!\n" \
                "python3-pip" \
                "python3.10-venv (or later)"
            return 1
        fi

        VENV_ACTIVATION_SCRIPT=$(find . -name 'activate' -path './venv/bin/*')
        if ! source "$VENV_ACTIVATION_SCRIPT"; then
            >&2 printf "\e[31mThere was a problem activating the virutal environment!\n\e[0m"
            return 1
        fi
        if ! pip install -r requirements.txt; then
            >&2 printf "\e[31mThere was a problem installing the dependencies!\n\e[0m"
            return 1
        fi
        printf "Setting up the activation script with the environment variables...\n"
        cat <<- '_end_var_fix'  >> ./venv/bin/activate

			BOT_TOKEN="$(head -1 "$HOME/.config/discord/BOT_TOKEN")"
			LAVALINK_PASS="$(head -1 "$HOME/.config/discord/LAVALINK_PASS")"
			OWNER_ID="$(head -1 "$HOME/.config/discord/OWNER_ID")"
_end_var_fix
        printf "\e[32mDone!\n\e[0m"

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





# Banner
[[ -f ./banner.txt ]] && dpkg -l | grep -q 'lolcat' 2>/dev/null &&
    lolcat < ./banner.txt

if ! check_activation_script; then
    >&2 printf "\e[31mThere was a problem setting up the virtual environment.\n\e[0m" && exit 1
fi

if ! check_vars; then
    >&2 printf "\e[31mCouldn't verify essential environment variables.\n\e[0m" && exit 1
fi


if ! source "$VENV_ACTIVATION_SCRIPT" && ! source "$(find . -name 'activate')"; then
    >&2 printf "\e[31mThere was a problem activating the virutal environment!\n\e[0m" && exit 1
fi

printf "\e[32mVirtual environment activated!\n\e[0m"

if ! start_lavalink; then
    >&2 printf "\e[31mThere was a problem starting Lavalink!\n\e[0m" && exit 1
fi

if ! [[ -d "./logs" ]]; then
    if ! mkdir ./logs; then
        >&2 printf "Couldn't create a logs directory!\n"
        exit 1
    fi 
fi

if ! python3 -m kolbot; then
    >&2 printf "\e[31mKolbot encountered a problem! Exiting...\n\e[0m" && exit 1
fi

# TODO: Listen for "Cannot connect to host" error message and handle it:
# WARNING wavelink.websocket An unexpected error occurred while connecting Node(identifier=1FJkuhP7V1f4GujL, uri=http://0.0.0.0:2333, status=NodeStatus.CONNECTING, players=0) to Lavalink: 
# "Cannot connect to host 0.0.0.0:2333 ssl:default [Connect call failed ('0.0.0.0', 2333)]"
#   * Create a named pipe to kolbot, copying stdout and stderr to it.
#   * Listen through the named pipe (helper script? backgrounded function process?)
#   * Exit kolbot if the pipe receives the error message.
#   * Listen for "Cannot connect to host" or "Connect call failed" in the named pipe.  


