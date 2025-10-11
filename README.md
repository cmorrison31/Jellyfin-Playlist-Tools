# Jellyfin-Playlist-Tools
This project is a collection of scripts for managing music playlists on a 
Jellyfin instance. 

## Available Scripts
 - sort_playlist
 - combine_playlists
 - export_playlist
 - filter_playlist
 - import_playlist
 - remove_duplicates

# License
This project is licensed under the MIT license. See LICENSE for more 
information.

# Configuration
Create a config.ini like so:

```ini
[jellyfin]
username = username
password = password
server url = example.com
playlist name = some_playlist
playlists to combine = some_playlist2, some_playlist3
```

Not every configuration option is used at the same time. For example, 
"playlists to combine" is only relevant and required if you're actively 
combining playlists.

# Example Usage
Call the script function for the operation you wish to execute. The 
config.ini file needs to be in the same directory as your script. 

For example, if sorting a playlist, the following command will sort the 
playlist given by "playlist name" in the configuration file.

```python
from JellyfinPlaylistTools import Scripts


def main():
    Scripts.sort_playlist()


if __name__ == '__main__':
    main()

```

# Note
Jellyfin-Playlist-Tools is not affiliated with the official Jellyfin 
project