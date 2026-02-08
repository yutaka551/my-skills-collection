# Playlist management script for YouTube Music Skill
# Requires ytmusicapi

from ytmusicapi import YTMusic
import sys
import os

# Usage: python playlist_manager.py <action> <playlist_name> [<song_name> <artist_name>]
# Actions: create <playlist_name>, add <playlist_name> <song_name> [<artist_name>], list, get <playlist_id>
def get_ytmusic():
    headers_path = os.environ.get("YTMUSIC_HEADERS")
    if not headers_path:
        print("Error: YTMUSIC_HEADERS environment variable not set.")
        sys.exit(1)
    return YTMusic(headers_path)

def create_playlist(playlist_name):
    ytmusic = get_ytmusic()
    playlist_id = ytmusic.create_playlist(playlist_name, "Created by YouTube Music Skill")
    print(f"Playlist '{playlist_name}' created with ID: {playlist_id}")

def add_song_to_playlist(playlist_name, song_name, artist_name=None):
    ytmusic = get_ytmusic()
    playlists = ytmusic.get_library_playlists()
    playlist_id = next((pl['playlistId'] for pl in playlists if pl['title'] == playlist_name), None)
    if not playlist_id:
        print(f"Playlist '{playlist_name}' not found.")
        return
    query = song_name if not artist_name else f"{song_name} {artist_name}"
    results = ytmusic.search(query, filter="songs")
    if not results:
        print("Song not found.")
        return
    song_id = results[0]['videoId']
    ytmusic.add_playlist_items(playlist_id, [song_id])
    print(f"Added '{song_name}' to playlist '{playlist_name}'.")

def list_playlists():
    ytmusic = get_ytmusic()
    playlists = ytmusic.get_library_playlists(limit=None)
    for pl in playlists:
        print(f"{pl['title']} (ID: {pl['playlistId']})")

def get_playlist_songs(playlist_id):
    ytmusic = get_ytmusic()
    playlist_data = ytmusic.get_playlist(playlist_id, limit=None)
    songs = playlist_data.get('tracks', [])
    return songs

def main():
    if len(sys.argv) < 2:
        print("Usage: python playlist_manager.py <action> <playlist_name> [<song_name> <artist_name>]")
        print("Actions: create <playlist_name>, add <playlist_name> <song_name> [<artist_name>], list, get <playlist_id>")
        sys.exit(1)
    action = sys.argv[1]
    if action == "create":
        create_playlist(sys.argv[2])
    elif action == "add":
        if len(sys.argv) < 4:
            print("Usage: python playlist_manager.py add <playlist_name> <song_name> [<artist_name>]")
            sys.exit(1)
        add_song_to_playlist(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    elif action == "list":
        list_playlists()
    elif action == "get":
        if len(sys.argv) < 3:
            print("Usage: python playlist_manager.py get <playlist_id>")
            sys.exit(1)
        songs = get_playlist_songs(sys.argv[2])
        for song in songs:
            print(f"{song['title']} by {song['artists'][0]['name']}")
    else:
        print("Unknown action.")

if __name__ == "__main__":
    main()
