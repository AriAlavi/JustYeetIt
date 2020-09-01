async function loadHosts(){
    func = eel.getHosts();
    hosts = await func();
    host_parent = document.getElementById("hosts")
    while (host_parent.firstChild) {
        host_parent.removeChild(host_parent.lastChild);
      }
    for(var i = 0; i < hosts.length; i++){
        var host = hosts[i];
        host_elem = document.createElement("div");
        host_elem.classList.add('host');
        host_elem.innerText = host;
        host_elem.id = host;
        host_parent.appendChild(host_elem);
    }
}


function intToByteLengthString(byte_length){
    const BYTE = 1;
    const KILOBYTE = 1028;
    const MEGABYTE = 1000 * KILOBYTE;
    const GIGABYTE = 1000 * MEGABYTE;
    const PENTABYTE = 1000 * GIGABYTE;
    byte_length_list = [PENTABYTE, GIGABYTE, MEGABYTE, KILOBYTE, BYTE]
    byte_abbrv = ["PB", "GB", "MB", "KB", "B"]

    if(byte_length == 0){
        return "0 B"
    }
    for(var i = 0; i < byte_length_list.length; i++){
        var name = byte_abbrv[i];
        var base_size = byte_length_list[i];
        if(byte_length > base_size * 3){
            return String((byte_length / base_size).toFixed(1)) + " " +name;
        }
    }
    
}

async function getUserCount(){
    func = eel.users_connected();
    return await func();
}

function intToTimeString(givenInt){
    const SECOND = 1;
    const MINUTE = 60 * SECOND;
    const HOUR = 60 * MINUTE;
    const DAY = 24 * HOUR;
    const WEEK = 7 * DAY;

    if(givenInt < 0){
        return "Time to complete: Infinite"
    }
    if(givenInt == 0){
        return ""
    }

    const NAMES = ["Week", "Day", "Hour", "Minute", "Second"];
    const DENOMINATIONS = [WEEK, DAY, HOUR, MINUTE, SECOND];
    var times = []
    for(var i = 0; i < NAMES.length; i++){
        var name = NAMES[i];
        var denomination = DENOMINATIONS[i];
        if(givenInt > denomination){
            count = Math.floor(givenInt / denomination);
            givenInt = givenInt % denomination;
            if(count > 1){
                name = name + "s";
            }
            times.push(String(count) + " " + name)
        }
        if(times.length == 2){
            return "Time to complete: " + times[0] + ", " + times[1];
        }
    }
    if(times.length == 1){
        return "Time to complete: " + times[0];
    }
    return "Time to complete: " + times[0] + ", " + times[1];
}

async function addHost(){
    IP = document.getElementById("addIP").value;
    await eel.addHost(IP);
    loadHosts();
}
async function removeHost(IP){
    await eel.removeHost(IP)
    loadHosts();
}

function hostingEffects(){
    document.getElementById("hostIP").disabled = true;
    document.getElementById("hostIP").placeholder = "";
    document.getElementById("hostingServer").hidden = false;
    document.getElementsByClassName("connected")[0].hidden = false;
}

async function checkHosting(){
    hosting = await eel.checkHosting()();
    if(hosting){
        hostingEffects();
    }
}

function clearFiles(){
    files_parent = document.getElementById("files");
    while(files_parent.firstChild){
        files_parent.removeChild(files_parent.lastChild);
    }
}

async function getFiles(ip){
    files = await eel.getFiles(ip)();
    files_parent = document.getElementById("files");
    for(let file of files){
        file_elem = document.createElement("div")
        file_elem.id = file;
        file_elem.classList.add("file");
        file_elem.innerText = file;
        file_elem.title = file;
        files_parent.appendChild(file_elem);
    }
    for(let elem of document.getElementsByClassName("host")){
        elem.classList.remove("disabled")
    }
    return files;
}

async function getQueue(){
    unparsedList = await eel.getQueue()();
    parsedList = [];
    for(let x of unparsedList){
        parsedList.push(JSON.parse(x))
    }
    return parsedList;
}

async function addToQueue(file_name, ip){
    await eel.addToQueue(file_name, ip, 5003)();
}


function hostServer(){
    IP = document.getElementById("hostIP").value;
    eel.hostServer(IP)(function(res){
        if(res == false){
            document.getElementById("hostIP").disabled = false;
            alert("Failed to start server!")
        }
    });
    hostingEffects();
}

async function refreshQueue(){
    await sleep(10);
    q_parent = document.getElementById("queue");
    queue_objs = await getQueue();
    while(q_parent.firstChild){
        q_parent.removeChild(q_parent.lastChild);
    }
    for(let q_json of queue_objs){
        q_elem = document.createElement("div");
        q_elem.classList.add("queue_item");
        q_elem.id = q_json['hash'];
        q_text_elem = document.createElement('div');
        q_text_elem.innerText = q_json['filename'];
        q_text_elem.title = q_json['filename'];
        q_text_elem.classList.add("q_text_elem");
        q_server_elem = document.createElement("div");
        q_server_elem.innerText = q_json['ip'];
        q_server_elem.classList.add("q_server_elem");


        q_elem_top = document.createElement("div");
        q_elem_bottom = document.createElement("div");
        progress_elem = document.createElement("div");
        progress_elem.classList.add("progress");
        q_elem_top.appendChild(q_text_elem);
        
        q_elem_top.classList.add("q_top");
        q_elem_bottom.appendChild(q_server_elem)
        q_elem_bottom.appendChild(progress_elem);
        q_elem.appendChild(q_elem_top);
        q_elem.appendChild(q_elem_bottom);
        q_parent.appendChild(q_elem);

        remove_elem = document.createElement("div");
        remove_elem.innerText = "✘";
        remove_elem.classList.add("remove");
        q_elem_top.appendChild(remove_elem);
        var downloaded = q_json["downloaded"];
        var speed = q_json['speed'];
        var color = '#790d0d';
        if(q_json['complete'] == true){
            color = '#002D2D';
            downloaded = q_json["filesize"];
            speed = 0
        }else{
            if(q_json['paused']){
                pause_or_resume = document.createElement("div");
                pause_or_resume.innerText = "⏵︎";
                pause_or_resume.classList.add("pause");
            }else{
                pause_or_resume = document.createElement("div");
                pause_or_resume.innerText = "❚❚";
                pause_or_resume.classList.add("pause");
            }
            q_elem_top.appendChild(pause_or_resume)
        }
        var progress = new ProgressBar.Line('#' + q_json['hash'] + ' .progress', {
            color: color,
            easing: 'easeInOut'
        });
        progress.set(q_json["percent"]);


        q_elem_data = document.createElement("div");
        file_progress = document.createElement("div");
        file_progress.innerText = intToByteLengthString(downloaded) + "/" + intToByteLengthString(q_json["filesize"]);
        download_speed = document.createElement("div");
        download_speed.innerText = "Speed: " + intToByteLengthString(speed) + "/s"
        q_elem_data.appendChild(file_progress);
        q_elem_data.appendChild(download_speed);
        q_elem_data.classList.add("q_data")


        q_elem_time = document.createElement('div');
        q_elem_time.innerText = intToTimeString(q_json['remains'])

        q_elem.appendChild(q_elem_data);
        q_elem.appendChild(q_elem_time);
    }
}
function sleep (time) {
    return new Promise((resolve) => setTimeout(resolve, time));
}
async function refreshQueueForever(){
    while(true){
        await refreshQueue();
        await sleep(1000);
    }
}

async function pauseQueueAlternate(uniqueHash){
    await eel.pauseQueueAlternate(uniqueHash)();
}

async function removeQueue(uniqueHash){
    await eel.removeFromQueue(uniqueHash)();
}

async function updateConnected(){
    while(true){
        await sleep(1000);
        var count = await getUserCount();
        document.getElementById("connected").innerText = count;
    }
    
}