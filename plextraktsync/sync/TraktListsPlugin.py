from __future__ import annotations

from typing import TYPE_CHECKING

from plextraktsync.decorators.measure_time import measure_time
from plextraktsync.factory import logging
from plextraktsync.plugin import hookimpl

if TYPE_CHECKING:
    from .plugin.SyncPluginInterface import (Media, SyncPluginManager,
                                             TraktUserListCollection)


class TraktListsPlugin:
    """
    Plugin handling syncing of Trakt lists.
    """
    logger = logging.getLogger(__name__)

    def __init__(self):
        self.trakt_lists = None
        self.add_to_lists = None

    @staticmethod
    def enabled(config):
        # Check for need is performed in init()
        return True

    @classmethod
    def factory(cls, sync):
        return cls()

    @hookimpl(trylast=True)
    def init(self, pm: SyncPluginManager, trakt_lists: TraktUserListCollection):
        self.trakt_lists = trakt_lists
        self.add_to_lists = not trakt_lists.is_empty
        # Skip updating lists if it's empty
        if trakt_lists.is_empty:
            self.logger.warning("Disabling TraktListsPlugin: No lists to process")
            pm.unregister(self)

    @hookimpl
    def fini(self, dry_run: bool):
        if dry_run or self.trakt_lists.is_empty:
            return

        with measure_time("Updated liked list"):
            self.trakt_lists.sync()

    @hookimpl
    def walk_movie(self, movie: Media):
        if not self.add_to_lists:
            return
        self.trakt_lists.add_to_lists(movie)

    @hookimpl
    def walk_episode(self, episode: Media):
        if not self.add_to_lists:
            return
        self.trakt_lists.add_to_lists(episode)
