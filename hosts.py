import pickle
import os
import eel

FILE_NAME = "hosts.pickle"

@eel.expose
def getHosts(raw=False):
    if os.path.isfile(FILE_NAME):
        file = open(FILE_NAME, "rb")
        data = pickle.load(file)
        file.close()
        if raw:
            return data
        return list(data)
    else:
        file = open(FILE_NAME, "wb")
        pickle.dump(set(), file)
        file.close()
        if raw:
            return set()
        return []

@eel.expose
def addHost(host_ip):
    print("Adding {}".format(host_ip))
    hosts = getHosts(True)
    hosts.add(host_ip)
    file = open(FILE_NAME, "wb")
    pickle.dump(hosts, file)
    file.close()

@eel.expose
def removeHost(host_ip):
    print("Removing {}".format(host_ip))
    hosts = getHosts(True)
    try:
        hosts.remove(host_ip)
    except:
        print("Failed to remove host {}".format(host_ip))
    file = open(FILE_NAME, "wb")
    pickle.dump(hosts, file)
    file.close()

