// Track image inputs through Canvas without exporting the composed page bitmap.
(() => {
    if (window.__kindleSources) return;
    const blobs = new WeakMap(), bitmaps = new WeakMap(), canvases = new WeakMap();
    const urls = new Map(), sources = new Map();
    let nextId = 1;
    const sourceIds = blob => {
        if (!blobs.has(blob)) {
            const id = nextId++;
            blobs.set(blob, [id]);
            sources.set(id, blob);
        }
        return blobs.get(blob);
    };
    const inputs = image => {
        if (bitmaps.has(image)) return bitmaps.get(image);
        if (canvases.has(image)) return canvases.get(image);
        return urls.get(image.currentSrc || image.src) || [];
    };
    const createURL = URL.createObjectURL;
    URL.createObjectURL = function (blob) {
        const url = createURL.call(this, blob);
        if (blob instanceof Blob) urls.set(url, sourceIds(blob));
        return url;
    };
    // Keep provenance after revokeObjectURL: loaded images may still be drawn.
    if (window.createImageBitmap) {
        const createBitmap = window.createImageBitmap;
        window.createImageBitmap = async function (image, ...args) {
            const result = await createBitmap.call(this, image, ...args);
            bitmaps.set(result, image instanceof Blob ? sourceIds(image) : inputs(image));
            return result;
        };
    }
    const hookContext = prototype => {
        const draw = prototype.drawImage, clear = prototype.clearRect;
        prototype.drawImage = function (image, ...args) {
            const result = draw.call(this, image, ...args);
            const ids = [...(canvases.get(this.canvas) || [])];
            for (const id of inputs(image)) if (!ids.includes(id)) ids.push(id);
            canvases.set(this.canvas, ids);
            return result;
        };
        prototype.clearRect = function (x, y, w, h) {
            const result = clear.call(this, x, y, w, h);
            const t = this.getTransform();
            if (t.isIdentity && x <= 0 && y <= 0 && w >= this.canvas.width && h >= this.canvas.height)
                canvases.set(this.canvas, []);
            return result;
        };
        if (prototype.reset) {
            const reset = prototype.reset;
            prototype.reset = function (...args) {
                const result = reset.apply(this, args);
                canvases.set(this.canvas, []);
                return result;
            };
        }
    };
    hookContext(CanvasRenderingContext2D.prototype);
    if (window.OffscreenCanvasRenderingContext2D) hookContext(OffscreenCanvasRenderingContext2D.prototype);
    const hookResize = prototype => {
        for (const key of ['width', 'height']) {
            const descriptor = Object.getOwnPropertyDescriptor(prototype, key);
            if (!descriptor?.set) continue;
            Object.defineProperty(prototype, key, {...descriptor, set(value) {
                descriptor.set.call(this, value);
                canvases.set(this, []);
            }});
        }
    };
    hookResize(HTMLCanvasElement.prototype);
    const toBlob = HTMLCanvasElement.prototype.toBlob;
    HTMLCanvasElement.prototype.toBlob = function (callback, ...args) {
        const ids = [...(canvases.get(this) || [])];
        return toBlob.call(this, blob => {
            if (blob) blobs.set(blob, ids);
            callback(blob);
        }, ...args);
    };
    if (window.OffscreenCanvas) {
        hookResize(OffscreenCanvas.prototype);
        const convert = OffscreenCanvas.prototype.convertToBlob;
        OffscreenCanvas.prototype.convertToBlob = async function (...args) {
            const ids = [...(canvases.get(this) || [])];
            const blob = await convert.apply(this, args);
            blobs.set(blob, ids);
            return blob;
        };
        const transfer = OffscreenCanvas.prototype.transferToImageBitmap;
        OffscreenCanvas.prototype.transferToImageBitmap = function (...args) {
            const ids = [...(canvases.get(this) || [])];
            const bitmap = transfer.apply(this, args);
            bitmaps.set(bitmap, ids);
            canvases.set(this, []);
            return bitmap;
        };
    }
    window.__kindleSources = {
        ids(url) { return urls.get(url) || []; },
        async read(id) {
            const blob = sources.get(id);
            if (!blob) throw new Error('Image source no longer available');
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result.split(',')[1]);
                reader.onerror = () => reject(new Error('Cannot read source image'));
                reader.readAsDataURL(blob);
            });
        },
        release(ids) { for (const id of ids) sources.delete(id); }
    };
})();
