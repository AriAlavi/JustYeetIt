from network import *
from hosts import *
from download_queue import *
import eel
import multiprocessing


@eel.expose
def hostServer(server_ip):
    global hosting
    try:
        # server(server_ip, 5003)
        p = multiprocessing.Process(target=server, args=(server_ip, 5003))
        hosting = True
        p.start()
        return True
    except Exception as e:
        print(e)
        return False

@eel.expose
def checkHosting():
    global hosting
    return hosting

@eel.expose
def getFiles(ip):
    client = Client(ip, 5003)
    eel.sleep(.5)
    try:
        return client.getFileList()
    except:
        return []

@eel.expose
def getQueue():
    return [x.toJson() for x in generate_hash_lists()]
    
@eel.expose
def addToQueue(file_name, ip, port=5003):
    client = Client(ip, port)
    filesize = client.requestFileSize(file_name)
    progress = DownloadProgress(file_name, filesize, ip, port)

    call = {
        "function" : "add",
        "args" : (progress,),
    }
    action_queue.put(call)
    return True

@eel.expose
def removeFromQueue(uniqueHash):
    call = {
        "function" : "remove",
        "args" : (uniqueHash,),
    }
    action_queue.put(call)
    
@eel.expose
def pauseQueueAlternate(uniqueHash):
    call = {
        "function" : "pause",
        "args" : (uniqueHash,),
    }
    action_queue.put(call)
    return True

def runDownloadQueue(action_queue, shared_list):
    dq = DownloadQueue(action_queue, shared_list)
    dq.run()



def main():
    multiprocessing.freeze_support()
    global DOWNLOAD_QUEUE
    global generate_hash_lists
    global action_queue
    global hosting
    print("Starting setup...")
    hosting = False
    setup()
    print("Setup complete")
    print("Starting queues...")
    # download_q = Process(target=downloadQDownloader, args=())
    action_queue = multiprocessing.Manager().Queue()
    shared_list = multiprocessing.Manager().list()
    print("Queues complete")
    DOWNLOAD_QUEUE = DownloadQueue(action_queue, shared_list)
    generate_hash_lists = DownloadQueue.HashListGenerator(shared_list)
    print("Starting eel...")
    eel.init('gui')
    eel.start('main.html', block=False, port=0)
    print("Eel complete")
    print("Starting other process...")
    p = multiprocessing.Process(target=runDownloadQueue, args=(action_queue, shared_list))
    p.start()
    print("Process complete")
    print("Now useable")
    try:
        while True:
            eel.sleep(120)
    finally:
        action_queue.put({
                "function" : "stop",
                "args" : ()
            })
        print("Execution complete")
if __name__ == "__main__":
    main()
