from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from rich.markup import escape

from plextraktsync.decorators.flatten import flatten_dict
from plextraktsync.factory import logging
from plextraktsync.media import Media

if TYPE_CHECKING:
    from plexapi.playlist import Playlist
    from plexapi.server import PlexServer

    from plextraktsync.plex.types import PlexMedia


class PlexPlaylist:
    def __init__(self, server: PlexServer, name: str):
        self.server = server
        self.name = name
        self.logger = logging.getLogger("PlexTraktSync.PlexPlaylist")

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items.keys())

    def __contains__(self, m: Media):
        return m.plex_key in self.items

    @cached_property
    def playlist(self) -> Playlist | None:
        try:
            playlists = self.server.playlists(title=self.name, title__iexact=self.name)
            playlist: Playlist = playlists[0]
            if len(playlists) > 1:
                self.logger.warning(f"Found multiple playlists ({len(playlists)}) with same name: '{self.name}', "
                                    f"Using first playlist with id {playlist.ratingKey}")
            self.logger.debug(f"Loaded plex list: '{self.name}'")
            return playlist
        except IndexError:
            self.logger.debug(f'Unable to find Plex playlist with title "{self.name}".')
            return None

    @cached_property
    @flatten_dict
    def items(self) -> dict[int, PlexMedia]:
        if self.playlist is None:
            return
        for m in self.playlist.items():
            yield m.ratingKey, m

    def update(self, items: list[PlexMedia], description=None) -> bool:
        """
        Updates playlist (creates if name missing) replacing contents with items[]
        """
        playlist = self.playlist
        if playlist is None and len(items) > 0:
            # Force reload
            del self.__dict__["playlist"]
            del self.__dict__["items"]
            playlist = self.server.createPlaylist(self.name, items=items)
            self.logger.info(f"Created plex playlist '{self.name}' with {len(items)} items")

        # Skip if playlist could not be made/retrieved
        if playlist is None:
            return False

        updated = False
        if description is not None and description != playlist.summary:
            playlist.editSummary(summary=description)
            self.logger.debug(f"Updated '{self.name}' description: {description}")
            updated = True

        # Skip if nothing to update
        if self.same_list(items, playlist.items()):
            return updated

        playlist.removeItems(playlist.items())
        playlist.addItems(items)
        self.logger.debug(f"Updated '{self.name}' items")

        return True

    @property
    def title_link(self):
        if self.playlist is not None:
            link = self.playlist._getWebURL()

            return f"[link={link}][green]{escape(self.name)}[/][/]"

        return f"[green]{escape(self.name)}[/]"

    @staticmethod
    def same_list(list_a: list[PlexMedia], list_b: list[PlexMedia]) -> bool:
        """
        Return true if two list contain same Plex items.
        The comparison is made on ratingKey property,
        the items don't have to actually be identical.
        """

        # Quick way out of lists with different length
        if len(list_a) != len(list_b):
            return False

        a = [m.ratingKey for m in list_a]
        b = [m.ratingKey for m in list_b]

        return a == b
