import time

import core


def main():
    watchdog = core.watchdog.Watchdog()

    while True:
        try:
            watchdog.run_loop()

            time.sleep(int(core.config["WATCHDOG_INTERVAL"]))

        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
