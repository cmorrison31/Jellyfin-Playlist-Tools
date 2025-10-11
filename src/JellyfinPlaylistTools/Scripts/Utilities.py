from JellyfinPlaylistTools.API import JellyfinAPI


class PlaylistItem:
    def __init__(self, artist, album, track):
        self.artist = artist
        self.album = album
        self.track = track


def load_config_and_login():
    config = JellyfinAPI.load_config()

    server = JellyfinAPI.ServerConnection(config.get('jellyfin', 'url'),
                                          config.get('jellyfin', 'username'),
                                          config.get('jellyfin', 'password'))

    server.login()

    return config, server


def select_artist(track):
    if 'AlbumArtist' in track and len(track["AlbumArtist"]) > 0:
        return track['AlbumArtist']
    elif 'AlbumArtists' in track and len(track["AlbumArtists"]) > 0:
        return track['AlbumArtists']
    elif ('Artists' in track and len(track["Artists"]) > 0 and
          len(track["Artists"][0]) > 0):
        return ' '.join(track["Artists"])
    else:
        return 'None'