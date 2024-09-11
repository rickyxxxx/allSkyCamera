function showTab(tabId) {
    if (tabId === 'gallery') {
        fetchImages();
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
            const galleryContent = document.getElementById('galleryContent');
            galleryContent.innerHTML = '';
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

function starImage(imageName, star) {
    fetch('/star', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ image: imageName })
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success)
            alert('Failed to star image.');
    })
    .catch(error => {
        console.error('Error:', error);
    });
    fetchImages();
}

// Set default tab
showTab('gallery');
