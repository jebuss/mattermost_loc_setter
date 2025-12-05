# Mattermost Location Status Setter

This tool automatically updates your Mattermost status based on your network location and meeting state.

## Installation

1.  **Create Configuration File**

    Copy the `config.toml.example` file to `~/.config/mm-status/config.toml` and fill in your `access_token` and `user_id`.

    ```bash
    mkdir -p ~/.config/mm-status
    cp config.toml.example ~/.config/mm-status/config.toml
    # Now edit ~/.config/mm-status/config.toml with your favorite editor
    ```

2.  **Install the Package**

    Navigate to the project's root directory and install it using pip:

    ```bash
    pip install .
    ```

## Usage

The package provides the `mm-status` command.

```bash
# Automatically detect and set status
mm-status auto

# Manually set a status
mm-status set "Working on a new feature" rocket

# Clear the current custom status
mm-status clear

# Test the connection to the Mattermost server
mm-status test
```

## Automation

### Option 1: macOS launchd (Recommended for macOS)

Use `launchd` for reliable background execution with proper network permissions. Create the file `~/Library/LaunchAgents/org.lamarr.mattermost-status.plist` with the following content:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>org.lamarr.mattermost-status</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/mm-status</string>
        <string>auto</string>
    </array>
    <key>StartInterval</key>
    <integer>60</integer>
    <key>StandardOutPath</key>
    <string>/tmp/mm_loc_setter.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/mm_loc_setter_error.log</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
```

**Load and manage the agent:**

```bash
# Load the agent
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/org.lamarr.mattermost-status.plist

# Start it immediately
launchctl kickstart -k gui/$(id -u)/org.lamarr.mattermost-status

# Stop the agent
launchctl bootout gui/$(id -u)/org.lamarr.mattermost-status

# Check if it's running
launchctl list | grep mattermost
```

**Important:** Replace `/usr/local/bin/mm-status` with the actual path from `which mm-status`.

### Option 2: Cron (Linux/Unix)

For Linux systems or if you prefer cron on macOS, add a cron job:

```bash
# Edit your crontab
crontab -e

# Add this line to run every minute between 8am-6pm on weekdays
*/1 8-18 * * 1-5 /usr/local/bin/mm-status auto >> /tmp/mm_loc_setter.log 2>&1
```

**Important notes for cron:**
- Replace `/usr/local/bin/mm-status` with the output from `which mm-status`
- On macOS, you may need to grant Terminal/cron Full Disk Access in System Preferences → Security & Privacy → Privacy
- The script includes time checks, so it will only run during working hours even if cron runs 24/7

**To remove the cron job:**

```bash
crontab -e
# Delete the mm-status line and save
```