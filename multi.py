from download_queue import *
from multiprocessing import Process, Queue
import time

# def printList(arg):
#     assert isinstance(arg, DownloadQueue)
#     while True:
#         print(arg.hashList())
#         time.sleep(1)


# def pointerPrintList(arg):
#     while True:
#         print(arg.pointing.hashList())
#         time.sleep(1)

# class Pointer:
#     def __init__(self, pointing):
#         self.pointing = pointing


class Pointing:
    def __init__(self, q):
        # assert isinstance(q, Queue)
        while True:
            time.sleep(1)
            print(q.get())

if __name__ == "__main__":
    q = Queue()
    p = Process(target=Pointing, args=(q,))
    p.start()
    time.sleep(5)
    print("Putting in")
    q.put(1)
    q.put(2)
    q.put(3)
    print("Stopped")
    # a = DownloadQueue()
    # pointer = Pointer(a)
    # p = Process(target=pointerPrintList, args=(pointer,))
    # p.start()


    # time.sleep(5)
    # print("Add another")
    # dp = DownloadProgress("test", 100, "69.69", a, 5002)
    # a.add(dp)
    # print("IT IS", a.hashList())
    # time.sleep(5)
    # print("Removing it")
    # a.remove(dp.uniqueHash())