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

// function onDownloadClicked() {
//     window.location.href = '/download';
// }

function onDownloadClicked(filename) {
    alert("requesting download");
    fetch('/download', {
        method: 'GET'
    })
    .then(response => response.blob())
    .then(blob => {
        alert("Download will start shortly");
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = "images.bin";
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    })
    .catch(error => console.error('Error downloading files:', error));
}


// function onDownloadClicked() {
//     fetch('/download', {
//         method: 'GET'
//     })
//     .then(response => response.arrayBuffer())
//     .then(buffer => {
//         alert("Download will start shortly");
//         const byteArray = new Uint8Array(buffer);
//         // Assuming the server sends a custom format where each file is prefixed with its length and name
//         let offset = 0;
//         while (offset < byteArray.length) {
//             const nameLength = byteArray[offset];
//             offset += 1;
//             const name = new TextDecoder().decode(byteArray.slice(offset, offset + nameLength));
//             offset += nameLength;
//             const fileLength = new DataView(byteArray.buffer, offset, 4).getUint32(0, true);
//             offset += 4;
//             const fileData = byteArray.slice(offset, offset + fileLength);
//             offset += fileLength;
//
//             const blob = new Blob([fileData]);
//             const url = window.URL.createObjectURL(blob);
//             const a = document.createElement('a');
//             a.style.display = 'none';
//             a.href = url;
//             a.download = name;
//             document.body.appendChild(a);
//             a.click();
//             window.URL.revokeObjectURL(url);
//             document.body.removeChild(a);
//         }
//     })
//     .catch(error => console.error('Error downloading files:', error));
// }

function displayImages() {
    const galleryContent = document.getElementById('galleryContent');
    galleryContent.innerHTML = ''; // Clear previous images
    galleryContent.style.display = 'grid';
    galleryContent.style.gridTemplateColumns = 'repeat(4, 1fr)';
    galleryContent.style.gap = '10px';


    for (let i = 0; i < 4; i++) {
        const row = document.createElement('div');
        row.className = 'row';

        for (let j = 0; j < 2; j++) {
            let index = i * 2 + j;
            if (index >= images.length)
                continue;
            const imageDiv = document.createElement('div');
            let exp_str = '';
            if (images[index][2] < 1000){
                exp_str = images[index][2] + ' us';
            } else if (images[index][2] < 1000000){
                exp_str = (images[index][2] / 1000) + ' ms';
            } else {
                exp_str = (images[index][2] / 1000000) + ' s';
            }
            imageDiv.className = 'image';
            imageDiv.innerHTML = `
                <div>
                    <img src='/shared/img/${images[index][0]}.png' onclick="toggleFullscreen(this)" alt="">
                    <div>
                        <h2 style="margin: 0;">${images[index][1]}</h2>
                        <div style="margin-top: auto;">
                            <p>Exposure: ${exp_str}</p>
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


function calcPagingLabel(totalPages) {
    let page_index = [1, 2];
    if (totalPages <= 1)
        return [1];
    if (totalPages <= 5){
        for (let i = 3; i <= totalPages; i++)
            page_index.push(i);
        return page_index;
    }

    // if the code reaches here, totalPages > 5
    let start_page = Math.max(currentPage - 1, 1);
    let end_page = Math.min(currentPage + 3, totalPages);
    if (start_page > 3)
        page_index.push(-1);
    start_page = Math.max(start_page, 3);
    for (let i = start_page; i <= end_page; i++){
        page_index.push(i);
    }
    if (end_page < totalPages - 2) {
        page_index.push(-1);
        for (let i = totalPages - 1; i <= totalPages; i++)
            page_index.push(i);
    } else {
        for (let i = end_page + 1; i <= totalPages; i++)
            page_index.push(i);
    }
    return page_index;
}

function updatePage(){
    fetchAndDisplayImages();
    clearPagination();
    setupPagination();
}

function setupPagination() {
    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';

    fetch('/get_total_pages')
        .then(response => response.json())
        .then(data => {
            let totalPages = data.totalPages;

            const prev = document.createElement('button');
            prev.innerText = '<';
            prev.className = 'labelButton';
            prev.disabled = currentPage === 0;
            prev.onclick = () => {
                if (currentPage > 0) {
                    currentPage--;
                    updatePage();
                }
            }
            pagination.appendChild(prev);

            calcPagingLabel(totalPages).forEach(page => {
                const button = document.createElement('button');
                if (page === -1){
                    button.innerText = '...';
                    button.disabled = true;
                    button.className='labelButton';
                } else {
                    button.innerText = page;
                    button.className = 'pageButton';
                    button.disabled = page === currentPage + 1;
                    button.onclick = () => {
                        currentPage = page - 1;
                        updatePage()
                    }
                }
                pagination.appendChild(button);
            });

            const next = document.createElement('button');
            next.innerText = '>';
            next.className = 'labelButton';
            next.disabled = currentPage === totalPages - 1;
            next.onclick = () => {
                if (currentPage < totalPages - 1) {
                    currentPage++;
                    updatePage();
                }
            }
            pagination.appendChild(next);

            const index = document.createElement("p")
            index.innerText = `Page ${currentPage + 1} of ${Math.max(totalPages, 1)}`;
            pagination.appendChild(index);


            const goto_input = document.createElement('input');
            goto_input.id = 'gi';
            const goto = document.createElement('button');
            goto.innerText = 'Go to';
            goto.onclick = () => {
                gi = document.getElementById('gi');
                isNumber(gi.value) && gi.value > 0 && gi.value <= totalPages ? currentPage = gi.value - 1 : alert("Invalid page number");
                updatePage();
            }

            pagination.appendChild(goto_input);
            pagination.appendChild(goto);

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

// async function downloadFile(url, filename) {
//     try {
//         const response = await fetch(url);
//         const blob = await response.blob();
//         const objectUrl = window.URL.createObjectURL(blob);
//         const a = document.createElement('a');
//         a.style.display = 'none';
//         a.href = objectUrl;
//         a.download = filename;
//         document.body.appendChild(a);
//         a.click();
//         window.URL.revokeObjectURL(objectUrl);
//         document.body.removeChild(a);
//     } catch (error) {
//         console.error('Error downloading file:', error);
//     }
// }
//
// async function downloadImages() {
//     let fitsbox = document.getElementById("fits");
//     let pngbox = document.getElementById("png");
//     let exts = [];
//
//     if (!fitsbox.checked && !pngbox.checked) {
//         alert("Please select at least one file type to download.");
//         return;
//     }
//     if (fitsbox.checked) exts.push('fits');
//     if (pngbox.checked) exts.push('png');
//
//     alert("Download will start shortly");
//
//     try {
//         const response = await fetch("/estimate_pagesize");
//         const data = await response.json();
//         const downloadPromises = [];
//
//         for (let i = 0; i < data.totalPages; i++) {
//             for (const ext of exts) {
//                 const url = `/download_image/${ext}/${i}`;
//                 const filename = `image_${i}.${ext}`;
//                 downloadPromises.push(downloadFile(url, filename));
//             }
//         }
//
//         await Promise.all(downloadPromises);
//         alert("All downloads completed");
//     } catch (error) {
//         console.error('Error estimating page size:', error);
//     }
// }

function downloadImages() {
    alert("download will start shortly")
    fetch("/estimate_pagesize")
        .then(response => response.json())
        .then(data => {
            for (let i = 0; i < data.totalPages; i++) {
                fetch(`/download_image/${ext}/${i}`)
                .then(response => response.blob())
                .then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = `image_${i}.${ext}`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                })
                .catch(error => console.error('Error downloading file:', error));
            }
        });
}

function deletePresent(){
    const userConfirmed = confirm("Are you sure you want to delete all the selected images?");
    if (!userConfirmed)
        return;
    if (document.getElementById('tags').value === 'All') {
        if (document.getElementById('keywords').value === '') {
            const userConfirmed = confirm("!!! You did not apply any filter !!! \n" +
                "Are you sure you want to delete all images?");
            if (!userConfirmed)
                return;
        }
    }

    fetch(`/delete_all_images`)
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            document.getElementById('tags').value = 'All';
            document.getElementById('keywords').value = '';
            updatePage();
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
            updatePage();
        })
        .catch(error => console.error('Error fetching images:', error));
}

function onClearFilterClicked(){
    currentPage = 0;
    fetch('/apply_filter/all/all')
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            updatePage();
            document.getElementById('tags').value = 'All';
            document.getElementById('keywords').value = '';
        })
        .catch(error => console.error('Error fetching images:', error));

}

function main(){
    fetchAndDisplayImages();
    setupPagination();
    update_tags();
}

main();


