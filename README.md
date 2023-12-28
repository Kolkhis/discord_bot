
# Personal Discord Bot

A personal Discord bot made with discordpy and wavelink (wrapper for lavalink).


## Dependencies
* `discordpy[voice]`
Voice dependencies for Linux-based environments:
* `libffi-dev`
* `libnacl-dev`
* `python3-dev`

```bash
sudo apt install libffi-dev libnacl-dev python3-dev
```

* Lavalink 
    * [Lavalink.jar](https://github.com/lavalink-devs/Lavalink/releases)
* Lavalink Config
    * [Lavalink example application.yml](https://raw.githubusercontent.com/lavalink-devs/Lavalink/master/LavalinkServer/application.yml.example)
    * [LavaSrc example application.yml](https://raw.githubusercontent.com/topi314/LavaSrc/master/application.example.yml)
* Requires Java 17+ (not the default- apt packages):
  ```bash
  sudo apt install openjdk-17-jdk openjdk-17-jre
  ```
* Wrong Java version in `apt`:
    * default-jre (v11)
    * default-jdk (v11)

## Running in the background
* How to run as a service via [systemd](https://lavalink.dev/configuration/systemd)
* Run as a [docker container](https://lavalink.dev/configuration/docker)

* Permission integer: `19599322192` (`4417645833296` with sound board support)


