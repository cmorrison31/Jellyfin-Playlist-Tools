import configparser
import json

import requests


def load_config(configuration_file_path='config.ini'):
    configuration = configparser.ConfigParser()

    # Set default values
    configuration['jellyfin'] = \
        {'username': '',
         'password': '',
         'server url': '',
         'playlist name': '',
         'playlists to combine': ''}

    configuration.read(configuration_file_path)

    url = configuration.get('jellyfin', 'server url')

    if not url.startswith('http://') and not url.startswith('https:'):
        url = 'https://' + url

    configuration.set('jellyfin', 'url', url)

    return configuration


class ServerConnection:
    class AlbumCache:
        def __init__(self, album=None, tracks=None):
            self.album = album
            self.tracks = tracks

    def __init__(self, server_url, user_name, password):
        self.server_url = server_url
        self.user_name = user_name
        self.password = password

        self.token = None
        self.user_id = None
        self.headers = {}

        self.album_cache = {}

    def _headers(self):
        authorization = (
            'MediaBrowser , '
            'Client="other", '
            'Device="script", '
            'DeviceId="script", '
            'Version="0.0.0"'
        )

        # Set required authorization header
        self.headers = {
            'x-emby-authorization': authorization
        }

        if self.token is not None:
            self.headers['x-mediabrowser-token'] = self.token

    def login(self):
        # Build json payload to authenticate to the server
        auth_data = {
            'Username': self.user_name,
            'Pw': self.password
        }

        self._headers()

        # Log in to the server
        r = requests.post(f'{self.server_url}/Users/AuthenticateByName',
                          headers=self.headers,
                          json=auth_data)

        # Retrieve auth token and user id from returned data
        self.token = r.json().get('AccessToken')
        self.user_id = r.json().get('User').get('Id')

        self._headers()

    def create_playlist(self, playlist_name):
        payload = {
            'Name': playlist_name,
            'userId': self.user_id
        }

        r = requests.post(f'{self.server_url}/Playlists',
                          headers=self.headers, json=payload)

        if r.status_code == 200:
            response = json.loads(r.content.decode('utf-8'))

            return response['Id']
        else:
            return r.status_code

    def get_playlist_id_from_name(self, name):
        r = requests.get(f'{self.server_url}/Users/{self.user_id}/Views',
                         headers=self.headers)

        response = json.loads(r.content.decode('utf-8'))

        playlist_library_id = None

        for item in response['Items']:
            if item['Name'] == 'Playlists':
                playlist_library_id = item['Id']

        params = {
            'ParentId': playlist_library_id
        }

        r = requests.get(f'{self.server_url}/Users/{self.user_id}/Items',
                         headers=self.headers, params=params)

        response = json.loads(r.content.decode('utf-8'))

        playlist_id = None

        for item in response['Items']:
            if item['Name'] == name:
                playlist_id = item['Id']

        return playlist_id

    def add_item_to_playlist(self, playlist_id, item_ids):
        if not isinstance(item_ids, list):
            item_ids = [item_ids, ]

        params = {
            'playlistId': playlist_id,
            'Ids': item_ids,
            'userId': self.user_id
        }

        r = requests.post(f'{self.server_url}/Playlists/{playlist_id}/Items',
                          headers=self.headers, params=params)

        return r.status_code

    def remove_items_from_playlist(self, playlist_id, item_ids):
        if not isinstance(item_ids, list):
            item_ids = [item_ids, ]

        for i, item in enumerate(item_ids):
            item_ids[i] = item['PlaylistItemId']

        params = {
            'EntryIds': item_ids,
        }

        r = requests.delete(f'{self.server_url}/Playlists/{playlist_id}/Items',
                            headers=self.headers, params=params)

        return r.status_code

    def get_playlist_items(self, playlist_id):
        params = {
            'UserId': self.user_id
        }

        r = requests.get(f'{self.server_url}/Playlists/{playlist_id}/Items',
                         headers=self.headers, params=params)

        response = json.loads(r.content.decode('utf-8'))

        return response['Items']

    def get_album_from_id(self, album_id):
        if album_id in self.album_cache and \
                self.album_cache[album_id].album is not None:
            return self.album_cache[album_id].album
        else:
            r = requests.get(f'{self.server_url}/Users/{self.user_id}/Items/'
                             f'{album_id}', headers=self.headers)

            response = json.loads(r.content.decode('utf-8'))

            if album_id in self.album_cache:
                self.album_cache[album_id].album = response
            else:
                self.album_cache[album_id] = \
                    ServerConnection.AlbumCache(album=response)

            return response

    def get_album_items_from_id(self, album_id):
        if album_id in self.album_cache and \
                self.album_cache[album_id].tracks is not None:
            return self.album_cache[album_id].tracks
        else:
            params = {
                'ParentId': album_id
            }

            r = requests.get(f'{self.server_url}/Users/{self.user_id}/Items',
                             headers=self.headers, params=params)

            response = json.loads(r.content.decode('utf-8'))

            if album_id in self.album_cache:
                self.album_cache[album_id].tracks = response
            else:
                self.album_cache[album_id] = \
                    ServerConnection.AlbumCache(tracks=response)

            return response

    @staticmethod
    def get_album_sort_key(album):
        if 'AlbumArtist' not in album:
            return ''

        if album['AlbumArtist'].strip().lower() == 'various artists':
            album_artists = set()

            for artist in album['Artists']:
                sanitized = artist.strip().lower()

                sanitized = "".join(sanitized.split())

                album_artists.add(sanitized)

            key = ''.join(sorted(list(album_artists)))
        else:
            sanitized = album['AlbumArtist'].strip().lower()

            sanitized = "".join(sanitized.split())

            key = sanitized

        return key

    def get_track_sort_key(self, track):
        album_id = track['AlbumId']

        album = self.get_album_from_id(album_id)

        album_tracks = self.get_album_items_from_id(album_id)

        key = ''
        number_of_tracks = album['ChildCount']

        number_of_discs = 1
        for t in album_tracks:
            if 'ParentIndexNumber' in t:
                number_of_discs = max(int(t['ParentIndexNumber']),
                                      number_of_discs)

        key += self.get_album_sort_key(album)
        if 'PremiereDate' in album:
            key += album['PremiereDate']
        elif 'ProductionYear' in album:
            key += str(album['ProductionYear'])

        key += album['SortName']

        if 'ParentIndexNumber' in track:
            key += '{:0{width}.0f}'.format(int(track['ParentIndexNumber']),
                                           width=len(str(number_of_discs)))

        if 'IndexNumber' in track:
            key += '{:0{width}.0f}'.format(int(track['IndexNumber']),
                                           width=len(str(number_of_tracks)))

        key += track['Name']

        return key

    def move_playlist_track(self, playlist_id, playlist_track_id, index):
        params = {
            'UserId': self.user_id
        }

        r = requests.post(f'{self.server_url}/Playlists/{playlist_id}/Items/'
                          f'{playlist_track_id}/Move/{index}',
                          headers=self.headers, params=params)

        if r.status_code != 204:
            print(r.status_code)

    def search_for_music_track_by_name(self, name):
        params = {
            'searchTerm': name,
            'Fields': 'PrimaryImageAspectRatio, CanDelete, BasicSyncInfo, '
                      'MediaSourceCount',
            'Recursive': True,
            'EnableTotalRecordCount': False,
            'ImageTypeLimit': 1,
            'IncludePeople': False,
            'IncludeMedia': True,
            'IncludeGenres': False,
            'IncludeStudios': False,
            'IncludeArtists': False,
            'IncludeItemTypes': 'Audio'
        }

        r = requests.get(f'{self.server_url}/Users/{self.user_id}/Items',
                         headers=self.headers, params=params)

        response = json.loads(r.content.decode('utf-8'))

        return response['Items']
