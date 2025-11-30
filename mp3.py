"""Simple command-line MP3 player using pygame.

This script loads MP3 files from a directory and provides an interactive
prompt for controlling playback. Commands include listing tracks,
playing by index, pausing, resuming, skipping, and quitting.

Dependencies
------------
- Python 3.9+
- pygame (for audio playback)

Usage examples
--------------
    python mp3.py --directory /path/to/music
    python mp3.py --directory /path/to/music --loop
"""

import argparse
import threading
import time
from pathlib import Path
from typing import List, Optional


def find_mp3_files(directory: Path) -> List[Path]:
    """Return a sorted list of MP3 files within the directory."""
    return sorted(directory.glob("*.mp3"))


class MP3Player:
    """Manage MP3 playback and playlist navigation."""

    def __init__(self, directory: Path, loop: bool = False) -> None:
        import pygame

        self.pygame = pygame
        self.tracks = find_mp3_files(directory)
        self.loop = loop
        self.current_index: Optional[int] = 0 if self.tracks else None
        self.state: str = "stopped"

        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        self.pygame.mixer.init()
        self._monitor = threading.Thread(target=self._monitor_playback, daemon=True)
        self._monitor.start()

    def list_tracks(self) -> None:
        if not self.tracks:
            print("No MP3 files found.")
            return

        for idx, track in enumerate(self.tracks):
            marker = "->" if idx == self.current_index and self.state == "playing" else "  "
            print(f"{marker} [{idx}] {track.name}")

    def play(self, index: Optional[int] = None) -> None:
        if not self.tracks:
            print("Playlist is empty.")
            return

        with self._lock:
            if index is not None:
                if index < 0 or index >= len(self.tracks):
                    print(f"Index {index} out of range.")
                    return
                self.current_index = index

            track = self.tracks[self.current_index]
            self.pygame.mixer.music.load(track)
            self.pygame.mixer.music.play()
            self.state = "playing"
            print(f"Playing: {track.name}")

    def pause(self) -> None:
        with self._lock:
            if self.state != "playing":
                print("Nothing is currently playing.")
                return
            self.pygame.mixer.music.pause()
            self.state = "paused"
            print("Paused.")

    def resume(self) -> None:
        with self._lock:
            if self.state != "paused":
                print("Player is not paused.")
                return
            self.pygame.mixer.music.unpause()
            self.state = "playing"
            print("Resumed.")

    def stop(self) -> None:
        with self._lock:
            self.pygame.mixer.music.stop()
            self.state = "stopped"
            print("Stopped.")

    def next_track(self) -> None:
        with self._lock:
            if self.current_index is None:
                print("No tracks available.")
                return
            self.current_index = (self.current_index + 1) % len(self.tracks)
            self._play_current()

    def previous_track(self) -> None:
        with self._lock:
            if self.current_index is None:
                print("No tracks available.")
                return
            self.current_index = (self.current_index - 1) % len(self.tracks)
            self._play_current()

    def status(self) -> None:
        if self.current_index is None:
            print("No track loaded.")
            return
        track = self.tracks[self.current_index]
        print(f"Track: {track.name}")
        print(f"State: {self.state}")

    def close(self) -> None:
        self._stop_event.set()
        self.pygame.mixer.music.stop()
        self.pygame.mixer.quit()

    def _play_current(self) -> None:
        track = self.tracks[self.current_index]
        self.pygame.mixer.music.load(track)
        self.pygame.mixer.music.play()
        self.state = "playing"
        print(f"Playing: {track.name}")

    def _monitor_playback(self) -> None:
        while not self._stop_event.is_set():
            time.sleep(0.5)
            with self._lock:
                if self.state != "playing":
                    continue
                if self.pygame.mixer.music.get_busy():
                    continue
                if self.current_index is None:
                    continue
                if self.current_index == len(self.tracks) - 1 and not self.loop:
                    self.state = "stopped"
                    continue
                self.current_index = (self.current_index + 1) % len(self.tracks)
                self._play_current()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Command-line MP3 player")
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path.cwd(),
        help="Directory containing MP3 files (default: current directory)",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Loop the playlist when reaching the end.",
    )
    return parser.parse_args()


def interactive_loop(player: MP3Player) -> None:
    print("Commands: play [index], pause, resume, stop, next, prev, list, status, quit")
    while True:
        try:
            command = input("mp3> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not command:
            continue

        parts = command.split()
        action = parts[0].lower()

        if action == "play":
            index = int(parts[1]) if len(parts) > 1 else None
            player.play(index)
        elif action == "pause":
            player.pause()
        elif action == "resume":
            player.resume()
        elif action == "stop":
            player.stop()
        elif action in {"next", "skip"}:
            player.next_track()
        elif action in {"prev", "previous"}:
            player.previous_track()
        elif action == "list":
            player.list_tracks()
        elif action == "status":
            player.status()
        elif action in {"quit", "exit"}:
            break
        else:
            print("Unknown command.")


def main() -> int:
    args = parse_args()
    directory = args.directory.expanduser().resolve()

    if not directory.exists() or not directory.is_dir():
        print(f"Directory not found: {directory}")
        return 1

    player = MP3Player(directory=directory, loop=args.loop)

    if not player.tracks:
        print("No MP3 files found in the specified directory.")
        return 1

    player.list_tracks()
    player.play(player.current_index)

    try:
        interactive_loop(player)
    finally:
        player.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
