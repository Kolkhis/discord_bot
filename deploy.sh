#!/bin/bash
# shellcheck disable=SC1090

#######################################################################
#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%#
#%%                                                                 %%#
#%%   888    d8P            888  888       888       d8b            %%#
#%%   888   d8P             888  888       888       Y8P            %%#
#%%   888  d8P              888  888       888                      %%#
#%%   888d88K      .d88b.   888  888  888  88888b.   888  .d8888b   %%#
#%%   8888888b    d88""88b  888  888 .88P  888 "88b  888  88K       %%#
#%%   888  Y88b   888  888  888  888888K   888  888  888  "Y8888b.  %%#
#%%   888   Y88b  Y88..88P  888  888 "88b  888  888  888       X88  %%#
#%%   888    Y88b  "Y88P"   888  888  888  888  888  888   88888P'  %%#
#%%                                                                 %%#
#%%                                                                 %%#
#%%                           Presents...                           %%#
#%%                                                                 %%#
#%%                                                                 %%#
#%%    888    d8P              888   888                   888      %%#
#%%    888   d8P               888   888                   888      %%#
#%%    888  d8P                888   888                   888      %%#
#%%    888d88K       .d88b.    888   88888b.     .d88b.    888888   %%#
#%%    8888888b     d88""88b   888   888 "88b   d88""88b   888      %%#
#%%    888  Y88b    888  888   888   888  888   888  888   888      %%#
#%%    888   Y88b   Y88..88P   888   888 d88P   Y88..88P   Y88b.    %%#
#%%    888    Y88b   "Y88P"    888   88888P"     "Y88P"     "Y888   %%#
#%%                                                                 %%#
#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%#
#######################################################################




trap "[[ -f ./lavalink_pipe ]] && rm ./lavalink_pipe" SIGINT

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
        printf "Lavalink: %s\n" "$line"
        if printf "%s" "$line" | grep 'Lavalink is ready to accept connections.' > /dev/null 2>&1; then
            printf "\e[32mLavalink is ready to accept connections!\n\nLaunching Kolbot...\e[0m\n"
            break
        fi
    done < lavalink_pipe
    rm lavalink_pipe
}


if [[ ! -d "./venv" ]] || ! find . -name 'activate'; then
    printf "No virtual environment found. Creating one...\n"
    if ! python3 -m venv venv; then
        printf "There was a problem creating the virtual environment.\n"
        printf "Make sure you have %s and %s installed!\n" \
            "python3-pip" \
            "python3.10-venv (or later)"
        exit 1
    fi
    . "$(find . -name 'activate')"
    . venv/bin/activate
    pip install -r requirements.txt
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
                >&2 printf "Invalid Lavalink directory!\n" && exit 1;
            [[ -f "${LAVALINK_DIR}/Lavalink.jar" ]] ||
                >&2 printf "No Lavalink.jar found in %s!\n" "$LAVALINK_DIR" && exit 1;
            printf "Using Lavalink directory: %s\n" "$LAVALINK_DIR"
            shift;
            exit 0;
            ;;
    esac
done


if [[ -z "$LAVALINK_DIR" ]]; then LAVALINK_DIR="./Lavalink"; fi


if ! check_vars; then
    printf "Couldn't verify essential environment variables.\n" && exit 1
fi

if ! source ./venv/bin/activate; then
    printf "Activation script not found at ./venv/bin/activate\n" 
    printf "Searching for the activation script...\n"
    SCRIPT="$(find . -name 'activate')" &&
        printf "Activation script found at %s\n" "$SCRIPT" ||
        printf "Couldn't find a virtual environment activation script. Aborting.\n" &&
        exit 1
    if ! source "$SCRIPT"; then
        printf "There was a problem activating the virtual environment.\n" && exit 1
    fi
    printf "Activation script found at %s\n" "$SCRIPT"
fi
printf "Virtual environment activated!\n"

if ! start_lavalink; then
    printf "There was a problem starting Lavalink!\n" && exit 1
fi

if ! python3 -m kolbot; then
    printf "There was a problem starting kolbot!\n" && exit 1
fi


