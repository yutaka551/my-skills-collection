# YouTube Music Skill

## Overview
This skill allows you to search for songs and manage playlists on YouTube Music using Python scripts. It provides functionality to search for songs, create playlists, add songs to playlists, list playlists, and retrieve songs from a specific playlist.

## Usage
- Search for songs by title or artist
- Create new playlists
- Add songs to existing playlists
- List all playlists
- Get songs from a specific playlist by ID

## Constraints
- **Do not create new Python scripts or programs.**
- Execute tasks exclusively by calling the existing scripts (`song_search.py` and `playlist_manager.py`) as shown in the examples.
- For complex tasks, combine multiple command calls in sequence.
- Temporary files and helper scripts (if any) must be created inside a session directory under `tmp/` — for example `tmp/<session-id>/`. Remove that directory and all its contents when the task is finished.
- Session-temp utilities for creating/cleaning session directories are centralized in `scripts/playlist_manager.py`; other scripts import these utilities instead of re-implementing them.

> Note: 一時ファイルは必ず `tmp/<session-id>/` 配下に作成し、作業完了時に削除してください。

## Triggers
- `search_song`: Search for a song by title or artist
- `create_playlist`: Create a new playlist
- `add_to_playlist`: Add a song to an existing playlist
- `remove_from_playlist`: Remove a song from an existing playlist
- `list_playlists`: List all playlists
- `get_playlist_songs`: Retrieve songs from a playlist by ID

## Requirements
Python 3
ytmusicapi library (install with pip)
  - Install: `pip install ytmusicapi`
YTMUSIC_HEADERS environment variable set with path to YouTube Music authentication headers

## Examples
Search for "Shape of You" by Ed Sheeran: `python song_search.py "Shape of You" "Ed Sheeran"`
Create a playlist: `python playlist_manager.py create "My Favorites"`
Add a song to playlist: `python playlist_manager.py add "My Favorites" "Blinding Lights" "The Weeknd"`
Remove a song from playlist: `python playlist_manager.py remove "My Favorites" "Blinding Lights" "The Weeknd"`
List playlists: `python playlist_manager.py list`
Get songs from playlist: `python playlist_manager.py get "PLAYLIST_ID"`

---

See scripts/ for implementation details.
