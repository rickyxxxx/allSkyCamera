let currentPage = 0;
let images = [];

function fetchAndDisplayImages() {
    fetch(`/images/${currentPage}`)
        .then(response => response.json())
        .then(data => {
            images = data.sort((a, b) => a[1].localeCompare(b[1])).reverse();
            displayImages(); // Ensure displayImages is called here
        })
        .catch(error => console.error('Error fetching images:', error));
}

function displayImages() {
    const galleryContent = document.getElementById('galleryContent');
    galleryContent.innerHTML = ''; // Clear previous images
    galleryContent.style.display = 'grid';
    galleryContent.style.gridTemplateColumns = 'repeat(4, 1fr)';
    galleryContent.style.gap = '10px';


    for (let i = 0; i < 4; i++) {
        const row = document.createElement('div');
        row.className = 'row';

        for (let j = 0; j < 3; j++) {
            let index = i * 3 + j;
            if (index >= images.length)
                continue;
            const imageDiv = document.createElement('div');
            imageDiv.className = 'image';
            imageDiv.innerHTML = `
                <div>
                    <img src='/shared/img/${images[index][0]}' onclick="toggleFullscreen(this)" alt="">
                    <div>
                        <h2 style="margin: 0;">${images[index][1]}</h2>
                        <div style="margin-top: auto;">
                            <p>Exposure: ${images[index][2]}</p>
                            <p>Gain/Offset: ${images[index][3]}/${images[index][4]}</p>
                        </div>
                    </div>
                </div>
            `;
            row.appendChild(imageDiv);
        }
        galleryContent.appendChild(row);
    }
}

function setupPagination() {

    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';

    fetch('/get_total_pages')
        .then(response => response.json())
        .then(data => {
            let totalPages = data.totalPages;
            let i = 1;
            if (totalPages > 10){
                i = totalPages - 5;
                totalPages = i + 10;
            }

            for (let i = 1; i <= totalPages; i++) {
                const button = document.createElement('button');
                button.innerText = i;
                button.disabled = i === currentPage;
                button.onclick = () => {
                    currentPage = i - 1;
                    fetchAndDisplayImages();
                };
                pagination.appendChild(button);
            }

            const prev = document.createElement('button');
            prev.innerText = 'Prev';
            prev.onclick = () => {
                if (currentPage > 0) {
                    currentPage--;
                    fetchAndDisplayImages();
                }
            }
            const next = document.createElement('button');
            next.innerText = 'Next';
            next.onclick = () => {
                if (currentPage < totalPages - 1) {
                    currentPage++;
                    fetchAndDisplayImages();
                }
            }
            const goto = document.createElement('button');
            goto.innerText = 'Go to';
            goto.onclick = () => {
                const gi = document.createElement('input');

                gi.min = 1;
                gi.max = totalPages;
                currentPage = gi.value - 1;
                alert(currentPage);
                fetchAndDisplayImages();
            }
            const goto_input = document.createElement('input');
            pagination.appendChild(prev);
            pagination.appendChild(next);
            pagination.appendChild(goto);
            pagination.appendChild(goto_input);

        })
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

function onHomeClicked(){
    window.location.href = '/';
}

function onSelectClicked(){
    alert("Select clicked");
}

function onDeleteClicked(){
    alert("Detect clicked");
}

function onDownloadClicked(){
    alert("Download clicked");
}


function main(){
    fetchAndDisplayImages();
    setupPagination();
}

main();


