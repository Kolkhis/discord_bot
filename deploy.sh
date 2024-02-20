#!/bin/bash
# shellcheck disable=SC1090


[[ -f ./banner.txt ]] && dpkg -l | grep -q 'lolcat' 2>/dev/null &&
    lolcat < ./banner.txt

trap "[[ -f ./lavalink_pipe ]] && rm ./lavalink_pipe && exit 0" SIGINT

declare LAVALINK_DIR

check_vars() {
    [[ -z "$XDG_CONFIG_HOME" ]] && XDG_CONFIG_HOME="$HOME/.config"

    if [[ ! -s "$XDG_CONFIG_HOME/discord/OWNER_ID" ]]; then
        printf "No Discord Owner ID provided.\n \
            Please provide an Owner ID in %s\n" \
            "$XDG_CONFIG_HOME/discord/OWNER_ID"
        return 1
    fi

    if [[ ! -s "$XDG_CONFIG_HOME/discord/LAVALINK_PASS" ]]; then
        printf "\nNo Lavalink Password provided.\n \
            Please provide a Lavalink Password in %s\n\
            It should also be specified in ./Lavalink/application.yml.\n" \
            "$XDG_CONFIG_HOME/discord/LAVALINK_PASS"
        return 1
    fi

    if [[ ! -s "$XDG_CONFIG_HOME/discord/BOT_TOKEN" ]]; then
        printf "\nNo Discord Bot Token provided.\n \
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
    ACTIVATION_SCRIPT=$(find . -name 'activate')
    if ! grep -q -E "BOT_TOKEN|LAVALINK_PASS|OWNER_ID" "$ACTIVATION_SCRIPT" 2>/dev/null; then
        printf "Setting up the activation script with the environment variables...\n"
        cat >> ./venv/bin/activate <<- '_end_var_fix'

            BOT_TOKEN="$(head -1 "$HOME/.config/discord/BOT_TOKEN")"
            LAVALINK_PASS="$(head -1 "$HOME/.config/discord/LAVALINK_PASS")"
            OWNER_ID="$(head -1 "$HOME/.config/discord/OWNER_ID")"
_end_var_fix
    fi
    return $?;
}


if [[ ! -d "./venv" ]] && ! find . -name 'activate'; then
    printf "No virtual environment found. Creating one...\n"
    if ! python3 -m venv venv; then
        printf "There was a problem creating the virtual environment.\n"
        printf "Make sure you have %s and %s installed!\n" \
            "python3-pip" \
            "python3.10-venv (or later)"
        exit 1
    fi
    if ! source venv/bin/activate && source "$(find . -name 'activate')"; then
        printf "\e[31mThere was a problem activating the virutal environment!\n\e[0m"
        exit 1
    fi
    if ! pip install -r requirements.txt; then
        printf "\e[31mThere was a problem installing the dependencies!\n\e[0m"
        exit 1
    fi
    printf "Setting up the activation script with the environment variables...\n"
    cat >> ./venv/bin/activate <<- 'EOC'

        BOT_TOKEN="$(head -1 "$HOME/.config/discord/BOT_TOKEN")"
        LAVALINK_PASS="$(head -1 "$HOME/.config/discord/LAVALINK_PASS")"
        OWNER_ID="$(head -1 "$HOME/.config/discord/OWNER_ID")"
EOC
    printf "\e[32mDone!\n\e[0m"
fi




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


if ! check_vars; then
    printf "\e[31mCouldn't verify essential environment variables.\n\e[0m" && exit 1
fi

if ! source venv/bin/activate && ! source "$(find . -name 'activate')"; then
    printf "\e[31mThere was a problem activating the virutal environment!\n\e[0m"
    exit 1
fi

printf "\e[32mVirtual environment activated!\n\e[0m"

if ! start_lavalink; then
    printf "\e[31mThere was a problem starting Lavalink!\n\e[0m" && exit 1
fi

if ! python3 -m kolbot; then
    printf "\e[31mKolbot encountered a problem! Exiting...\n\e[0m" && exit 1
fi

# TODO: Listen for "Cannot connect to host" error message and handle it:
# WARNING wavelink.websocket An unexpected error occurred while connecting Node(identifier=1FJkuhP7V1f4GujL, uri=http://0.0.0.0:2333, status=NodeStatus.CONNECTING, players=0) to Lavalink: 
# "Cannot connect to host 0.0.0.0:2333 ssl:default [Connect call failed ('0.0.0.0', 2333)]"


