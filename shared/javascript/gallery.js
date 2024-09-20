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


function clearPagination() {
    const pagination = document.getElementById('pagination');
    while (pagination.firstChild) {
        pagination.removeChild(pagination.firstChild);
    }
}

function setupPagination() {

    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';

    fetch('/get_total_pages')
        .then(response => response.json())
        .then(data => {
            let totalPages = data.totalPages;

            let page_start = currentPage;
            let page_end = totalPages;

            if (totalPages > 10) {
                page_start = Math.max(page_start - 5, 1);
                page_end = Math.min(page_start + 5, totalPages);
                page_start = Math.max(page_end - 10, 1);
            }

            for (let i = page_start + 1; i <= page_end; i++) {
                const button = document.createElement('button');
                button.innerText = i;
                button.disabled = i === currentPage + 1;
                button.onclick = () => {
                    currentPage = i;
                    fetchAndDisplayImages();
                    clearPagination();
                    setupPagination();
                };
                pagination.appendChild(button);
            }

            const index = document.createElement("p")
            index.innerText = `Page ${currentPage + 1} of ${totalPages}`;
            pagination.appendChild(index);

            const prev = document.createElement('button');
            prev.innerText = 'Prev';
            prev.onclick = () => {
                if (currentPage > 0) {
                    currentPage--;
                    fetchAndDisplayImages();
                    clearPagination();
                    setupPagination();
                }
            }
            const next = document.createElement('button');
            next.innerText = 'Next';
            next.onclick = () => {
                if (currentPage < totalPages - 1) {
                    currentPage++;
                    fetchAndDisplayImages();
                    clearPagination();
                    setupPagination();
                }
            }
            const goto = document.createElement('button');
            goto.innerText = 'Go to';
            goto.onclick = () => {
                gi = document.getElementById('gi');
                isNumber(gi.value) && gi.value > 0 && gi.value <= totalPages ? currentPage = gi.value - 1 : alert("Invalid page number");
                fetchAndDisplayImages();
                clearPagination();
                setupPagination();
            }
            const goto_input = document.createElement('input');
            goto_input.id = 'gi';
            pagination.appendChild(prev);
            pagination.appendChild(next);
            pagination.appendChild(goto);
            pagination.appendChild(goto_input);

        })
}

function isNumber(value) {
    const number = Number(value);
    return Number.isInteger(number) && number >= 0;
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
    let fitsbox = document.getElementById("fits");
    let pngbox = document.getElementById("png");

    if (!fitsbox.checked && !pngbox.checked) {
        alert("Please select at least one file type to download.");
        return;
    }else if (fitsbox.checked && pngbox.checked){
        window.location.href = '/download_all_images/fits;png';
    }else if (fitsbox.checked){
        window.location.href = '/download_all_images/fits';
    }else{
        window.location.href = '/download_all_images/png';
    }

    const box = document.getElementById("deleteOnDownload");
    if (box.checked) {
        deletePresent();
    }
}

function deletePresent(){
    const userConfirmed = confirm("Are you sure you want to delete all images after downloading?");
    if (!userConfirmed)
        return;
    let fitsbox = document.getElementById("fits");
    let pngbox = document.getElementById("png");

    let type = "";

    if (!fitsbox.checked && !pngbox.checked) {
        alert("Please select at least one file type to download.");
        return;
    }else if (fitsbox.checked && pngbox.checked){
        type = 'fits;png';
    }else if (fitsbox.checked){
        type = 'fits';
    }else{
        type = 'png';
    }

    fetch(`/delete_all_images/${type}`)
        .then(response => response.json())
        .then(data => {
            alert(data.message);
        })
        .catch(error => console.error('Error:', error));
}

function update_tags() {
    fetch('/get_tags')
        .then(response => response.json())
        .then(data => {
            const dropdown = document.getElementById('tags'); // Replace 'dropdownId' with the actual ID of your dropdown
            removeAllChildren(dropdown);
            const all = document.createElement('option');
            all.text = 'All';
            dropdown.add(all);
            data.tags.forEach(tag => {
                const option = document.createElement('option');
                option.text = tag;
                dropdown.add(option);
            });
        })
        .catch(error => console.error('Error:', error));
}

function removeAllChildren(element) {
    while (element.firstChild) {
        element.removeChild(element.firstChild);
    }
}

function onHomeClicked(){
    window.location.href = '/';
}

function onFilterClicked(){
    currentPage = 0;
    let conditions = document.getElementById('keywords').value;
    if (conditions === '')
        conditions = 'All';
    fetch(`/apply_filter/${document.getElementById('tags').value}/${conditions}`)
        .then(response => response.json())
        .then(data => {
            alert(data.message);
        })
        .catch(error => console.error('Error fetching images:', error));
    fetchAndDisplayImages();
}

function onClearFilterClicked(){
    currentPage = 0;
    fetch('/clear_filter')
        .then(response => response.json())
        .then(data => {
            alert(data.message);
        })
        .catch(error => console.error('Error fetching images:', error));
    fetchAndDisplayImages();
    document.getElementById('tags').value = 'All';
    document.getElementById('keywords').value = '';
}


function onRefreshClicked(){
    fetchAndDisplayImages();
}

function main(){
    fetchAndDisplayImages();
    setupPagination();
    update_tags();
}

main();


