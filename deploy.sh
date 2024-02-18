#!/bin/bash

trap "[ -f ./lavalink_pipe ] && rm ./lavalink_pipe" SIGINT

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
            It should be specified in application.yml." \
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


if [[ ! -d "./venv" ]]; then
    printf "No virtual environment found. Creating one...\n"
    if ! python3 -m venv venv; then
        printf "There was a problem creating the virtual environment.\n"
        printf "Do you have %s and %s installed?\n" \
            "python3-pip" \
            "python3.10-venv (or later)"
        exit 1
    fi
    cat >> ./venv/bin/activate <<- 'EOC'

        BOT_TOKEN="$(head -1 "$HOME/.config/discord/BOT_TOKEN")"
        LAVALINK_PASS="$(head -1 "$HOME/.config/discord/LAVALINK_PASS")"
        OWNER_ID="$(head -1 "$HOME/.config/discord/OWNER_ID")"
EOC
fi

start_lavalink() {
    mkfifo lavalink_pipe
    (cd ./Lavalink && java -jar ./Lavalink.jar > ../lavalink_pipe 2>&1) &
    printf "Waiting for Lavalink to be ready...\n"
    while IFS= read -r line; do
        printf "Lavalink: %s\n" "$line"
        if printf "%s" "$line" | grep 'Lavalink is ready to accept connections.' > /dev/null 2>&1; then
            printf "\e[32mLavalink is ready to accept connections!\e[0m\n"
            break
        fi
    done < lavalink_pipe
    rm lavalink_pipe
}

if ! check_vars; then
    printf "Couldn't verify essential environment variables.\n" && exit 1
fi

if ! source ./venv/bin/activate; then
    printf "There was a problem activating the virtual environment.\n" && exit 1
fi

if ! start_lavalink; then
    printf "There was a problem starting Lavalink!\n" && exit 1
fi

if ! python3 -m kolbot; then
    printf "There was a problem starting kolbot!\n" && exit 1
fi
