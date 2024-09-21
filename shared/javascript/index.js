let current_image = "";
let exposing = false;
let tag = "";

function onLiveModeClicked(){
    alert("Under Development");
}

function onExposureClicked(){
    exposing = true;
    let count = document.getElementById('exposureCount').value;
    if (count === ''){
        count = document.getElementById('exposureCount').placeholder;
    }
    if (document.getElementById('exposure').innerText === 'Start Exposure') {
        alert(`taking ${count} exposures`);
        startScheduler();
    } else {
        alert('Stopping exposure');
        stopScheduler();
    }
}

function restoreCurrentTag(){
    fetch('/get_current_tag')
        .then(response => response.json())
        .then(data => {
            tag = data.tag;

            const tagNameDisplay = document.getElementById('currentTag');
            tagNameDisplay.innerText = `Current Tag: ${tag}`;
            document.getElementById('clearTag').disabled = tag === 'none';
            if (tag !== 'none')
                document.getElementById('tagName').value = tag;
            else
                document.getElementById('tagName').value = '';
        });
}

function onGalleryClicked(){
    window.location.href = '/gallery';
}

function onAddTagClicked(){
    tagNameField = document.getElementById('tagName');
    tagName = tagNameField.value;
    if (tagName === ''){
        alert('Please enter a tag name');
        return;
    }
    tag = document.getElementById('tagName').value;
    const tagNameDisplay = document.getElementById('currentTag');
    tagNameDisplay.innerText = `Current Tag: ${tagName}`;
    document.getElementById('clearTag').disabled = false;

    fetch(`/add_tag/${tagName}`)
        .then(response => response.json())
        .then(data => {
            alert(data.message);
        })
        .catch(error => {
            console.error('Error:', error);
        });

}

function onClearTagClicked(){
    fetch('/stop_tagging')
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            tag = "";
            const tagNameDisplay = document.getElementById('currentTag');
            tagNameDisplay.innerText = `Current Tag: None`;
            document.getElementById('clearTag').disabled = true;
        });
}

function isNumber(value) {
    const number = Number(value);
    return Number.isInteger(number) && number >= 0;
}

function isPosNumber(value) {
    const number = Number(value);
    return number > 0;
}

function startScheduler() {
    let exposureTime = document.getElementById('exposureTime').value;
    const exposureTimeUnit = document.getElementById('exposureTimeUnit').value;
    let intervalTime = document.getElementById('intervalTime').value;
    let gain = document.getElementById('gain').value;
    let offset = document.getElementById('offset').value;
    let count = document.getElementById('exposureCount').value;

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
    if (count === ''){
        count = document.getElementById('exposureCount').placeholder;
    }

    if (!isNumber(exposureTime) || !isNumber(intervalTime) || !isNumber(gain) || !isNumber(offset)) {
        alert('Please enter valid numbers for all fields. All fields must be positive integers.');
        return;
    }
    if (!isPosNumber(count)){
        alert('Please enter a valid number for exposure count. It must be a positive integer.');
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

    const data = {
        exposure: exposureTime,
        interval: intervalTime,
        gain: gain,
        offset: offset
    };

    fetch(`/start_scheduler/${count}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json());
}

function stopScheduler() {
    fetch('/stop_scheduler')
        .then(response => response.json())
        .then(data => {
            alert(data.message);
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

function updateDiskMemory() {
    fetch('/resources')
        .then(response => response.json())
        .then(data => {
            document.getElementById("diskInfo").innerText = data.disk;
            document.getElementById('memoryInfo').innerText = data.memory;
        });
}

function getSchedulerStatus() {
    fetch('/get_scheduler_status')
        .then(response => response.json())
        .then(data => {
            if (data.running === "r") {
                document.getElementById("exposure").innerText = "Cancel Exposure";
                fetch('/get_progress')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('expProgress').innerText = data.eta;
                    });
            } else {
                document.getElementById("exposure").innerText = "Start Exposure";
                document.getElementById('expProgress').innerText = '';
                exposing = false;
            }
        });
}

function getPreviewImage() {
    fetch('/get_preview_images')
        .then(response => response.json())
        .then(data => {
            if(data.img_name === "NONE") {
                document.getElementById('previewImage').src = '/shared/assets/placeholder.jpg';

                return;
            }
            if (current_image === data.img_name) {
                return;
            }
            document.getElementById('previewImage').src = `/shared/img/${data.img_name}`;
            current_image = data.img_name;
        });
}

function repeatGetPreviewImage() {
    if (exposing)
        getPreviewImage();
}

function main(){
    getSettings();
    getPreviewImage();
    restoreCurrentTag();
}

main();
setInterval(getSchedulerStatus, 1000);
setInterval(repeatGetPreviewImage, 1000);
setInterval(updateDiskMemory, 1000);
