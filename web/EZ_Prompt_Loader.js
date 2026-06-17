import { app } from "../../../scripts/app.js";

// Code largely inspired by FILL NODES, credit to the author: https://github.com/filliptm/ComfyUI_Fill-Nodes

app.registerExtension({
    name: "Comfy.EZ_Prompt_Loader",
    async nodeCreated(node) {
        if (node.comfyClass === "EZ_Prompt_Loader") {
            addFileBrowserUI(node);
        }
    }
});

async function addFileBrowserUI(node) {
    // Tweakable variables
    const CLICK_Y_OFFSET = 0;
    const CLICK_X_OFFSET = -2;

    const rootDirectoryWidget = node.widgets.find(w => w.name === "prompt_directory");
    const selectedFilesWidget = node.widgets.find(w => w.name === "selected_files");
    const selectionModeWidget = node.widgets.find(w => w.name === "selection_mode");
    const filterTextWidget = node.widgets.find(w => w.name === "filter_text");

    if (!rootDirectoryWidget || !selectedFilesWidget || !selectionModeWidget || !filterTextWidget) {
        console.error("Required widgets not found:", { rootDirectoryWidget, selectedFilesWidget, selectionModeWidget, filterTextWidget });
        return;
    }

    rootDirectoryWidget.hidden = false;
    selectedFilesWidget.hidden = true;
    selectionModeWidget.hidden = false;
    filterTextWidget.hidden = false;

    const MIN_WIDTH = 390;
    const MIN_HEIGHT = 410;
    const TOP_PADDING = 212;
    const BOTTOM_PADDING = 5;
    const BOTTOM_SKIP = 10;
    const TOP_BAR_HEIGHT = 0;
    const ITEM_SIZE = 180;
    const MIN_ITEM_SIZE = 180; // Your desired base size
    const ITEM_PADDING = 10;
    const SCROLLBAR_WIDTH = 8;
    const TEXT_PADDING = 10;
    const PREVIEW_PADDING = 20; // Padding for preview text
    const PREVIEW_SKIP = 152; // Skip for preview text
    const BORDER_RADIUS = 0;
    const SELECTION_BORDER_RADIUS = 0;
    const SELECTION_BORDER_PADDING = 2;
    const ELLIPSIS = "...";

    const COLORS = {
        background: "#1e1e1e",
        topBar: "#252526",
        item: "#2d2d30",
        itemHover: "#3e3e42",
        itemSelected: "#0e639c",
        text: "#ffffff",
        scrollbar: "#3e3e42",
        scrollbarHover: "#505050",
        divider: "#4f0074",
        dividerHover: "#16727c"
    };

    let currentDirectory = null;
    let filterText = filterTextWidget.value;
    let selectedFiles = new Set();
    let files = [];
    let thumbnails = {};
    let scrollOffset = 0;
    let targetScrollOffset = 0;
    let isAnimating = false;
    let isDragging = false;
    let scrollStartY = 0;
    let scrollStartOffset = 0;


// Helper to calculate the stretched size
function getAdaptiveSize() {
    const availableWidth = node.size[0] - SCROLLBAR_WIDTH - ITEM_PADDING;
    // Calculate how many columns fit at the minimum size
    const cols = Math.max(1, Math.floor(availableWidth / (MIN_ITEM_SIZE + ITEM_PADDING)));
    // Distribute remaining space so they fit perfectly
    const stretchedSize = (availableWidth / cols) - ITEM_PADDING;
    return { size: stretchedSize, cols: cols };
}
    async function updateFiles() {
        try {
            const response = await fetch('/ez_file_browser/get_directory_structure', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: currentDirectory, filter: filterText })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                console.error("Server error:", errorData.error);
                return;
            }

            const data = await response.json();
            if (!data.files) {
                console.error("Invalid response format:", data);
                return;
            }

            files = data.files;
            await loadThumbnails();
            node.setDirtyCanvas(true);
        } catch (error) {
            console.error("Error updating files:", error);
        }
    }

    async function loadThumbnails() {
        thumbnails = {};
        for (const file of files) {
            try {
                const imageFile = file.replace('.txt', '.png');
                // Extract directory and filename for thumbnail request
                const pathParts = file.split(/[/\\]/);
                const fileName = pathParts[pathParts.length - 1];
                const dirPath = pathParts.length > 1 ? pathParts.slice(0, -1).join('/') : '';
                const fileDir = dirPath ? `${currentDirectory}/${dirPath}` : currentDirectory;
                // Replace PROMPTS with THUMBNAILS in the path for thumbnail loading
                const thumbnailDir = fileDir.replace(/prompts/g, 'thumbnails');
                
                const response = await fetch('/ez_file_browser/get_thumbnail', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: thumbnailDir, file: fileName.replace('.txt', '.png') })
                });
                if (response.ok) {
                    const blob = await response.blob();
                    thumbnails[file] = await createImageBitmap(blob);
                }
            } catch (error) {
                console.error(`Error loading thumbnail for ${file}:`, error);
            }
        }
    }

    async function fetchFileInfo(relativePath) {
        try {
            const response = await fetch('/ez_file_browser/get_file_info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ relative_path: relativePath })
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error("Server error:", errorData.error);
                return null;
            }

            const result = await response.json();
            return result.full_path || null;
        } catch (error) {
            console.error("Error fetching file info:", error);
            return null;
        }
    }

    function updateSelectedFiles(file) {
        if (selectionModeWidget.value === "multiple" || selectionModeWidget.value === "random") {
            if (selectedFiles.has(file)) {
                selectedFiles.delete(file);
            } else {
                selectedFiles.add(file);
            }
        } else {
            selectedFiles.clear();
            selectedFiles.add(file);
        }
        
        const selectedFilesString = Array.from(selectedFiles).join(", ");
        selectedFilesWidget.value = selectedFilesString;
        node.setDirtyCanvas(true);
    }

    function drawPreviewText(ctx, text) {
        ctx.fillStyle = COLORS.text;
        ctx.font = "12px Arial";
        
        // Calculate available width for text
        const maxWidth = node.size[0] - TEXT_PADDING * 2;
        
        let displayText = text;
        if (selectionModeWidget.value === "multiple") {
            const count = selectedFiles.size;
            displayText = `${count} prompt${count !== 1 ? 's' : ''} selected`;
        } else if (selectionModeWidget.value === "random") {
            const count = selectedFiles.size > 0 ? selectedFiles.size : files.length;
            displayText = `selecting from ${count} prompt${count !== 1 ? 's' : ''}`;
        } else {
            // Single mode - show first selected file name (filename only, no path)
            if (selectedFiles.size > 0) {
                const selectedFile = Array.from(selectedFiles)[0];
                const pathParts = selectedFile.split(/[/\\]/);
                const fileName = pathParts[pathParts.length - 1].split(".")[0];
                displayText = fileName;
            } else {
                displayText = "";
            }
        }
        
        // Measure text width
        const textMetrics = ctx.measureText(displayText);
        
        // If text is too long, truncate it
        if (textMetrics.width > maxWidth) {
            let truncatedText = displayText;
            while (ctx.measureText(truncatedText + ELLIPSIS).width > maxWidth && truncatedText.length > 0) {
                truncatedText = truncatedText.slice(0, -1);
            }
            displayText = truncatedText + ELLIPSIS;
        }
        
        // Draw the text
        ctx.fillText(displayText, PREVIEW_PADDING, PREVIEW_SKIP);
    }

    const refreshButton = node.addWidget("button", "Refresh / Clear", null, () => {
        selectedFiles.clear();
        selectedFilesWidget.value = "";
        (async () => {
            currentDirectory = await fetchFileInfo(rootDirectoryWidget.value);
            if (currentDirectory) {
                updateFiles();
            }
        })();
    });

    rootDirectoryWidget.callback = () => {
        selectedFiles.clear();
        selectedFilesWidget.value = "";
        (async () => {
            currentDirectory = await fetchFileInfo(rootDirectoryWidget.value);
            if (currentDirectory) {
                updateFiles();
            }
        })();
    };

    selectionModeWidget.callback = () => {
        selectedFiles.clear();
        selectedFilesWidget.value = "";
        node.setDirtyCanvas(true);
    };

    filterTextWidget.callback = () => {
        filterText = filterTextWidget.value;
        updateFiles();
    };

    // Add Invert Selection button widget
    const invertButton = node.addWidget("button", "Invert Selection", null, () => {
        if (selectionModeWidget.value !== "multiple" && selectionModeWidget.value !== "random") return;
        const allFileNames = files;
        const newSelected = new Set();
        for (const file of allFileNames) {
            if (!selectedFiles.has(file)) newSelected.add(file);
        }
        selectedFiles = newSelected;
        // Update widget value
        const selectedFilesString = Array.from(selectedFiles).join(", ");
        selectedFilesWidget.value = selectedFilesString;
        node.setDirtyCanvas(true);
    });
    // Ensure correct enabled state on load
    setTimeout(() => {
        invertButton.disabled = selectionModeWidget.value !== "multiple" && selectionModeWidget.value !== "random";
    }, 0);

    // Update button enabled/disabled state on mode change
    const origSelectionModeCallback = selectionModeWidget.callback;
    selectionModeWidget.callback = () => {
        selectedFiles.clear();
        selectedFilesWidget.value = "";
        invertButton.disabled = selectionModeWidget.value !== "multiple" && selectionModeWidget.value !== "random";
        node.setDirtyCanvas(true);
        if (origSelectionModeCallback) origSelectionModeCallback();
    };

    node.onDrawBackground = function(ctx) {
        if (!this.flags.collapsed) {
            const pos = TOP_PADDING - TOP_BAR_HEIGHT;
            ctx.fillStyle = COLORS.background;
            ctx.fillRect(0, pos, this.size[0], this.size[1] - pos - BOTTOM_SKIP);

            // Draw top bar
            ctx.fillStyle = COLORS.topBar;
            ctx.fillRect(0, pos, this.size[0], TOP_BAR_HEIGHT);

            // Draw selected file preview
            drawPreviewText(ctx, selectedFiles.size > 0 ? Array.from(selectedFiles)[0].split(".")[0] : "");

            ctx.save();
            ctx.beginPath();
            ctx.rect(0, TOP_PADDING, this.size[0] - SCROLLBAR_WIDTH, this.size[1] - TOP_PADDING - BOTTOM_PADDING - BOTTOM_SKIP);
            ctx.clip();
            drawFiles(ctx, 0, TOP_PADDING - scrollOffset, this.size[0] - SCROLLBAR_WIDTH - 10, this.size[1] - TOP_PADDING - BOTTOM_PADDING - BOTTOM_SKIP);
            ctx.restore();

            // Draw scrollbar
            drawScrollbar(ctx, this.size[0] - SCROLLBAR_WIDTH, TOP_PADDING, SCROLLBAR_WIDTH, this.size[1] - TOP_PADDING - BOTTOM_PADDING - BOTTOM_SKIP, scrollOffset, getTotalFilesHeight());
        }
    };

    function drawRoundedRect(ctx, x, y, width, height, radius, color) {
        ctx.beginPath();
        ctx.moveTo(x + radius, y);
        ctx.lineTo(x + width - radius, y);
        ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
        ctx.lineTo(x + width, y + height - radius);
        ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
        ctx.lineTo(x + radius, y + height);
        ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
        ctx.lineTo(x, y + radius);
        ctx.quadraticCurveTo(x, y, x + radius, y);
        ctx.closePath();
        ctx.fillStyle = color;
        ctx.fill();
    }

    function drawScrollbar(ctx, x, y, width, height, offset, totalHeight) {
        drawRoundedRect(ctx, x, y, width, height, width / 2, COLORS.scrollbar);

        const visibleHeight = height;
        const scrollHeight = Math.max(height * (visibleHeight / totalHeight), 20);
        const maxOffset = Math.max(0, totalHeight - visibleHeight);
        const scrollY = y + (offset / maxOffset) * (height - scrollHeight);

        drawRoundedRect(ctx, x, scrollY, width, scrollHeight, width / 2, COLORS.scrollbarHover);
    }

    function getTotalFilesHeight() {
        const itemsPerRow = Math.floor((node.size[0] - SCROLLBAR_WIDTH) / (ITEM_SIZE + ITEM_PADDING));
        return Math.ceil(files.length / itemsPerRow) * (ITEM_SIZE + ITEM_PADDING);
    }
function drawFiles(ctx, x, y, width, height) {
    const { size, cols } = getAdaptiveSize();
    const startRow = Math.floor(scrollOffset / (size + ITEM_PADDING));
    const endRow = Math.min(Math.ceil(files.length / cols), startRow + Math.ceil(height / (size + ITEM_PADDING)) + 2);

    for (let row = startRow; row < endRow; row++) {
        for (let col = 0; col < cols; col++) {
            const fileIndex = row * cols + col;
            if (fileIndex >= files.length) break;

            const file = files[fileIndex];
            const xPos = x + ITEM_PADDING + col * (size + ITEM_PADDING);
            const yPos = y + ITEM_PADDING + row * (size + ITEM_PADDING);

            // Background
            const bgColor = selectedFiles.has(file) ? COLORS.itemSelected : COLORS.item;
            drawRoundedRect(ctx, xPos, yPos, size, size, BORDER_RADIUS, bgColor);

            // Thumbnail
            if (thumbnails[file]) {
                ctx.save();
                ctx.beginPath();
                ctx.roundRect(xPos, yPos, size, size, BORDER_RADIUS);
                ctx.clip();
                ctx.drawImage(thumbnails[file], xPos, yPos, size, size);
                ctx.restore();
            }

            // Gradient Overlay (Dynamic Height)
            const gradientHeight = size / 2;
            const gradient = ctx.createLinearGradient(xPos, yPos + size - gradientHeight, xPos, yPos + size);
            gradient.addColorStop(0, 'rgba(0, 0, 0, 0)');
            gradient.addColorStop(1, 'rgb(0, 0, 0)');
            ctx.fillStyle = gradient;
            ctx.fillRect(xPos, yPos + size - gradientHeight, size, gradientHeight);

            // Filename (Dynamic Truncation)
            ctx.fillStyle = COLORS.text;
            ctx.font = "12px Arial";
            const pathParts = file.split(/[/\\]/);
            const fileName = pathParts[pathParts.length - 1].split(".")[0];
            const maxTextWidth = size - TEXT_PADDING * 2;
            
            let displayText = fileName;
            if (ctx.measureText(displayText).width > maxTextWidth) {
                while (ctx.measureText(displayText + ELLIPSIS).width > maxTextWidth && displayText.length > 0) {
                    displayText = displayText.slice(0, -1);
                }
                displayText += ELLIPSIS;
            }
            ctx.fillText(displayText, xPos + TEXT_PADDING, yPos + size - TEXT_PADDING);

            // Selection Border
            if (selectedFiles.has(file)) {
                ctx.strokeStyle = COLORS.itemSelected;
                ctx.lineWidth = 3;
                ctx.strokeRect(xPos - 1, yPos - 1, size + 2, size + 2);
            }
        }
    }
}
    function XdrawFiles(ctx, x, y, width, height) {
        ctx.fillStyle = COLORS.background;
        ctx.fillRect(x, y, width, height);

        const itemsPerRow = Math.floor(width / (ITEM_SIZE + ITEM_PADDING));
        const visibleHeight = height;
        const startRow = Math.floor(scrollOffset / (ITEM_SIZE + ITEM_PADDING));
        const endRow = Math.min(Math.ceil(files.length / itemsPerRow), startRow + Math.ceil(visibleHeight / (ITEM_SIZE + ITEM_PADDING)) + 2);

        for (let row = startRow; row < endRow; row++) {
            for (let col = 0; col < itemsPerRow; col++) {
                const fileIndex = row * itemsPerRow + col;
                if (fileIndex >= files.length) break;

                const file = files[fileIndex];
                const xPos = x + ITEM_PADDING + col * (ITEM_SIZE + ITEM_PADDING);
                const yPos = y + ITEM_PADDING + row * (ITEM_SIZE + ITEM_PADDING);

                // Draw file background
                const bgColor = selectedFiles.has(file) ? COLORS.itemSelected : COLORS.item;
                drawRoundedRect(ctx, xPos, yPos, ITEM_SIZE, ITEM_SIZE, BORDER_RADIUS, bgColor);

                // Draw thumbnail if available
                if (thumbnails[file]) {
                    // Draw thumbnail with rounded corners
                    ctx.save();
                    ctx.beginPath();
                    ctx.roundRect(xPos, yPos, ITEM_SIZE, ITEM_SIZE, BORDER_RADIUS);
                    ctx.clip();
                    ctx.drawImage(thumbnails[file], xPos, yPos, ITEM_SIZE, ITEM_SIZE);
                    ctx.restore();
                }

                // Draw gradient overlay at the bottom
                const gradientHeight = ITEM_SIZE/2;
                const gradient = ctx.createLinearGradient(
                    xPos, 
                    yPos + ITEM_SIZE - gradientHeight, 
                    xPos, 
                    yPos + ITEM_SIZE
                );
                gradient.addColorStop(0, 'rgba(0, 0, 0, 0)');
                gradient.addColorStop(1, 'rgb(0, 0, 0)');
                ctx.fillStyle = gradient;
                ctx.fillRect(xPos, yPos + ITEM_SIZE - gradientHeight, ITEM_SIZE, gradientHeight);

                // Draw filename
                ctx.fillStyle = COLORS.text;
                ctx.font = "12px Arial";
                
                // Get just the filename (everything after the last slash or backslash)
                const pathParts = file.split(/[/\\]/);
                const fileName = pathParts[pathParts.length - 1].split(".")[0];
                // Calculate available width for text
                const maxTextWidth = ITEM_SIZE - TEXT_PADDING * 2;
                
                let displayText = fileName;
                
                // Measure text width
                const textMetrics = ctx.measureText(displayText);
                
                // If text is too long, truncate it
                if (textMetrics.width > maxTextWidth) {
                    let truncatedText = fileName;
                    while (ctx.measureText(truncatedText + ELLIPSIS).width > maxTextWidth && truncatedText.length > 0) {
                        truncatedText = truncatedText.slice(0, -1);
                    }
                    displayText = truncatedText + ELLIPSIS;
                }
                
                // Draw the filename
                ctx.fillText(displayText, xPos + TEXT_PADDING, yPos + ITEM_SIZE - TEXT_PADDING);

                // Draw selection border
                if (selectedFiles.has(file)) {
                    ctx.strokeStyle = COLORS.itemSelected;
                    ctx.lineWidth = 3;
                    ctx.beginPath();
                    ctx.roundRect(
                        xPos - SELECTION_BORDER_PADDING, 
                        yPos - SELECTION_BORDER_PADDING, 
                        ITEM_SIZE + SELECTION_BORDER_PADDING * 2, 
                        ITEM_SIZE + SELECTION_BORDER_PADDING * 2, 
                        SELECTION_BORDER_RADIUS
                    );
                    ctx.stroke();
                }
            }
        }
    }

node.onMouseDown = function(event) {
    const pos = TOP_PADDING - TOP_BAR_HEIGHT;
    const localY = event.canvasY - this.pos[1] - pos + CLICK_Y_OFFSET;
    const localX = event.canvasX - this.pos[0] + CLICK_X_OFFSET;

    if (localY > TOP_BAR_HEIGHT && localY < this.size[1] - pos - 10) {
        if (localX >= 0 && localX < this.size[0] - SCROLLBAR_WIDTH) {
            const { size, cols } = getAdaptiveSize(); // Get the current calculated size
            const row = Math.floor((localY - TOP_BAR_HEIGHT + scrollOffset) / (size + ITEM_PADDING));
            const col = Math.floor(localX / (size + ITEM_PADDING));
            const fileIndex = row * cols + col;
            
            if (fileIndex >= 0 && fileIndex < files.length) {
                updateSelectedFiles(files[fileIndex]);
            }
            return true;
            } else if (localX >= this.size[0] - SCROLLBAR_WIDTH) {
                // Click on scrollbar
                isDragging = true;
                scrollStartY = event.canvasY;
                scrollStartOffset = scrollOffset;
                return true;
            }
        }

        return false;
    };

    node.onMouseMove = function(event) {
        const pos = TOP_PADDING - TOP_BAR_HEIGHT;
        const localY = event.canvasY - this.pos[1] - pos + CLICK_Y_OFFSET;
        const localX = event.canvasX - this.pos[0] + CLICK_X_OFFSET;

        if (isDragging) {
            const totalHeight = getTotalFilesHeight();
            const visibleHeight = this.size[1] - TOP_PADDING - BOTTOM_PADDING - BOTTOM_SKIP;
            const maxOffset = Math.max(0, totalHeight - visibleHeight);
            const scrollMove = (event.canvasY - scrollStartY) * (totalHeight / visibleHeight);
            scrollOffset = Math.max(0, Math.min(maxOffset, scrollStartOffset + scrollMove));
            this.setDirtyCanvas(true);
            return true;
        }

        return false;
    };

    node.onMouseUp = function(event) {
        isDragging = false;
        document.body.style.cursor = 'default';
        return false;
    };

    function updateNodeSize() {
        const width = Math.max(MIN_WIDTH, node.size[0]);
        const height = Math.max(MIN_HEIGHT, node.size[1]);
        node.size[0] = width;
        node.size[1] = height;
    }

    node.onResize = function() {
        updateNodeSize();
        this.setDirtyCanvas(true);
    };

    // Restore selection from widget value on load
    setTimeout(() => {
        selectedFiles = new Set(
            selectedFilesWidget.value.split(',').map(t => t.trim()).filter(t => t !== '')
        );
        invertButton.disabled = selectionModeWidget.value !== "multiple" && selectionModeWidget.value !== "random";
        node.setDirtyCanvas(true);
    }, 0);

    // Initialize
    setTimeout(async () => {
        currentDirectory = await fetchFileInfo(rootDirectoryWidget.value);
        if (currentDirectory) {
            updateFiles();
        }
        updateNodeSize();
    }, 0);
    
const canvasEl = app.canvas.canvas;

    const stopViewportZoom = (event) => {
        // 1. Convert screen coordinates to ComfyUI world coordinates
        const rect = canvasEl.getBoundingClientRect();
        const mouseX = event.clientX - rect.left;
        const mouseY = event.clientY - rect.top;
        const worldPos = app.canvas.convertCanvasToOffset([mouseX, mouseY]);
        
        const localX = worldPos[0] - node.pos[0];
        const localY = worldPos[1] - node.pos[1];

        // 2. Define the exact hit-box for the file browser
        // Check if mouse is within the width of the node AND within the file list Y bounds
        const isOverBrowser = (
            localX >= 0 && 
            localX <= node.size[0] &&
            localY >= TOP_PADDING && 
            localY <= node.size[1] - BOTTOM_SKIP
        );

if (isOverBrowser && !node.flags.collapsed) {
        event.preventDefault(); 
        event.stopPropagation();

        const totalHeight = getTotalFilesHeight();
        const visibleHeight = node.size[1] - TOP_PADDING - BOTTOM_PADDING - BOTTOM_SKIP;
        const maxOffset = Math.max(0, totalHeight - visibleHeight);

        // Update target instead of current offset
        // Adjust the 0.5 multiplier to change scroll speed
        targetScrollOffset = Math.max(0, Math.min(maxOffset, targetScrollOffset + event.deltaY * 0.5));

        // Start the animation loop if it's not running
        if (!isAnimating) {
            isAnimating = true;
            requestAnimationFrame(smoothScrollLoop);
        }
    }
};
function smoothScrollLoop() {
    // The closer the factor (0.1) is to 1, the "snappier" it feels. 
    // Closer to 0.01 feels "heavy" or "floaty".
    const easingFactor = 0.15;
    const diff = targetScrollOffset - scrollOffset;

    if (Math.abs(diff) > 0.1) {
        scrollOffset += diff * easingFactor;
        node.setDirtyCanvas(true);
        requestAnimationFrame(smoothScrollLoop);
    } else {
        scrollOffset = targetScrollOffset;
        isAnimating = false;
        node.setDirtyCanvas(true);
    }
}
    // Use { capture: true } to intercept the event before ComfyUI's zoom listener
    canvasEl.addEventListener('wheel', stopViewportZoom, { passive: false, capture: true });

    // Cleanup when node is removed
    const onRemoved = node.onRemoved;
    node.onRemoved = function() {
        canvasEl.removeEventListener('wheel', stopViewportZoom, { capture: true });
        if (onRemoved) onRemoved.apply(this, arguments);
    };
}
