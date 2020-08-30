
import socket
import time
import sys
import asyncio
import pickle
import re
import os
from collections import OrderedDict
from statistics import mean

BYTES_TO_SEND = 1024 * 1024 * 128 # 128 megabytes
FILES_LOCATION = "files"
INCOMPLETE_FILES_LOCATION = "incomplete"


class BufferInstance():
    def __init__(self, size):
        self.size = size
        self.attempts = []
    def mean(self) -> float:
        if len(self.attempts) == 0:
            return 0
        return mean(self.attempts)

    def add(self, time: float):
        self.attempts.append(time)
    def __str__(self):
        return "{} size with {} time, in {}".format(self.size, self.mean(), len(self.attempts))
    def __repr__(self):
        return str(self)

class BufferSize:
    def __init__(self, initial=1024):
        assert initial % 1024 == 0
        self.size = initial
        self.history = []
        self.history_dict = {}
        self.tries = 0
        self.calibrations_made = 0
        self.MAX_CALIBRATION_ACCURACY = 128
    def addHistory(self, time):
        if self.calibrations_made >= self.MAX_CALIBRATION_ACCURACY:
            return
        if not self.size in self.history_dict.keys():
            self.history_dict[self.size] = BufferInstance(self.size)
            self.history.append(self.history_dict[self.size])
        self.history_dict[self.size].add(time)
        self.tries += 1
    def getSize(self):
        if self.tries < 3 or self.calibrations_made >= self.MAX_CALIBRATION_ACCURACY:
            return self.size
        else:
            self.tries = 0
            self.history.sort(key=lambda x: x.mean())
            if len(self.history) == 1:
                self.size = self.size * 2
            else:
                if self.history[0].size == self.size:
                    if self.history[0].size >= max(x.size for x in self.history):
                        self.size = self.size * 2
                    else:
                        self.size = (self.history[1].size + self.history[0].size) // 2
                elif self.history[1].size == self.size:
                    self.size = (self.history[1].size + self.history[0].size) // 2
                else:
                    self.size = self.history[0].size
        self.calibrations_made += 1
        return self.size
    def __str__(self):
        return str(self.size)
    def __repr__(self):
        return str(self)

        

class Server:
    async def sendInt(self, w, givenInt: int):
        assert givenInt > 0
        data_length_in_bytes = givenInt.to_bytes(7, byteorder="big") # Please don't use files larger than 1 Pentabyte, thank you
        w.write(data_length_in_bytes)
        await w.drain()
    async def recvInt(self, r) -> int:
        data_length_in_bytes = await r.read(7)
        return int.from_bytes(data_length_in_bytes, byteorder="big")
    async def recvStr(self, r) -> str:
        data_length = await self.getDataLength(r)
        BYTES_PER_TICK = 1024
        bytes_got = 0
        chunks = []
        while bytes_got < data_length:
            bytes_to_get = min(BYTES_PER_TICK, data_length - bytes_got)
            current = await r.read(bytes_to_get)
            chunks.append(current)
            bytes_got += len(current)
        return (b"".join(chunks)).decode()
    async def sendDataLength(self, w, data):
        await self.sendInt(w, len(data))
    async def getDataLength(self, r):
        assert isinstance(r, asyncio.StreamReader)
        return await self.recvInt(r)
    async def sendBool(self, w, givenBool):
        assert isinstance(givenBool, bool)
        if givenBool:
            data = "\x01"
        else:
            data = "\x00"
        w.write(data)
        await w.drain()

    async def getFileList(self, r, w):
        files = []
        for file in os.listdir(FILES_LOCATION):
            if os.path.isfile(os.path.join(FILES_LOCATION, file)):
                files.append(file)
        pickled_files = pickle.dumps(files)
        await self.sendDataLength(w, pickled_files)
        w.write(pickled_files)
        await w.drain()
    async def sendFile(self, r, w):
        assert isinstance(w, asyncio.StreamWriter)
        file_name = await self.recvStr(r)
        assert file_name in os.listdir(FILES_LOCATION)
        file_path = os.path.join(FILES_LOCATION, file_name)
        starting_byte = await self.recvInt(r)
        file_length = os.stat(file_path).st_size
        bytes_remain = file_length - starting_byte
        if bytes_remain > BYTES_TO_SEND:
            bytes_remain = BYTES_TO_SEND

        await self.sendInt(w, file_length)
        await self.sendInt(w, bytes_remain)

        file = open(file_path, "rb")
        file.seek(starting_byte)
        w.write(file.read(bytes_remain))
        await w.drain()

    async def sendFileSize(self, r, w):
        file_name = await self.recvStr(r)
        assert file_name in os.listdir(FILES_LOCATION)
        file_path = os.path.join(FILES_LOCATION, file_name)
        file_length = os.stat(file_path).st_size
        await self.sendInt(w, file_length)

    BYTE_MAP = {
        b"\x00" : getFileList,
        b"\x01" : sendFile,
        b"\x02" : sendFileSize,
        }
    async def _handle_client(self, r, w):
        assert isinstance(r, asyncio.StreamReader)
        assert isinstance(w, asyncio.StreamWriter)
        try:
            func = self.BYTE_MAP[await r.read(1)]
            await func(self, r, w)
        except ConnectionResetError:
            pass
        

    async def run(self, host_ip, port):
        self.HOST_IP = host_ip
        self.PORT = port
        print("Ready to receive connections on {}:{}".format(self.HOST_IP, self.PORT))
        await asyncio.start_server(self._handle_client, self.HOST_IP, self.PORT)

def checkCorrectFile(base_file, checking_file) -> bool:
    assert isinstance(base_file, str)
    assert isinstance(checking_file, str)
    if checking_file[:len(base_file)] != base_file: # bob.txt vs knob.txt
        return False
    if "." in base_file:
        if checking_file.count(".") != base_file.count(".") + 1: # bob.png vs bob.1 , .bob.png vs .bob.1
            return False
        checking_extension = checking_file.split(".")[-2]
        base_extension = base_file.split(".")[-1]
        if checking_extension != base_extension: # bob.png vs bob.jpg
            return False
    else:
        if checking_file.count(".") != 1: # bob vs bob.png.1
            return False

    if "." != checking_file[len(base_file):len(base_file)+1]: # bob.png vs bobb.png
        return False

    return True
        
class Client:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.buffer = BufferSize(1024)
    def getSocket(self) -> socket.socket:
        s = socket.socket()
        s.connect((self.ip, self.port))
        return s
    def sendInt(self, s, givenInt: int):
        data_length_in_bytes = givenInt.to_bytes(7, byteorder="big") # Please don't use files larger than 1 Pentabyte, thank you
        s.send(data_length_in_bytes)
    def recvInt(self, s):
        int_in_bytes = s.recv(7)
        return int.from_bytes(int_in_bytes, byteorder="big")
   
    def sendDataLength(self, s, data):
        assert isinstance(s, socket.socket)
        self.sendInt(s, len(data))
    def recvBool(self, s) -> bool:
        assert isinstance(s, socket.socket)
        given_bool = s.recv(1)
        if given_bool == b"x\00":
            return False
        elif given_bool == b"x\01":
            return True
        else:
            raise Exception("{} is not a valid boolean".format(given_bool))
    def sendStr(self, s, givenString: str):
        as_bytes = givenString.encode()
        self.sendDataLength(s, as_bytes)
        s.send(as_bytes)

    def hangForever(self):
        while True:
            time.sleep(120)

    def getDataLength(self, s) -> int:
        assert isinstance(s, socket.socket)
        return self.recvInt(s)

    def getFileList(self):
        s = self.getSocket()
        s.send(b"\x00")
        file_size_length = self.getDataLength(s)
        bytes_got = 0
        chunks = []
        while bytes_got < file_size_length:
            bytes_to_get = min(1024, file_size_length - bytes_got)
            current = s.recv(bytes_to_get)
            chunks.append(current)
            bytes_got += len(current)
        byte_data =  b"".join(chunks)
        s.close()
        return pickle.loads(byte_data)
    def getTempFiles(self, file_name):
        assert isinstance(file_name, str)
        temp_files = []
        for current_file_name in os.listdir(INCOMPLETE_FILES_LOCATION):
            if checkCorrectFile(file_name, current_file_name):
                temp_files.append(os.path.join(INCOMPLETE_FILES_LOCATION, current_file_name))
        if len(temp_files) == 0:
            return []
        temp_files.sort(key=lambda x: int(x.split(".")[-1]))
        last = temp_files.pop()
        if os.stat(last).st_size == BYTES_TO_SEND:
            temp_files.append(last)
        try:
            assert all(os.stat(file_path).st_size == BYTES_TO_SEND for file_path in temp_files)
        except Exception:
            print("Files for {} corrupted!".format(file_name))
            self.hangForever()
            
        return temp_files

    def requestFile(self, file_name, **kwargs):
        from download_queue import DownloadProgress
        assert isinstance(file_name, str)
        progress = kwargs.get("progress", None)
        interrupt = kwargs.get("interrupt", None)
        action_queue = kwargs.get("action_queue", None)
        if progress:
            assert isinstance(progress, DownloadProgress)
            assert progress and interrupt and action_queue
        MASTER_FILE_PATH = os.path.join(FILES_LOCATION, file_name)
        TEMP_FILE_PATH = os.path.join(INCOMPLETE_FILES_LOCATION, file_name)
        temp_files = self.getTempFiles(file_name)
        if temp_files:
            starting_byte = (len(temp_files)) * BYTES_TO_SEND
        else:
            starting_byte = 0

        file_length = None
        while (not file_length or starting_byte < file_length) and (not progress or not progress.paused):
            s = self.getSocket()
            s.send(b"\x01")
            self.sendStr(s, file_name)
            self.sendInt(s, starting_byte)
            file_length = self.recvInt(s)
            to_recieve_length = self.recvInt(s)
            overall_download_length = starting_byte
            bytes_recieved = 0
            temp_file_name = TEMP_FILE_PATH + ".{}".format(len(temp_files))
            file = open(temp_file_name, "wb")
            i = 0
            new_buffer_size_start = (self.buffer.getSize() // 1024) * 1024
            self.buffer = BufferSize(new_buffer_size_start)
            last_called_download_speed_tracker = time.time()
            total_bytes_download_speed_tracker = 0
            while bytes_recieved < to_recieve_length:
                time_before = time.time()
                buffer_size = self.buffer.getSize()
                data = s.recv(buffer_size)
                self.buffer.addHistory(time.time() - time_before )
                i += 1
                if i % 1000 == 0:
                    if progress:
                        download_speed = total_bytes_download_speed_tracker / (time.time() - last_called_download_speed_tracker + .0001)
                        last_called_download_speed_tracker = time.time()
                        total_bytes_download_speed_tracker = 0
                        progress.setDownloaded(overall_download_length + bytes_recieved, download_speed)
                        action_queue.put({
                            "function" : "save",
                            "args" : ()
                        })
                bytes_recieved += len(data)
                total_bytes_download_speed_tracker += len(data)
                file.write(data)
                if interrupt and interrupt.interrupt:
                    raise Exception("Interrupted")
            starting_byte += bytes_recieved
            
            file.close()
            temp_files.append(temp_file_name)
            s.close()
        if progress and progress.paused:
            return False
        master_file = open(MASTER_FILE_PATH, "wb")
        for temp_file in temp_files:
            file = open(temp_file, "rb")
            master_file.write(file.read())
            file.close()
        master_file.close()
        for temp_file in temp_files:
            os.remove(temp_file)
        if progress:
            progress.complete = True
            action_queue.put({
                "function" : "pause",
                "args" : (progress.uniqueHash(),)
            })
        return True

    def requestFileSize(self, file_name):
        assert isinstance(file_name, str)
        s = self.getSocket()
        s.send(b"\x02")
        self.sendStr(s, file_name)
        return self.recvInt(s)
        

def yesNoValidator(obj):
    if obj in ["y", "n"]:
        return True
    return False

def validateIP(givenIp):
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",givenIp):
        return True
    return False
    


def menu(prompt, validator, useClipboard=False):
    import pyperclip
    if useClipboard:
        input(prompt)
        result = pyperclip.paste()
    else:
        result = input(prompt + "\n")
    while not validator(result):
        if useClipboard:
            print("{} is invalid".format(pyperclip.paste()))
        else:
            print("Invalid input!")
        if useClipboard:
            input(prompt)
            result = pyperclip.paste()
        else:
            result = input(prompt + "\n")
    return result


def server(host_ip, port):
    loop = asyncio.get_event_loop()
    server = Server()
    loop.run_until_complete(server.run(host_ip, port))
    loop.run_forever()



def client(host_ip, port):
    client = Client(host_ip, port)
    file_list = client.getFileList()
    file_to_get = file_list[0]
    client.requestFile(file_to_get)


def setup():
    if not os.path.isdir(FILES_LOCATION):
        os.mkdir(FILES_LOCATION)
    if not os.path.isdir(INCOMPLETE_FILES_LOCATION):
        os.mkdir(INCOMPLETE_FILES_LOCATION)





