#!/usr/bin/env bash
pid=$(launchctl list | grep jp.openclaw.tg_poll_loop | awk '{print $1}')
if [ -z "$pid" ] || [ "$pid" = "-" ]; then
    launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/jp.openclaw.tg_poll_loop.plist
fi
