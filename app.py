import streamlit as st
from PIL import (
    Image, ImageOps, ImageDraw, ImageFont,
    ImageFilter, ImageEnhance, PngImagePlugin
)
import numpy as np
import io
import os
import base64
import json
from datetime import datetime
import piexif
import streamlit.components.v1 as components

# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="PragyanAI - Pixel_Forge-AI",
    page_icon="🖼️",
    layout="wide"
)

# ==================================================
# SESSION STATE INITIALIZATION
# ==================================================

if "working_image" not in st.session_state:
    st.session_state["working_image"] = None

# ==================================================
# CUSTOM DARK THEME CSS
# ==================================================

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #071329, #101d39, #080f20);
    color: white;
}

[data-testid="stSidebar"] {
    background: #0b1730;
}

[data-testid="stSidebar"] * {
    color: white;
}

h1, h2, h3, h4 {
    color: #ffffff;
}

p, label, span {
    color: #d0d8eb;
}

div.stButton > button {
    background: linear-gradient(90deg, #1769ff, #713bff);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 10px 18px;
    font-weight: bold;
    transition: all 0.2s ease-in-out;
}

div.stButton > button:hover {
    background: linear-gradient(90deg, #4385ff, #925fff);
    color: white;
    transform: translateY(-1px);
}

div[data-testid="stFileUploader"] {
    background: #152541;
    border-radius: 10px;
    padding: 10px;
    border: 1px dashed #2a4269;
}

div[data-testid="stMetric"] {
    background: #14233e;
    padding: 15px;
    border-radius: 10px;
    border: 1px solid #233b66;
}

.feature-card {
    background: linear-gradient(135deg, #172949, #101c35);
    border: 1px solid #2a4269;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 12px;
    min-height: 110px;
}

.feature-card h4 {
    color: #63b3ff;
    margin-bottom: 6px;
}

.feature-card p {
    color: #d4def2;
    font-size: 13px;
    margin: 0;
}

.hero-text {
    background: linear-gradient(135deg, #10254a, #142b55);
    padding: 24px;
    border-radius: 15px;
    border: 1px solid #294b81;
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)


# ==================================================
# HELPER FUNCTIONS & IMAGE PIPELINE
# ==================================================

def load_image(uploaded_file):
    """
    Safely load an uploaded image file, automatically handle EXIF rotation,
    and convert to standard RGB.
    """
    if uploaded_file is None:
        return None
    try:
        img = Image.open(uploaded_file)
        # Fix camera/phone orientation using EXIF data
        img = ImageOps.exif_transpose(img)
        return img.convert("RGB")
    except Exception as e:
        st.error(f"Failed to read image. The file may be corrupt or an unsupported format. Error: {e}")
        return None


def image_to_bytes(image, format="PNG"):
    """Convert a PIL image into downloadable raw bytes."""
    output = io.BytesIO()
    if format.upper() in ["JPG", "JPEG"] and image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    image.save(output, format=format)
    return output.getvalue()


def set_as_working_image(image, success_msg="Image loaded into workspace pipeline!"):
    """Store image in session state for cross-tool reuse."""
    st.session_state["working_image"] = image.copy()
    st.success(success_msg)


def show_download(image, filename="processed_image.png", allow_pipeline=True):
    """Display processed image, download button, and optional send-to-pipeline button."""
    st.image(image, caption="Processed Image", use_container_width=True)
    
    col_dl, col_pipe = st.columns([1, 1])
    with col_dl:
        mime = "image/jpeg" if filename.lower().endswith((".jpg", ".jpeg")) else "image/png"
        fmt = "JPEG" if mime == "image/jpeg" else "PNG"
        st.download_button(
            label="⬇️ Download Image",
            data=image_to_bytes(image, format=fmt),
            file_name=filename,
            mime=mime,
            use_container_width=True
        )
    if allow_pipeline:
        with col_pipe:
            if st.button("🔄 Push to Active Workspace", key=f"pipe_{filename}"):
                set_as_working_image(image, "Sent to workspace! You can now access it in other tabs.")


def get_font(size=30):
    """Load a true type font with fallback logic for Windows, Linux, and macOS."""
    font_candidates = (
        "C:/Windows/Fonts/seguiemj.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    )
    for font_path in font_candidates:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except (OSError, ValueError):
                continue
    return ImageFont.load_default()


def resize_crop(image, size):
    """Resize and center-crop image to exact dimensions."""
    return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)


def to_dms(value):
    """Convert decimal GPS coordinate to degrees/minutes/seconds for EXIF."""
    value = abs(value)
    degrees = int(value)
    minutes_float = (value - degrees) * 60
    minutes = int(minutes_float)
    seconds = round((minutes_float - minutes) * 60 * 10000)
    return (
        (degrees, 1),
        (minutes, 1),
        (seconds, 10000)
    )


# ==================================================
# DRAGGABLE / MOVEABLE INTERACTIVE TEXT CANVAS
# ==================================================

def draggable_text_editor(image, initial_text, key="draggable_text_component"):
    """
    Interactive HTML5 canvas component:
    - Pure drag & drop text positioning using mouse / touch coordinates (no coordinate sliders needed).
    - Font scale adapts automatically to image resolution (works on 500px or 4000px photos).
    - Text styling options: Font size, Color, Background badge toggle, and stroke.
    - Direct export and client-side download as high-res PNG.
    """
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_b64 = base64.b64encode(buffer.getvalue()).decode("ascii")

    # Adapt default font size proportional to image width
    base_dim = max(image.width, image.height)
    default_font_size = max(24, int(base_dim * 0.05))
    min_font_size = max(10, int(base_dim * 0.01))
    max_font_size = max(120, int(base_dim * 0.25))

    text_json = json.dumps(str(initial_text))
    image_json = json.dumps(image_b64)

    html = f"""
    <div style="font-family: Arial, sans-serif; color: #fff; background: #0b1730; padding: 16px; border-radius: 12px; border: 1px solid #2a4269;">
      <div style="display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; align-items: center;">
        <label style="display:flex; align-items:center; gap:6px; font-size:14px;">
            Font Size
            <input id="fs" type="range" min="{min_font_size}" max="{max_font_size}" value="{default_font_size}" style="cursor:pointer;">
            <span id="fs_val" style="min-width:35px; color:#63b3ff;">{default_font_size}px</span>
        </label>
        <label style="display:flex; align-items:center; gap:6px; font-size:14px;">
            Color
            <input id="fc" type="color" value="#ffffff" style="cursor:pointer; border:none; border-radius:4px; height:28px;">
        </label>
        <label style="display:flex; align-items:center; gap:6px; font-size:14px; cursor:pointer;">
            <input id="bg_toggle" type="checkbox" checked style="cursor:pointer;"> Semi-Transparent Badge
        </label>
        <button id="lock_btn" style="background:#1769ff; color:#fff; border:none; padding:6px 12px; border-radius:6px; cursor:pointer; font-weight:bold;">📌 Lock Position</button>
      </div>

      <div style="position: relative; width: 100%; overflow: auto; text-align: center; background: #071022; border-radius: 8px; border: 1px solid #1c3258;">
        <canvas id="c" style="max-width: 100%; height: auto; cursor: grab; display: inline-block; box-shadow: 0 4px 16px rgba(0,0,0,0.5);"></canvas>
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 14px; flex-wrap: wrap; gap: 10px;">
        <span id="status" style="color: #63b3ff; font-size: 13px;">✋ Click and drag the text anywhere on the image.</span>
        <button id="download_btn" style="background: linear-gradient(90deg, #1769ff, #713bff); color:#fff; border:none; padding:10px 20px; border-radius:8px; cursor:pointer; font-weight:bold;">⬇️ Download Result (PNG)</button>
      </div>
    </div>

    <script>
    (function() {{
        const img = new Image();
        img.src = 'data:image/png;base64,' + {image_json};
        const canvas = document.getElementById('c');
        const ctx = canvas.getContext('2d');
        const text = {text_json};
        
        let x = 40, y = 60;
        let size = {default_font_size};
        let color = '#ffffff';
        let showBg = true;
        let isDragging = false;
        let isLocked = false;
        let dragOffset = {{ x: 0, y: 0 }};

        function draw() {{
            if (!img.complete || !img.naturalWidth) return;
            canvas.width = img.naturalWidth;
            canvas.height = img.naturalHeight;

            // Render original image
            ctx.drawImage(img, 0, 0);

            // Configure text styling
            ctx.font = `bold ${{size}}px Arial, sans-serif`;
            ctx.textBaseline = 'top';

            const lines = text.split('\\n');
            let maxLineWidth = 0;
            lines.forEach(line => {{
                maxLineWidth = Math.max(maxLineWidth, ctx.measureText(line).width);
            }});
            const lineHeight = size * 1.25;
            const totalHeight = lines.length * lineHeight;
            const padX = size * 0.35;
            const padY = size * 0.25;

            // Optional background box
            if (showBg) {{
                ctx.fillStyle = 'rgba(0, 0, 0, 0.55)';
                ctx.beginPath();
                ctx.roundRect(x - padX, y - padY, maxLineWidth + (padX * 2), totalHeight + (padY * 2), 6);
                ctx.fill();
            }}

            // Draw bounding selection stroke if unlocked
            if (!isLocked) {{
                ctx.strokeStyle = '#00e1ff';
                ctx.lineWidth = Math.max(2, canvas.width / 600);
                ctx.setLineDash([6, 4]);
                ctx.strokeRect(x - padX, y - padY, maxLineWidth + (padX * 2), totalHeight + (padY * 2));
                ctx.setLineDash([]);
            }}

            // Render text lines with drop shadow/outline for readability
            lines.forEach((line, index) => {{
                ctx.fillStyle = 'rgba(0,0,0,0.8)';
                ctx.fillText(line, x + 2, y + 2 + (index * lineHeight));
                ctx.fillStyle = color;
                ctx.fillText(line, x, y + (index * lineHeight));
            }});
        }}

        img.onload = draw;

        // UI Listeners
        const fsInput = document.getElementById('fs');
        const fsVal = document.getElementById('fs_val');
        fsInput.addEventListener('input', (e) => {{
            size = parseInt(e.target.value);
            fsVal.textContent = size + 'px';
            draw();
        }});

        document.getElementById('fc').addEventListener('input', (e) => {{
            color = e.target.value;
            draw();
        }});

        document.getElementById('bg_toggle').addEventListener('change', (e) => {{
            showBg = e.target.checked;
            draw();
        }});

        const lockBtn = document.getElementById('lock_btn');
        lockBtn.addEventListener('click', () => {{
            isLocked = !isLocked;
            lockBtn.textContent = isLocked ? '🔓 Unlock Position' : '📌 Lock Position';
            lockBtn.style.background = isLocked ? '#22c55e' : '#1769ff';
            canvas.style.cursor = isLocked ? 'default' : 'grab';
            document.getElementById('status').textContent = isLocked ? 'Position locked. Ready to download.' : '✋ Click and drag the text box to reposition.';
            draw();
        }});

        // Coordinate calculations
        function getCanvasPoint(evt) {{
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            return {{
                x: (evt.clientX - rect.left) * scaleX,
                y: (evt.clientY - rect.top) * scaleY
            }};
        }}

        // Freeform Moveable Event Handling
        canvas.addEventListener('pointerdown', (e) => {{
            if (isLocked) return;
            const pt = getCanvasPoint(e);
            isDragging = true;
            dragOffset.x = pt.x - x;
            dragOffset.y = pt.y - y;
            canvas.style.cursor = 'grabbing';
            canvas.setPointerCapture(e.pointerId);
        }});

        canvas.addEventListener('pointermove', (e) => {{
            if (!isDragging || isLocked) return;
            const pt = getCanvasPoint(e);
            x = Math.max(10, Math.min(canvas.width - 50, pt.x - dragOffset.x));
            y = Math.max(10, Math.min(canvas.height - 50, pt.y - dragOffset.y));
            draw();
        }});

        function stopDrag(e) {{
            if (!isDragging) return;
            isDragging = false;
            if (!isLocked) canvas.style.cursor = 'grab';
        }}

        canvas.addEventListener('pointerup', stopDrag);
        canvas.addEventListener('pointercancel', stopDrag);

        // Download output image
        document.getElementById('download_btn').addEventListener('click', () => {{
            // Temporarily lock to remove dashed selection border on export
            const prevLock = isLocked;
            isLocked = true;
            draw();

            const link = document.createElement('a');
            link.download = 'edited_image_with_text.png';
            link.href = canvas.toDataURL('image/png');
            link.click();

            isLocked = prevLock;
            draw();
        }});
    }})();
    </script>
    """
    components.html(html, height=720, scrolling=True)


# ==================================================
# HEADER BANNER (CACHED)
# ==================================================

@st.cache_data(show_spinner=False)
def get_banner_image():
    # 1x1 fallback placeholder if embedded base64 is missing
    fallback_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    try:
        raw_b64 = globals().get("BANNER_IMAGE_BASE64", fallback_b64)
        bytes_data = base64.b64decode(raw_b64)
        return Image.open(io.BytesIO(bytes_data)).convert("RGB")
    except Exception:
        return Image.new("RGB", (1200, 200), color="#101d39")

st.image(get_banner_image(), use_container_width=True)


# ==================================================
# SIDEBAR NAVIGATION
# ==================================================

st.sidebar.title("🖼️ PragyanAI")
st.sidebar.caption("Pixel_Forge Image Studio")

# Workspace Status Widget
if st.session_state["working_image"] is not None:
    st.sidebar.success("🟢 Active Image in Workspace")
    if st.sidebar.button("Clear Workspace Image"):
        st.session_state["working_image"] = None
        st.rerun()

st.sidebar.markdown("---")

features = [
    "Home",
    "Image Blending",
    "Background Change",
    "Color to Black and White",
    "Color to Sketch",
    "Passport Size Photo Frame",
    "Stamp Size Photo",
    "Image Similarity",
    "Add Text to Image (Moveable)",
    "Add Date and Text (Moveable)",
    "Image Enhancements & Rotate",
    "Geo-Tag Image",
    "Multiple Images with Text",
    "Thumbnail Generator",
    "Wallpaper with Title"
]

option = st.sidebar.selectbox("Select Feature", features)


# Helper to get either upload or pipeline image
def get_primary_image(uploader_key, label="Upload Image"):
    col_up, col_info = st.columns([2, 1])
    with col_up:
        uploaded_file = st.file_uploader(label, type=["jpg", "jpeg", "png", "webp"], key=uploader_key)
    
    with col_info:
        use_workspace = False
        if st.session_state["working_image"] is not None:
            use_workspace = st.checkbox("Use Image from Workspace", value=(uploaded_file is None), key=f"use_ws_{uploader_key}")

    if use_workspace and st.session_state["working_image"] is not None:
        return st.session_state["working_image"].copy()
    if uploaded_file:
        return load_image(uploaded_file)
    return None


# ==================================================
# 1. HOME PAGE
# ==================================================

if option == "Home":
    st.markdown("""
    <div class="hero-text">
        <h2>Welcome to PragyanAI Image Studio</h2>
        <p>
            An all-in-one suite for professional image manipulation, AI background replacement,
            freeform drag-and-drop text overlay, geo-tagging, similarity analysis, and print frames.
        </p>
        <p>
            Select any tool from the sidebar or pass images between tools using the <b>Active Workspace</b> pipeline!
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Explore Tool Suite")
    feature_data = [
        ("🟣 Image Blending", "Blend two images together seamlessly with transparency control."),
        ("🖼️ Background Change", "AI-powered subject cutout and background replacement."),
        ("⚫ Black & White", "High-contrast grayscale and monochrome conversions."),
        ("✏️ Sketch Effect", "Turn portraits and landscapes into realistic pencil sketches."),
        ("🪪 Passport Photo Frame", "Generate standard multi-copy passport photo print sheets."),
        ("📏 Stamp Size Photo", "Resize images to custom pixel dimensions."),
        ("🔍 Image Similarity", "Structural Similarity Index (SSIM) image comparison."),
        ("✏️ Moveable Text", "Freeform interactive drag-and-drop text and emoji overlay."),
        ("🔤 Date & Text", "Stamp moveable dates, times, and captions without position sliders."),
        ("🎨 Enhancements & Rotate", "Brightness, contrast, sharpness, saturation, and rotation."),
        ("📍 Geo-Tag Image", "Burn EXIF GPS metadata & optional overlay badges."),
        ("🧩 Batch Image Overlay", "Add draggable text and reorder batches of images."),
        ("🖼️ Thumbnail Maker", "Generate constrained aspect-ratio thumbnails."),
        ("🌄 Wallpaper Generator", "Produce 1080p full-HD desktop wallpapers with custom styling.")
    ]

    cols = st.columns(3)
    for i, (title, desc) in enumerate(feature_data):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="feature-card">
                <h4>{title}</h4>
                <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)


# ==================================================
# 2. IMAGE BLENDING
# ==================================================

elif option == "Image Blending":
    st.header("🟣 Image Blending")
    st.write("Blend two images together using an adjustable transparency alpha ratio.")

    col1, col2 = st.columns(2)
    with col1:
        img1 = get_primary_image("blend_img1", "Upload First Image")
        if img1:
            st.image(img1, caption="Image 1", use_container_width=True)
    with col2:
        file2 = st.file_uploader("Upload Second Image", type=["jpg", "jpeg", "png", "webp"], key="blend_img2")
        img2 = load_image(file2) if file2 else None
        if img2:
            st.image(img2, caption="Image 2", use_container_width=True)

    alpha = st.slider("Blending Weight (Image 1 → Image 2)", 0.0, 1.0, 0.5, 0.05)

    if img1 and img2:
        img2_matched = img2.resize(img1.size, Image.Resampling.LANCZOS)
        blended = Image.blend(img1, img2_matched, alpha)
        st.subheader("Result")
        show_download(blended, "blended_image.png")


# ==================================================
# 3. BACKGROUND CHANGE
# ==================================================

elif option == "Background Change":
    st.header("🖼️ Background Change (AI)")
    st.write("Remove the foreground background and composite it onto a new background image.")

    col1, col2 = st.columns(2)
    with col1:
        fg_img = get_primary_image("fg_upload", "Upload Foreground Subject")
        if fg_img:
            st.image(fg_img, caption="Foreground", use_container_width=True)
    with col2:
        bg_file = st.file_uploader("Upload New Background", type=["jpg", "jpeg", "png", "webp"], key="bg_upload")
        bg_img = load_image(bg_file) if bg_file else None
        if bg_img:
            st.image(bg_img, caption="Background", use_container_width=True)

    if fg_img and bg_img:
        if st.button("✨ Remove & Replace Background", key="exec_bg_change"):
            with st.spinner("Processing cutout with rembg..."):
                try:
                    from rembg import remove
                    fg_rgba = fg_img.convert("RGBA")
                    fg_cutout = remove(fg_rgba)
                    if not isinstance(fg_cutout, Image.Image):
                        fg_cutout = Image.open(io.BytesIO(fg_cutout)).convert("RGBA")
                    else:
                        fg_cutout = fg_cutout.convert("RGBA")

                    # Match background to foreground dimensions
                    bg_matched = ImageOps.fit(bg_img.convert("RGBA"), fg_cutout.size, method=Image.Resampling.LANCZOS)
                    bg_matched.alpha_composite(fg_cutout)
                    result = bg_matched.convert("RGB")
                    
                    st.success("Background successfully changed!")
                    show_download(result, "new_background.png")
                except ImportError:
                    st.error("The `rembg` library is required for AI background removal. Install it using `pip install rembg`.")
                except Exception as e:
                    st.error(f"Error while removing background: {e}")


# ==================================================
# 4. COLOR TO BLACK AND WHITE
# ==================================================

elif option == "Color to Black and White":
    st.header("⚫ Color to Black and White")
    image = get_primary_image("bw_upload")

    if image:
        mode = st.radio("Conversion Type", ["Standard Grayscale", "High-Contrast Monochrome"])
        if mode == "Standard Grayscale":
            result = ImageOps.grayscale(image)
        else:
            gray = ImageOps.grayscale(image)
            enhancer = ImageEnhance.Contrast(gray)
            result = enhancer.enhance(1.8)
        show_download(result.convert("RGB"), "black_and_white.png")


# ==================================================
# 5. COLOR TO SKETCH
# ==================================================

elif option == "Color to Sketch":
    st.header("✏️ Color to Pencil Sketch")
    image = get_primary_image("sketch_upload")

    if image:
        blur_radius = st.slider("Sketch Softness / Detail", min_value=1, max_value=30, value=10, step=1)
        gray = ImageOps.grayscale(image)
        inverted = ImageOps.invert(gray)
        blurred = inverted.filter(ImageFilter.GaussianBlur(radius=blur_radius))

        gray_np = np.array(gray).astype(float)
        blurred_np = np.array(blurred).astype(float)

        # Color dodge blend algorithm
        sketch_np = gray_np * 255.0 / (255.0 - blurred_np + 1.0)
        sketch_np = np.clip(sketch_np, 0, 255)
        sketch = Image.fromarray(sketch_np.astype(np.uint8))
        show_download(sketch.convert("RGB"), "pencil_sketch.png")


# ==================================================
# 6. PASSPORT SIZE PHOTO FRAME
# ==================================================

elif option == "Passport Size Photo Frame":
    st.header("🪪 Passport Size Photo Sheet Generator")
    image = get_primary_image("passport_upload")

    col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
    with col_cfg1:
        copies = st.number_input("Number of Copies", min_value=1, max_value=36, value=8)
    with col_cfg2:
        photo_w = st.number_input("Photo Width (px)", min_value=150, max_value=600, value=300)
    with col_cfg3:
        photo_h = st.number_input("Photo Height (px)", min_value=150, max_value=800, value=350)

    if image:
        passport_tile = resize_crop(image, (int(photo_w), int(photo_h)))
        cols = 4 if int(copies) > 12 else 3
        rows = (int(copies) + cols - 1) // cols
        margin = 30
        gap = 20

        sheet_w = (margin * 2) + (cols * int(photo_w)) + ((cols - 1) * gap)
        sheet_h = (margin * 2) + (rows * int(photo_h)) + ((rows - 1) * gap)

        sheet = Image.new("RGB", (sheet_w, sheet_h), "white")
        draw = ImageDraw.Draw(sheet)

        for i in range(int(copies)):
            r = i // cols
            c = i % cols
            x = margin + c * (int(photo_w) + gap)
            y = margin + r * (int(photo_h) + gap)
            sheet.paste(passport_tile, (x, y))
            draw.rectangle([x, y, x + int(photo_w), y + int(photo_h)], outline="#999999", width=1)

        show_download(sheet, "passport_sheet.png")


# ==================================================
# 7. STAMP SIZE PHOTO
# ==================================================

elif option == "Stamp Size Photo":
    st.header("📏 Stamp Size Photo Resizer")
    image = get_primary_image("stamp_upload")

    if image:
        col1, col2 = st.columns(2)
        with col1:
            w = st.number_input("Width (px)", min_value=20, max_value=2000, value=150)
        with col2:
            h = st.number_input("Height (px)", min_value=20, max_value=2000, value=200)

        resized = image.resize((int(w), int(h)), Image.Resampling.LANCZOS)
        show_download(resized, "stamp_photo.png")


# ==================================================
# 8. IMAGE SIMILARITY (SSIM)
# ==================================================

elif option == "Image Similarity":
    st.header("🔍 Image Similarity Comparison")
    st.write("Compare two images using the Structural Similarity Index (SSIM).")

    col1, col2 = st.columns(2)
    with col1:
        img1 = get_primary_image("sim_img1", "Upload First Image")
        if img1:
            st.image(img1, caption="Image 1", use_container_width=True)
    with col2:
        file2 = st.file_uploader("Upload Second Image", type=["jpg", "jpeg", "png", "webp"], key="sim_img2")
        img2 = load_image(file2) if file2 else None
        if img2:
            st.image(img2, caption="Image 2", use_container_width=True)

    if img1 and img2:
        img1_eval = img1.resize((300, 300), Image.Resampling.LANCZOS)
        img2_eval = img2.resize((300, 300), Image.Resampling.LANCZOS)

        arr1 = np.array(ImageOps.grayscale(img1_eval))
        arr2 = np.array(ImageOps.grayscale(img2_eval))

        try:
            from skimage.metrics import structural_similarity
            score = structural_similarity(arr1, arr2, data_range=255)
            similarity_pct = max(0.0, float(score) * 100.0)
            st.metric("Similarity Score", f"{similarity_pct:.2f}%")
        except ImportError:
            # Fallback: Root Mean Squared Error similarity estimate
            mse = np.mean((arr1.astype(float) - arr2.astype(float)) ** 2)
            rmse_similarity = max(0.0, 100.0 - (np.sqrt(mse) / 255.0 * 100.0))
            st.metric("Similarity Score (Pixel Distance Metric)", f"{rmse_similarity:.2f}%")
            st.caption("Tip: Install `scikit-image` for true structural SSIM analysis.")


# ==================================================
# 9. ADD TEXT TO IMAGE (MOVEABLE - NO SLIDER COORDS)
# ==================================================

elif option == "Add Text to Image (Moveable)":
    st.header("✏️ Add Moveable Text (Interactive Drag & Drop)")
    st.info("💡 **How it works:** Type your text below, then **click and drag** it anywhere on the image canvas. You can change colors, sizes, or lock it down before downloading!")

    image = get_primary_image("moveable_text_upload")
    user_text = st.text_area("Enter Text / Caption (Emojis supported)", value="PragyanAI 🚀\nAwesome Edit! ✨", height=80)

    if image:
        draggable_text_editor(image, user_text or "Enter text ✨", key="freeform_text_editor")


# ==================================================
# 10. ADD DATE AND TEXT (MOVEABLE)
# ==================================================

elif option == "Add Date and Text (Moveable)":
    st.header("🔤 Add Moveable Date & Caption")
    image = get_primary_image("date_text_upload")

    col_t, col_d = st.columns([2, 1])
    with col_t:
        caption = st.text_input("Caption (Emojis supported)", placeholder="Vacation Memories 🏖️")
    with col_d:
        chosen_date = st.date_input("Date", value=datetime.today().date())

    if image:
        combined_text = f"{caption}\n📅 {chosen_date}" if caption else f"📅 {chosen_date}"
        draggable_text_editor(image, combined_text, key="date_text_moveable_editor")


# ==================================================
# 11. IMAGE ENHANCEMENTS & ROTATION
# ==================================================

elif option == "Image Enhancements & Rotate":
    st.header("🎨 Image Enhancements & Orientation")
    image = get_primary_image("enhance_upload")

    if image:
        col_ctl, col_rot = st.columns(2)
        with col_ctl:
            brightness = st.slider("Brightness", 0.2, 2.5, 1.0, 0.05)
            contrast = st.slider("Contrast", 0.2, 2.5, 1.0, 0.05)
            sharpness = st.slider("Sharpness", 0.0, 3.0, 1.0, 0.1)
            color_sat = st.slider("Saturation", 0.0, 3.0, 1.0, 0.1)

        with col_rot:
            st.write("Orientation & Flips")
            rotate_angle = st.selectbox("Rotate Angle", [0, 90, 180, 270])
            flip_h = st.checkbox("Flip Horizontally (Mirror)")
            flip_v = st.checkbox("Flip Vertically")

        # Apply adjustments sequentially
        enhanced = image.copy()
        if brightness != 1.0:
            enhanced = ImageEnhance.Brightness(enhanced).enhance(brightness)
        if contrast != 1.0:
            enhanced = ImageEnhance.Contrast(enhanced).enhance(contrast)
        if sharpness != 1.0:
            enhanced = ImageEnhance.Sharpness(enhanced).enhance(sharpness)
        if color_sat != 1.0:
            enhanced = ImageEnhance.Color(enhanced).enhance(color_sat)

        if rotate_angle != 0:
            enhanced = enhanced.rotate(-rotate_angle, expand=True)
        if flip_h:
            enhanced = ImageOps.mirror(enhanced)
        if flip_v:
            enhanced = ImageOps.flip(enhanced)

        show_download(enhanced, "enhanced_image.png")


# ==================================================
# 12. GEO-TAG IMAGE
# ==================================================

elif option == "Geo-Tag Image":
    st.header("📍 Geo-Tag Image (EXIF & Overlay)")
    st.write("Inject GPS coordinates and timestamps directly into image EXIF metadata, with an optional visible badge.")

    image = get_primary_image("geotag_upload")

    if image:
        col_l, col_d = st.columns(2)
        with col_l:
            location = st.text_input("Location Name", placeholder="e.g. Gateway of India, Mumbai")
            lat = st.number_input("Latitude", -90.0, 90.0, 18.9220, format="%.5f")
            lon = st.number_input("Longitude", -180.0, 180.0, 72.8347, format="%.5f")
        with col_d:
            timestamp_str = st.text_input("Date and Time", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            burn_label = st.checkbox("Burn Visible Metadata Overlay Badge onto Image", value=True)
            export_format = st.selectbox("File Format", ["JPEG (Embeds EXIF GPS)", "PNG (Embeds Chunk Info)"])

        if st.button("📍 Write Geo-Tag"):
            result = image.copy()
            if burn_label:
                draw = ImageDraw.Draw(result)
                badge_text = f"📍 {location}\nLAT: {lat:.4f} | LON: {lon:.4f}\nTIME: {timestamp_str}"
                badge_font = get_font(max(16, int(result.width * 0.025)))
                
                # Draw dark background badge
                pad = 12
                draw.rectangle([(10, 10), (int(result.width * 0.6), int(result.height * 0.18))], fill="rgba(0,0,0,180)")
                draw.text((20, 20), badge_text, fill="white", font=badge_font)

            output = io.BytesIO()

            if "JPEG" in export_format:
                gps_ifd = {
                    piexif.GPSIFD.GPSLatitudeRef: "N" if lat >= 0 else "S",
                    piexif.GPSIFD.GPSLatitude: to_dms(lat),
                    piexif.GPSIFD.GPSLongitudeRef: "E" if lon >= 0 else "W",
                    piexif.GPSIFD.GPSLongitude: to_dms(lon),
                    piexif.GPSIFD.GPSDateStamp: timestamp_str.split()[0].replace("-", ":")
                }
                exif_bytes = piexif.dump({"GPS": gps_ifd})
                result.save(output, format="JPEG", quality=95, exif=exif_bytes)
                out_filename = "geotagged_image.jpg"
                mime_type = "image/jpeg"
            else:
                png_info = PngImagePlugin.PngInfo()
                png_info.add_text("Location", location)
                png_info.add_text("Latitude", str(lat))
                png_info.add_text("Longitude", str(lon))
                png_info.add_text("DateTime", timestamp_str)
                result.save(output, format="PNG", pnginfo=png_info)
                out_filename = "geotagged_image.png"
                mime_type = "image/png"

            st.success("Geo-Tag applied successfully!")
            st.image(result, caption="Geo-Tagged Image", use_container_width=True)
            st.download_button(
                label="⬇️ Download Geo-Tagged Image",
                data=output.getvalue(),
                file_name=out_filename,
                mime=mime_type,
                use_container_width=True
            )


# ==================================================
# 13. MULTIPLE IMAGES WITH TEXT (MOVEABLE)
# ==================================================

elif option == "Multiple Images with Text":
    st.header("🧩 Batch Images with Moveable Text")
    st.write("Upload multiple images and apply interactive drag-and-drop captions to each one.")

    files = st.file_uploader("Upload Multiple Images", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True, key="batch_upload")
    shared_text = st.text_input("Default Caption / Emoji", placeholder="Holiday 2026 🏖️")

    if files:
        file_map = {f.name: f for f in files}
        selected_order = st.multiselect("Reorder Images", options=list(file_map.keys()), default=list(file_map.keys()))

        for idx, filename in enumerate(selected_order):
            st.markdown(f"### 📷 Image {idx + 1}: `{filename}`")
            img = load_image(file_map[filename])
            if img:
                draggable_text_editor(img, shared_text or f"Photo {idx+1} ✨", key=f"batch_canvas_{idx}_{filename}")


# ==================================================
# 14. THUMBNAIL GENERATOR
# ==================================================

elif option == "Thumbnail Generator":
    st.header("🖼️ Constrained Aspect-Ratio Thumbnail Generator")
    image = get_primary_image("thumb_upload")

    if image:
        col1, col2 = st.columns(2)
        with col1:
            max_w = st.number_input("Max Width (px)", min_value=50, max_value=1200, value=250)
        with col2:
            max_h = st.number_input("Max Height (px)", min_value=50, max_value=1200, value=250)

        thumb = image.copy()
        thumb.thumbnail((int(max_w), int(max_h)), Image.Resampling.LANCZOS)
        st.write(f"Generated Thumbnail Dimensions: **{thumb.width} × {thumb.height} px**")
        show_download(thumb, "thumbnail.png")


# ==================================================
# 15. WALLPAPER WITH TITLE
# ==================================================

elif option == "Wallpaper with Title":
    st.header("🌄 Full HD 1080p Wallpaper Generator")
    image = get_primary_image("wallpaper_upload")
    title = st.text_input("Wallpaper Title", value="NATURE VIBES 🌿")

    if image:
        # Fit precisely to 16:9 1080p Full HD
        wallpaper = ImageOps.fit(image, (1920, 1080), method=Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(wallpaper)
        font = get_font(size=72)

        # Draw stroke for high-contrast visibility against any photo
        draw.text(
            (80, 80),
            title,
            fill="white",
            font=font,
            stroke_width=4,
            stroke_fill="black"
        )
        show_download(wallpaper, "wallpaper_1080p.png")
```eof
http://googleusercontent.com/immersive_entry_chip/0

I have generated `app.py` with full drag-and-drop text positioning, EXIF orientation correction, session-state pipeline chaining, and image enhancement controls, along with the accompanying `README.md`.

***

<FollowUp>
<ElicitationsGroup>
Would you like to add interactive polygon or aspect-ratio bounding box cropping (e.g., using `streamlit-cropper`), or add additional custom TTF font upload capabilities for the canvas?
</ElicitationsGroup>
</FollowUp>
