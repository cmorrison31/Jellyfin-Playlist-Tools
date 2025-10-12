import re

from thefuzz import fuzz

import sys

from pathlib import Path

from JellyfinPlaylistTools.Scripts import Utilities


def sort_playlist():
    config, server = Utilities.load_config_and_login()

    print('Logged in')

    playlist_id = server.get_playlist_id_from_name(
        config.get('jellyfin', 'playlist name'))
    print('Got playlist')

    items = server.get_playlist_items(playlist_id)
    print('Got items')

    sort_keys = []

    for i, track in enumerate(items):
        sort_keys.append((server.get_track_sort_key(track), i))
    print('Got sort keys')

    sort_keys.sort(key=lambda x: x[0])
    print('Sorted the sort keys')

    with open('../keys.txt', 'w') as f:
        for k in sort_keys:
            f.write(k[0] + '\n')
    print('Sort keys written to keys.txt')

    print('Sorting')
    for i, sort_key in enumerate(sort_keys):
        track = items[sort_key[1]]

        server.move_playlist_track(playlist_id, track['PlaylistItemId'], i)
        print(f'{i}/{len(sort_keys)}')


def combine_playlists():
    config, server = Utilities.load_config_and_login()

    playlist_id = server.get_playlist_id_from_name(
        config.get('jellyfin', 'playlist name'))

    if playlist_id is None:
        playlist_id = server.create_playlist(
            config.get('jellyfin', 'playlist name'))

    playlists = [tmp for tmp in
                 config.get('jellyfin', 'playlists to combine').split(', ')]

    items = []

    for playlist in playlists:
        local_playlist_id = server.get_playlist_id_from_name(playlist)

        playlist_items = server.get_playlist_items(local_playlist_id)

        for item in playlist_items:
            items.append(item)

    for i, item in enumerate(items):
        if i % 10 == 0:
            print('{}/{}'.format(i, len(items)))

        status = server.add_item_to_playlist(playlist_id, item['Id'])

        if status != 204:
            print(f'Status code: {status}')


def export_playlist():
    config, server = Utilities.load_config_and_login()

    playlist_id = server.get_playlist_id_from_name(
        config.get('jellyfin', 'playlist name'))

    items = server.get_playlist_items(playlist_id)

    with open(config.get('jellyfin', 'playlist name') + '.txt', 'w') as f:
        for i, track in enumerate(items):
            artist = Utilities.select_artist(track)
            f.write('{:.0f} - {} - {} - {}\n'.format(i, artist, track['Album'],
                                                     track['Name']))


def filter_playlist():
    config, server = Utilities.load_config_and_login()

    playlist_id = server.get_playlist_id_from_name(
        config.get('jellyfin', 'playlist name'))

    items = server.get_playlist_items(playlist_id)

    for item in items:
        match = re.search('remix', item['Name'], re.IGNORECASE)

        if match:
            print(item)


def import_playlist():
    config, server = Utilities.load_config_and_login()

    playlist_id = server.get_playlist_id_from_name(
        config.get('jellyfin', 'playlist name'))

    playlist_data = []

    with open(config.get('jellyfin', 'playlist name') + '.txt', 'r') as f:
        for line in f:
            line_data = line.strip().split('-')

            if len(line_data) == 4:
                artist = line_data[1].strip()
                album = line_data[2].strip()
                track = line_data[3].strip()
            elif len(line_data) == 5:
                artist = line_data[1].strip()
                album = line_data[2].strip() + ' - ' + line_data[3].strip()
                track = line_data[4].strip()
            elif len(line_data) == 6:
                artist = line_data[1].strip()
                album = line_data[2].strip() + ' - ' + line_data[3].strip()
                track = line_data[4].strip() + ' - ' + line_data[5].strip()

            track_data = track.split("'")
            if len(track_data) > 1:
                track = track_data[0]

            playlist_data.append(Utilities.PlaylistItem(artist, album, track))

    no_matches = []
    low_scores = []

    for entry in playlist_data:
        items = server.search_for_music_track_by_name(entry.track)

        for item in items:
            artist = Utilities.select_artist(item)

            artist_score = fuzz.ratio(artist, entry.artist)
            album_score = fuzz.ratio(item['Album'], entry.album)
            track_score = fuzz.ratio(item['Name'], entry.track)

            score = artist_score + album_score + track_score

            item['Score'] = score

        items = sorted(items, key=lambda x: x['Score'], reverse=True)

        if len(items) == 0:
            string = (f'No matches found for {entry.artist} - '
                      f'{entry.album} - {entry.track}')
            print(string)
            no_matches.append(entry)
            continue

        match = items[0]

        if match['Score'] <= 150:
            low_scores.append((entry, match))
            print('Low score for match "{:s} - {:s} - {:s}" to query '
                  '"{:s} - {:s} - {:s}" with score {:.0f}'.format(
                Utilities.select_artist(match), match['Album'], match['Name'],
                entry.artist, entry.album, entry.track, match['Score']))
            continue

        print('Matching "{:s} - {:s} - {:s}" to query "{:s} - {:s} - {:s}" '
              'with score {:.0f}'.format(Utilities.select_artist(match),
                                         match['Album'], match['Name'],
                                         entry.artist, entry.album, entry.track,
                                         match['Score']))

        server.add_item_to_playlist(playlist_id, match['Id'])

    with open('match issues.txt', 'w') as f:
        f.write('No Matches:\n')

        for entry in no_matches:
            string = f'{entry.artist} - {entry.album} - {entry.track}'
            f.write(string + '\n')

        f.write('\nLow Scores:\n')

        for (entry, match) in low_scores:
            string = ('Query: "{:s} - {:s} - {:s}", '
                      'Match: "{:s} - {:s} - {:s}", '
                      'Score: {:.0f}\n').format(entry.artist, entry.album,
                                                entry.track,
                                                Utilities.select_artist(match),
                                                match['Album'], match['Name'],
                                                match['Score'])
            f.write(string)


def remove_duplicates():
    config, server = Utilities.load_config_and_login()

    playlist_id = server.get_playlist_id_from_name(
        config.get('jellyfin', 'playlist name'))

    items = server.get_playlist_items(playlist_id)

    items_to_delete = []
    count = 0

    last_item = None
    for item in items:
        if last_item is None:
            last_item = item
            continue

        if item['Id'] == last_item['Id']:
            items_to_delete.append(item)

        if len(items_to_delete) > 25:
            server.remove_items_from_playlist(playlist_id, items_to_delete)
            items_to_delete = []
            count += 25

        last_item = item

    if len(items_to_delete) > 0:
        server.remove_items_from_playlist(playlist_id, items_to_delete)
        count += len(items_to_delete)

    print(f'Removed {count} items')




def fix_genres(root_dir):
    """
    This function corrects bad genre delimiters and removes bad genre tags
    from a specified list. Unlike other functions, this function doesn't use
    the Jellyfin API and instead interacts with the filesystem directly.
    """

    root_path = Path(root_dir)
    if not root_path.exists():
        print(f'Directory {root_dir} not found.')
        return

    count = 0
    for dirpath, _, filenames in root_path.walk():
        for filename in filenames:
            file_path = dirpath / filename
            if file_path.suffix.lower() in ['.flac', '.mp3']:
                if Utilities.fix_genre_tag(file_path):
                    print(f'Updated: {file_path}')
                    count += 1

    print(f'Done. Updated genre tags in {count} files.')
