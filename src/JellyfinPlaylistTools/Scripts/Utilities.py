from mutagen.flac import FLAC
from mutagen.id3 import ID3, TCON, ID3NoHeaderError
from mutagen.mp3 import MP3

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
    elif ('Artists' in track and len(track["Artists"]) > 0 and len(
        track["Artists"][0]) > 0):
        return ' '.join(track["Artists"])
    else:
        return 'None'


def process_genre_list(genre_list):
    banned_list = {'255', 'Mod', 'Builds', 'Bowie', 'Drama', 'Film'}

    # Replace then split incase there's mixed "/" and ";" usage.
    split_genres = [x.strip().title() for x in
                    genre_list.replace('/', ';').split(';') if
                    x.strip().title() not in banned_list]

    return split_genres


def fix_genre_tag(file_path):
    ext = file_path.suffix.lower()
    changed = False

    if ext == '.flac':
        audio = FLAC(file_path)
        if 'genre' in audio:
            genres = audio['genre']
            new_genres = []
            for g in genres:
                genre_list = process_genre_list(g)
                new_genres.extend(genre_list)
            if genres != new_genres:
                audio['genre'] = new_genres
                audio.save()
                changed = True

    elif ext == '.mp3':
        try:
            audio = ID3(file_path)
        except ID3NoHeaderError:
            try:
                mp3 = MP3(file_path)
                mp3.add_tags()
                mp3.save()
                audio = ID3(file_path)
            except Exception as e:
                print(f'Error reading ID3 from {file_path}: {e}')
                return False

        if 'TCON' in audio:
            genres_raw = audio['TCON'].text
            new_genres = []
            for g in genres_raw:
                genre_list = process_genre_list(g)
                new_genres.extend(genre_list)
            if genres_raw != new_genres:
                audio['TCON'] = TCON(encoding=3, text=new_genres)
                audio.save()
                changed = True

    return changed
