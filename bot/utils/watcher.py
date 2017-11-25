import logging

import watchdog

from bot import logger
import datetime
import threading
import time
from abc import abstractmethod

import os
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from watchdog.events import PatternMatchingEventHandler

# TODO: away from watcher and make the class sync with it file system
"""
TODO this ->
    def lock(self):
        self.eventLock.acquire()
        self.runnable = False
        self.eventLock.release()

    def unlock(self):
        self.eventLock.acquire()
        self.runnable = True
        self.eventLock.release()

    def scheduleunlock(self):
        when = datetime.datetime.now() + datetime.timedelta(seconds=4)
        self.sched.add_job(self.unlock, trigger='date', id='unlock_file at %s' % (
            when.isoformat()), run_date=when)

    def check_runat(self):
        next_run_at = read_data_file()
        if 'runnow' in next_run_at and next_run_at['runnow'] is True:
            self.root.debug("Forcing run now")
            if self.thread is None:
                self.sched.remove_all_jobs()
                self.sched.add_job(main, id='cron_main_force')
            else:
                self.root.debug("Thread is currently running")
            next_run_at['runnow'] = False
            write_data_file(next_run_at)

    def check_stop(self):
        data = read_data_file()
        if self.thread is None:
            data.stop = False
            write_data_file(data)
            return
        if 'stop' in data and data['stop'] is True:
            for x in threading.enumerate():
                if x == self.thread:
                    x.do_run = False
            self.root.debug("Emitting stop event")
            data.stop = False
            write_data_file(data)
        elif 'stop' in data and data['stop'] is False:
            self.root.debug("Emitting resume event")
        
       if self.runnable:
            self.lock()
            self.check_runat()
            self.check_stop()
            self.scheduleunlock()
   runnable = True
    thread = None
    sched = None
    eventLock = threading.Lock()
"""


# IMPLEMENTATION: set so this gives event notifications

class WatchFile(PatternMatchingEventHandler):
    root = logging.getLogger("bot.watcher")

    def on_moved(self, event):
        super(WatchFile, self).on_moved(event)
        self.root.debug("File %s was just moved" % event.src_path)

    def on_created(self, event):
        super(WatchFile, self).on_created(event)
        self.root.debug("File %s was just created" % event.src_path)

    def on_deleted(self, event):
        super(WatchFile, self).on_deleted(event)
        self.root.debug("File %s was just deleted" % event.src_path)

    def on_modified(self, event):
        super(WatchFile, self).on_modified(event)
        self.root.debug("File %s was just modified" % event.src_path)

    def on_any_event(self, event):
        super(WatchFile, self).on_modified(event)
        self.notify_event(event)

    def notify_event(self, event):
        self.root.debug(str(event))
        self.event_notification(event)

    @abstractmethod
    def event_notification(self, event):
        raise NotImplementedError("event notification not ready")


class SyncWithFile(WatchFile):
    _observer = None

    @property
    def observer(self):
        return self._observer

    @observer.setter
    def observer(self, observer):
        self._observer = observer

    _file_observing = None

    @property
    def file_observing(self):
        return self._file_observing

    @file_observing.setter
    def file_observing(self, value):
        self._file_observing = value

    def event_notification(self, event):
        """ HANDLES ROUTING OF WATCHDOG EVENT TYPES, SOME EDITORS MOVE TO TEMP FILES TO WRITE"""
        # TODO LP Investigate other possible file modifications
        if isinstance(event, watchdog.events.FileModifiedEvent):
            self.settings_modified(event)
        elif isinstance(event, watchdog.events.FileMovedEvent):
            if event.dest_path == self.file_observing:
                self.settings_modified(event)
        else:
            self.root.debug("Event type {} is not handled".format(type(event)))

    @abstractmethod
    def settings_modified(self, events):
        raise NotImplementedError("settings_modified not implemented")

    def __init__(self, file, auto_start=False):
        self.watcher = WatchFile(patterns=[file])
        self.watcher.event_notification = self.event_notification
        self.file_observing = file
        if auto_start:
            self.start_observer()

    def start_observer(self):
        self.observer = Observer()
        self.observer.schedule(self.watcher, os.path.dirname(self.file_observing), recursive=False)
        self.observer.start()

    def stop_observer(self):
        self.observer.stop()


if __name__ == "__main__":
    data_file = r"D:\Sync\OneDrive\Yu-gi-oh_bot\run_at.json"
    syncer = SyncWithFile(data_file, auto_start=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        syncer.stop_observer()
    syncer.observer.join()