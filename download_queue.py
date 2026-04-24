import pickle
from network import INCOMPLETE_FILES_LOCATION, checkCorrectFile, Client
from multiprocessing import Queue, Manager
from threading import Thread
import os
import sys
import time
import asyncio
import json
import eel


DOWNLOAD_QUEUE_FILENAME = "downloads.pickle"
INTERRUPTED_SENTINEL = "INTERRUPTED"


class DownloadProgress:
    def __init__(self, filename, filesize, serverIP, serverPort=5003):
        assert isinstance(filename, str)
        assert isinstance(filesize, int)
        assert isinstance(serverIP, str)
        assert isinstance(serverPort, int)
        self.filename = filename
        self.downloaded = 0
        self.filesize = filesize
        self.serverIP = serverIP
        self.serverPort = serverPort
        self.download_speed = 0
        self.paused = False
        self.complete = False

    def uniqueHash(self):
        data = (
            "f{}{}{}".format(self.filename, self.serverIP, self.serverPort)
            .replace("#", "h")
            .replace(".", "d")
            .replace(" ", "_")
        )
        return "".join(
            [
                s
                for s in data
                if s in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890"
            ]
        )

    def delete(self):
        global INCOMPLETE_FILES_LOCATION
        for file_name in os.listdir("."):
            if checkCorrectFile(self.filename, file_name) and os.path.isfile(file_name):
                os.remove(file_name)

    def setDownloaded(self, byte_count, download_speed):
        assert isinstance(byte_count, int)
        assert isinstance(download_speed, float)
        self.downloaded = byte_count
        self.download_speed = download_speed

    # def download(self, download_queue):
    #     client = Client(self.serverIP, self.serverPort)
    #     client.requestFile(self.filename)
    def getPrecent(self) -> float:
        return self.downloaded / self.filesize

    def getTimeRemains(self) -> str:
        if self.complete:
            return 0
        if self.download_speed == 0:
            return -1
        time = (self.filesize - self.downloaded) / self.download_speed
        return time
        # SECOND = 1
        # MINUTE = SECOND * 60
        # HOUR = MINUTE * 60
        # DAY = HOUR * 24
        # WEEK = DAY * 7
        # NAME_LIST = ("Week", "Day", "Hour", "Minute", "Second")
        # NAME_DENOMINATIONS = (WEEK, DAY, HOUR, MINUTE, SECOND)
        # times = []
        # for i in range(len(NAME_DENOMINATIONS)):
        #     name = NAME_LIST[i]
        #     denomination = NAME_DENOMINATIONS[i]
        #     if time > denomination:
        #         counts = time // denomination
        #         time = time % denomination
        #         if counts > 1:
        #             name += "s"

        #         name = "{} {}".format(counts, name)
        #         times.append(name)
        # while len(times) > 2:
        #     times.pop()

        # return ", ".join(times)

    def toJson(self) -> str:
        data = {
            "filename": self.filename,
            "downloaded": self.downloaded,
            "filesize": self.filesize,
            "speed": self.download_speed,
            "ip": self.serverIP,
            "hash": self.uniqueHash(),
            "paused": self.paused,
            "percent": self.getPrecent(),
            "complete": self.complete,
            "remains": self.getTimeRemains(),
        }
        if self.complete:
            data["percent"] = 1
        return json.dumps(data)


class DownloadQueue:
    def __init__(self, actionQ, sharedList):
        self.data = []
        self.threads = []
        self.actionQ = actionQ
        self.sharedList = sharedList
        self._closed = False
        self.running = True
        self.last_save = 0
        self.kill = None
        self.interrupt = Interrupt()
        self.__load()

    def __load(self):
        print(os.getcwd())
        if not os.path.isfile(DOWNLOAD_QUEUE_FILENAME):
            return
        file = open(DOWNLOAD_QUEUE_FILENAME, "rb+")
        self.data = pickle.load(file)
        file.close()
        self.update()

    def update(self):
        while len(self.sharedList) > 0:
            self.sharedList.pop()
        self.sharedList.extend(self.data)

    def killDownloads(self):
        # Signal all active threads to stop using their current interrupt object,
        # then move threads to a background list. We do NOT join here to avoid
        # blocking run() while download threads drain the action queue.
        self.interrupt.execute()
        old_threads = self.threads
        old_interrupt = self.interrupt
        self.threads = []
        self.interrupt = Interrupt()

        def _reap(threads, interrupt):
            for t in threads:
                t.join(timeout=30)
                if t.is_alive():
                    print("Warning: download thread did not stop within 30s")
            interrupt.interrupt = False

        Thread(target=_reap, args=(old_threads, old_interrupt), daemon=True).start()

    def createDownloads(self):
        downloads = getToDownload(self.data)
        for download in downloads:
            thread = Thread(
                target=downloadFromProgress,
                args=(download, self.interrupt, self.actionQ, self),
                daemon=True,
            )
            self.threads.append(thread)
            thread.start()

    def save(self, forced=False):
        if (not forced) and time.time() - self.last_save < 1:
            return
        self.last_save = time.time()
        self.update()
        with open(DOWNLOAD_QUEUE_FILENAME, "wb") as file:
            pickle.dump(list(self.data), file)

    def findFromUniqueHash(self, uniqueHash):
        assert isinstance(uniqueHash, str)
        for x in self.data:
            if x.uniqueHash() == uniqueHash:
                return x
        return None

    def add(self, downloadProgress):
        assert isinstance(downloadProgress, DownloadProgress), "was {} instead".format(
            type(downloadProgress)
        )
        if not self.findFromUniqueHash(downloadProgress.uniqueHash()):
            self.data.append(downloadProgress)

    def remove(self, uniqueHash):
        assert isinstance(uniqueHash, str)
        obj = self.findFromUniqueHash(uniqueHash)
        if obj:
            self.data.remove(obj)

    def pause(self, uniqueHash):
        obj = self.findFromUniqueHash(uniqueHash)
        if obj:
            obj.paused = not obj.paused
        self.save()

    def complete(self, uniqueHash):
        obj = self.findFromUniqueHash(uniqueHash)
        if obj:
            obj.complete = True

    def stop(self):
        for x in self.data:
            x.download_speed = 0
        self.save(True)
        if self.kill is not None:
            self.kill.put(True)
        self.running = False
        self._closed = True

    @staticmethod
    def HashListGenerator(sharedList):
        last_result = []

        def hashList():
            nonlocal last_result
            current_result = list(sharedList)
            if len(current_result) == 0 and len(last_result) != 0:
                last_result = current_result
                return last_result
            last_result = current_result
            return current_result

        return hashList

    def kill_reference(self, interrupter):
        self.kill = interrupter

    FUNCTION_MAP = {
        "save": save,
        "add": add,
        "remove": remove,
        "stop": stop,
        "pause": pause,
        "complete": complete,
        "kill_reference": kill_reference,
    }
    STATE_CHANGING_FUNCTIONS = ["add", "remove", "pause", "complete"]

    def run(self):
        self.createDownloads()
        while self.running:
            try:
                action = self.actionQ.get(timeout=2)
            except Exception:
                # Timeout: use the idle cycle to persist state if needed
                self.save()
                continue
            print("Action got:", action)
            func_name = action["function"]
            func = self.FUNCTION_MAP[func_name]
            args = action["args"]
            assert callable(func)
            prev_to_download = getToDownload(self.data)
            func(*((self,) + args))
            if func_name in self.STATE_CHANGING_FUNCTIONS:
                self.save()
            post_to_download = getToDownload(self.data)

            if [x.uniqueHash() for x in prev_to_download] != [
                x.uniqueHash() for x in post_to_download
            ]:
                self.killDownloads()
                self.createDownloads()


class Interrupt:
    def __init__(self):
        self.interrupt = False

    def execute(self):
        self.interrupt = True


def getToDownload(givenList):
    assert isinstance(givenList, list)
    assert all(isinstance(x, DownloadProgress) for x in givenList)
    returnList = []
    serverList = []
    for x in givenList:
        if x.paused or x.complete:
            continue
        if x.serverIP in serverList:
            continue
        else:
            returnList.append(x)
            serverList.append(x.serverIP)
    return returnList


def downloadFromProgress(download_progress, interrupt, action_queue, download_queue):
    assert isinstance(download_progress, DownloadProgress)
    assert isinstance(interrupt, Interrupt)
    retry_delay = 10
    while True:
        if interrupt.interrupt:
            return
        try:
            client = Client(download_progress.serverIP, download_progress.serverPort)
            result = client.requestFile(
                download_progress.filename,
                progress=download_progress,
                interrupt=interrupt,
                action_queue=action_queue,
            )
            if result:
                break
            # result == False means the download was paused cleanly
            return
        except Exception as e:
            if interrupt.interrupt:
                return
            msg = str(e)
            if msg == INTERRUPTED_SENTINEL:
                return
            download_progress.download_speed = 0
            download_queue.update()
            print("Download error for {}: {}. Retrying in {} seconds...".format(
                download_progress.filename, msg, retry_delay
            ))
            for _ in range(retry_delay * 2):
                if interrupt.interrupt:
                    return
                time.sleep(0.5)
            retry_delay = min(retry_delay * 2, 120)


# def downloadQDownloader():
#     to_download = []
#     to_download_last = []
#     interrupt = Interrupt()
#     while True:
#         eel.sleep(1)
#         q = DownloadQueue()
#         to_download = getToDownload(q.q)
#         if [x.uniqueHash() for x in to_download] != [x.uniqueHash() for x in to_download_last]:
#             print("Download q change detected")
#             interrupt.execute()
#             interrupt = Interrupt()
#             # tasks = []
#             if len(to_download) == 0:
#                 continue
#             task = to_download[0]
#             try:
#                 downloadFromProgress(task, interrupt)
#             except:
#                 task.paused = True
#             # for download in to_download:
#             #     tasks.append(downloadFromProgress(download, interrupt))
#             # asyncio.gather(*tasks, return_exceptions=True)

#         to_download_last = to_download
