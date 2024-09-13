function showTab(tabId) {
    if (tabId === 'gallery') {
        fetchImages();
    } else if (tabId === 'scheduler') {
        getSettings();
        getSchedulerStatus();
    }
    document.querySelectorAll('.tab-content').forEach(content => {
        content.style.display = 'none';
    });
    document.getElementById(tabId).style.display = 'block';
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`.tab[onclick="showTab('${tabId}')"]`).classList.add('active');
}

function fetchImages() {
    fetch('/images')
        .then(response => response.json())
        .then(images => {
            images.sort((a, b) => a[1].localeCompare(b[1]));

            const galleryContent = document.getElementById('galleryContent');
            galleryContent.style.display = 'flex';
            galleryContent.style.flexDirection = 'column';
            galleryContent.style.alignItems = 'center'; // Optional: Center align the images

            images.forEach(image => {
                const div = document.createElement('div');
                div.className = 'image';
                div.innerHTML = `
                    <div>
                        <img src='/shared/img/${image[0]}' onclick="toggleFullscreen(this)">
                        <div>
                            <h2 style="margin: 0;">${image[1]}</h2>
                            <div style="margin-top: auto;">
                                <span>Exposure: ${image[2]}</span><br>
                                <span>Gain/Offset: ${image[3]}/${image[4]}</span>
                            </div>
                        </div>                 
                    </div>
                `;
                galleryContent.appendChild(div);
            });
        });
}

function toggleFullscreen(img) {
    if (!document.fullscreenElement) {
        img.requestFullscreen().catch(err => {
            alert(`Error attempting to enable full-screen mode: ${err.message} (${err.name})`);
        });
    } else {
        document.exitFullscreen().then(r => {});
    }
}

function downloadImages() {
    window.location.href = '/download_images';
}

function isNumber(value) {
    const number = Number(value);
    return Number.isInteger(number) && number > 0;
}

function startScheduler() {
    let exposureTime = document.getElementById('exposureTime').value;
    const exposureTimeUnit = document.getElementById('exposureTimeUnit').value;
    let intervalTime = document.getElementById('intervalTime').value;
    let gain = document.getElementById('gain').value;
    let offset = document.getElementById('offset').value;

    if (exposureTime === ''){
        exposureTime = document.getElementById('exposureTime').placeholder;
    }
    if (intervalTime === ''){
        intervalTime = document.getElementById('intervalTime').placeholder;
    }
    if (gain === ''){
        gain = document.getElementById('gain').placeholder;
    }
    if (offset === ''){
        offset = document.getElementById('offset').placeholder;
    }

    if (!isNumber(exposureTime) || !isNumber(intervalTime) || !isNumber(gain) || !isNumber(offset)) {
        alert('Please enter valid numbers for all fields. All fields must be positive integers.');
        return;
    }

    if (exposureTimeUnit === 'ms') {
        exposureTime = exposureTime * 1000;
    }else if (exposureTimeUnit === 's') {
        exposureTime = exposureTime * 1000000;
    }

    if (exposureTime < 22 || exposureTime > 100000000) {
        alert('Exposure time must be between 22us and 100s.');
        return;
    }

    if (intervalTime < 2){
        alert('Interval time must be at least 2 seconds.');
        return;
    }

    const data = {
        exposure: exposureTime,
        interval: intervalTime,
        gain: gain,
        offset: offset
    };

    fetch('/start_scheduler', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
        document.querySelector('button[onclick="startScheduler()"]').disabled = true;
        document.querySelector('button[onclick="stopScheduler()"]').disabled = false;
    });
}

function stopScheduler() {
    fetch('/stop_scheduler')
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            document.querySelector('button[onclick="startScheduler()"]').disabled = false;
            document.querySelector('button[onclick="stopScheduler()"]').disabled = true;
        });
}

function getSettings() {
    fetch('/get_settings')
        .then(response => response.json())
        .then(data => {
            if (data.exposure > 1000000) {
                document.getElementById('exposureTimeUnit').value = 's';
                document.getElementById('exposureTime').placeholder = data.exposure / 1000000;
            } else if (data.exposure > 1000) {
                document.getElementById('exposureTimeUnit').value = 'ms';
                document.getElementById('exposureTime').placeholder = data.exposure / 1000;
            } else {
                document.getElementById('exposureTimeUnit').value = 'us';
                document.getElementById('exposureTime').placeholder = data.exposure;
            }
            document.getElementById('intervalTime').placeholder = data.interval;
            document.getElementById('gain').placeholder = data.gain;
            document.getElementById('offset').placeholder = data.offset;
        });

}

function getSchedulerStatus() {
    fetch('/get_scheduler_status')
        .then(response => response.json())
        .then(data => {
            if (data.running === "r") {
                document.querySelector('button[onclick="startScheduler()"]').disabled = true;
                document.querySelector('button[onclick="stopScheduler()"]').disabled = false;
            } else {
                document.querySelector('button[onclick="startScheduler()"]').disabled = false;
                document.querySelector('button[onclick="stopScheduler()"]').disabled = true;
            }
        });
}


function main(){
    // set the default tab to Gallery on startup
    showTab('gallery');
}

main();


