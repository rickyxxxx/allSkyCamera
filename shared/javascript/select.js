function onGalleryClicked(){
    window.location.href = '/gallery';
}

function onHomeClicked(){
    window.location.href = '/';
}

function updateImageList(){
    fetch('/get_image_list/all')
        .then(response => response.json())
        .then(data => {
            createScrollFrameWithCheckboxes('imageList', data.img_list);
        });
}

function createScrollFrameWithCheckboxes(containerId, checkboxLabels) {
    const container = document.getElementById(containerId);

    // Create canvas and scrollbar
    const canvas = document.createElement('canvas');
    const scrollbar = document.createElement('div');
    scrollbar.style.overflowY = 'scroll';
    scrollbar.style.height = '100%';

    // Create inner frame for checkboxes
    const innerFrame = document.createElement('div');
    innerFrame.style.display = 'flex';
    innerFrame.style.flexDirection = 'column';

    // Add checkboxes to the inner frame
    checkboxLabels.forEach(label => {
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = label;
        const checkboxLabel = document.createElement('label');
        checkboxLabel.htmlFor = label;
        checkboxLabel.textContent = label;
        innerFrame.appendChild(checkbox);
        innerFrame.appendChild(checkboxLabel);
    });

    // Append inner frame to canvas and canvas to scrollbar
    canvas.appendChild(innerFrame);
    scrollbar.appendChild(canvas);
    container.appendChild(scrollbar);
}

function main(){
    updateImageList();
}

main();