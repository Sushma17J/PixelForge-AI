import base64
from datetime import datetime
import io
import json
import os
from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
    ImageOps,
    PngImagePlugin,
)
import numpy as np
import piexif
import streamlit as st
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
# HEADER BANNER (banner.png)
# ==================================================

BANNER_PATH = "banner.png"

if os.path.exists(BANNER_PATH):
    st.image(BANNER_PATH, use_container_width=True)
else:
    st.markdown(
        """
        <div style="background: linear-gradient(90deg, #0b1730, #142b55); padding: 25px; border-radius: 10px; text-align: center; border: 1px solid #233b66; margin-bottom: 20px;">
            <h1 style="color: #63b3ff; margin: 0; font-size: 30px;">🖼️ PragyanAI - Pixel_Forge-AI</h1>
            <p style="color: #d4def2; margin: 5px 0 0 0; font-size: 14px;">Studio Image Processing & Enhancement</p>
        </div>
        """,
        unsafe_allow_html=True
    )


# ==================================================
# HELPER FUNCTIONS & IMAGE PIPELINE
# ==================================================

def load_image(uploaded_file):
    if uploaded_file is None:
        return None
    try:
        img = Image.open(uploaded_file)
        img = ImageOps.exif_transpose(img)
        return img.convert("RGB")
    except Exception as e:
        st.error(f"Failed to read image. File may be corrupt or unsupported format. Error: {e}")
        return None


def image_to_bytes(image, format="PNG"):
    output = io.BytesIO()
    if format.upper() in ["JPG", "JPEG"] and image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    image.save(output, format=format)
    return output.getvalue()


def set_as_working_image(image, success_msg="Image loaded into workspace pipeline!"):
    st.session_state["working_image"] = image.copy()
    st.success(success_msg)


def show_download(image, filename="processed_image.png", allow_pipeline=True):
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
    return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)


def to_dms(value):
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


def create_location_app_stamp(
    image,
    location_name,
    lat,
    lon,
    timestamp_str,
    badge_style="GPS Camera Card",
    position="Bottom Left"
):
    img_w, img_h = image.size
    overlay = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    title_size = max(18, int(img_w * 0.032))
    sub_size = max(13, int(img_w * 0.020))

    title_font = get_font(title_size)
    sub_font = get_font(sub_size)

    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"
    coord_str = f"Lat: {abs(lat):.4f}° {lat_dir}  |  Long: {abs(lon):.4f}° {lon_dir}"
    time_label = f"📅 {timestamp_str}"

    lines = [
        f"📍 {location_name or 'Current Location'}",
        coord_str,
        time_label
    ]

    line_heights = [int(title_size * 1.3), int(sub_size * 1.4), int(sub_size * 1.4)]
    total_text_h = sum(line_heights)
    max_text_w = max(
        int(len(lines[0]) * title_size * 0.65),
        int(len(lines[1]) * sub_size * 0.60),
        int(len(lines[2]) * sub_size * 0.60)
    )

    pad_x = int(img_w * 0.025)
    pad_y = int(img_h * 0.020)
    card_w = max_text_w + (pad_x * 2)
    card_h = total_text_h + (pad_y * 2)

    if badge_style == "Full Bottom Bar":
        box_x0 = 0
        box_y0 = img_h - card_h - int(img_h * 0.01)
        box_x1 = img_w
        box_y1 = img_h
        text_x = pad_x
        text_y = box_y0 + pad_y
        draw.rectangle([box_x0, box_y0, box_x1, box_y1], fill=(15, 23, 42, 200))
    else:
        margin = int(img_w * 0.03)
        if position == "Bottom Left":
            box_x0 = margin
            box_y0 = img_h - card_h - margin
        elif position == "Bottom Right":
            box_x0 = img_w - card_w - margin
            box_y0 = img_h - card_h - margin
        else:
            box_x0 = margin
            box_y0 = margin

        box_x1 = box_x0 + card_w
        box_y1 = box_y0 + card_h
        text_x = box_x0 + pad_x
        text_y = box_y0 + pad_y

        radius = max(8, int(img_w * 0.015))
        draw.rounded_rectangle(
            [box_x0, box_y0, box_x1, box_y1],
            radius=radius,
            fill=(10, 18, 35, 195),
            outline=(56, 189, 248, 140),
            width=max(1, int(img_w * 0.002))
        )

    curr_y = text_y
    draw.text((text_x, curr_y), lines[0], font=title_font, fill=(255, 255, 255, 255))
    curr_y += line_heights[0]

    draw.text((text_x, curr_y), lines[1], font=sub_font, fill=(56, 189, 248, 240))
    curr_y += line_heights[1]

    draw.text((text_x, curr_y), lines[2], font=sub_font, fill=(226, 232, 240, 220))

    base_rgba = image.convert("RGBA")
    composited = Image.alpha_composite(base_rgba, overlay)
    return composited.convert("RGB")


# ==================================================
# DRAGGABLE / MOVEABLE INTERACTIVE TEXT CANVAS
# ==================================================

def draggable_text_editor(image, initial_text, key="draggable_text_component"):
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_b64 = base64.b64encode(buffer.getvalue()).decode("ascii")

    base_dim = max(image.width, image.height)
    default_font_size = max(24, int(base_dim * 0.05))
    min_font_size = max(10, int(base_dim * 0.01))
    max_font_size = max(120, int(base_dim * 0.25))

    lines_list = [line for line in str(initial_text).split("\n")]
    lines_json = json.dumps(lines_list)
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
        const canvas = document.getElementById('c');
        const ctx = canvas.getContext('2d');
        const lines = {lines_json};
        
        let x = 40, y = 60;
        let size = {default_font_size};
        let color = '#ffffff';
        let showBg = true;
        let isDragging = false;
        let isLocked = false;
        let dragOffset = {{ x: 0, y: 0 }};

        const img = new Image();
        img.src = 'data:image/png;base64,' + {image_json};

        function draw() {{
            if (!img.complete || !img.naturalWidth) return;
            canvas.width = img.naturalWidth;
            canvas.height = img.naturalHeight;

            ctx.drawImage(img, 0, 0);

            ctx.font = 'bold ' + size + 'px Arial, sans-serif';
            ctx.textBaseline = 'top';

            let maxLineWidth = 0;
            lines.forEach(function(line) {{
                maxLineWidth = Math.max(maxLineWidth, ctx.measureText(line).width);
            }});
            const lineHeight = size * 1.25;
            const totalHeight = lines.length * lineHeight;
            const padX = size * 0.35;
            const padY = size * 0.25;

            if (showBg) {{
                ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
                ctx.fillRect(x - padX, y - padY, maxLineWidth + (padX * 2), totalHeight + (padY * 2));
            }}

            if (!isLocked) {{
                ctx.strokeStyle = '#00e1ff';
                ctx.lineWidth = Math.max(2, canvas.width / 600);
                if (ctx.setLineDash) {{
                    ctx.setLineDash([6, 4]);
                }}
                ctx.strokeRect(x - padX, y - padY, maxLineWidth + (padX * 2), totalHeight + (padY * 2));
                if (ctx.setLineDash) {{
                    ctx.setLineDash([]);
                }}
            }}

            lines.forEach(function(line, index) {{
                ctx.fillStyle = 'rgba(0,0,0,0.85)';
                ctx.fillText(line, x + 2, y + 2 + (index * lineHeight));
                ctx.fillStyle = color;
                ctx.fillText(line, x, y + (index * lineHeight));
            }});
        }}

        if (img.complete) {{
            draw();
        }} else {{
            img.onload = draw;
        }}

        const fsInput = document.getElementById('fs');
        const fsVal = document.getElementById('fs_val');
        fsInput.addEventListener('input', function(e) {{
            size = parseInt(e.target.value);
            fsVal.textContent = size + 'px';
            draw();
        }});

        document.getElementById('fc').addEventListener('input', function(e) {{
            color = e.target.value;
            draw();
        }});

        document.getElementById('bg_toggle').addEventListener('change', function(e) {{
            showBg = e.target.checked;
            draw();
        }});

        const lockBtn = document.getElementById('lock_btn');
        lockBtn.addEventListener('click', function() {{
            isLocked = !isLocked;
            lockBtn.textContent = isLocked ? '🔓 Unlock Position' : '📌 Lock Position';
            lockBtn.style.background = isLocked ? '#22c55e' : '#1769ff';
            canvas.style.cursor = isLocked ? 'default' : 'grab';
            document.getElementById('status').textContent = isLocked ? 'Position locked. Ready to download.' : '✋ Click and drag the text box to reposition.';
            draw();
        }});

        function getCanvasPoint(evt) {{
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            return {{
                x: (evt.clientX - rect.left) * scaleX,
                y: (evt.clientY - rect.top) * scaleY
            }};
        }}

        canvas.addEventListener('pointerdown', function(e) {{
            if (isLocked) return;
            const pt = getCanvasPoint(e);
            isDragging = true;
            dragOffset.x = pt.x - x;
            dragOffset.y = pt.y - y;
            canvas.style.cursor = 'grabbing';
            canvas.setPointerCapture(e.pointerId);
        }});

        canvas.addEventListener('pointermove', function(e) {{
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

        document.getElementById('download_btn').addEventListener('click', function() {{
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
    components.html(html, height=760, scrolling=True)


# ==================================================
# SIDEBAR NAVIGATION
# ==================================================

st.sidebar.title("🖼️ PragyanAI")
st.sidebar.caption("Pixel_Forge Image Studio")

if st.session_state["working_image"] is not None:
    st.sidebar.success("🟢 Active Image in Workspace")
    if st.sidebar.button("Clear Workspace Image"):
        st.session_state["working_image"] = None
        st.rerun()

st.sidebar.markdown("---")

features = [
    "Home",
    "Blend Two Images",
    "AI Background Changer",
    "Black & White Converter",
    "Pencil Sketch Converter",
    "Passport Photo Maker",
    "Custom Size Resizer",
    "Image Comparison (Match %)",
    "Drag & Drop Text Editor",
    "Add Date & Stamp",
    "Adjust & Rotate Photo",
    "Add GPS Location (Geo-Tag)",
    "Photo Collage, Wallpaper & Frame Story",
    "Thumbnail Generator"
]

option = st.sidebar.selectbox("Select a Tool", features)


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
# 1. HOME DASHBOARD
# ==================================================

if option == "Home":
    st.markdown("""
    <div class="hero-text">
        <h2>PragyanAI Studio & Analytical Suite</h2>
        <p>
            An all-in-one suite for AI background replacement, drag-and-drop text overlay,
            photo filters, GPS camera watermarking, and custom frame stories.
        </p>
        <p>
            Choose a tool from the sidebar or pass images between tools using the <b>Active Workspace</b> pipeline!
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Available Tools")
    feature_data = [
        ("🟣 Blend Two Images", "Blend two images together seamlessly with transparency control."),
        ("🖼️ AI Background Changer", "Cut out people or objects and place them in front of new scenery."),
        ("⚫ Black & White Converter", "Convert colorful photos into sharp grayscale or high-contrast monochrome."),
        ("✏️ Pencil Sketch Converter", "Turn portraits and landscapes into realistic pencil sketches."),
        ("🪪 Passport Photo Maker", "Generate multiple passport-sized copies on a single print sheet."),
        ("📏 Custom Size Resizer", "Resize images to custom width and height dimensions."),
        ("🔍 Image Comparison (Match %)", "Compare two photos and get an exact similarity score percentage."),
        ("✏️ Drag & Drop Text Editor", "Add text and emojis that you can freely drag anywhere on your image."),
        ("🔤 Add Date & Stamp", "Stamp dates and captions directly onto your images."),
        ("🎨 Adjust & Rotate Photo", "Change brightness, contrast, sharpness, saturation, and rotation."),
        ("📍 Add GPS Location (Geo-Tag)", "Burn realistic GPS camera location badges & EXIF data."),
        ("🧩 Photo Collage, Wallpaper & Frame Story", "Order photos into multi-image collages or 1080p wallpapers with title text."),
        ("🖼️ Thumbnail Generator", "Quickly create clean thumbnails without distorting image proportions.")
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
# 2. BLEND TWO IMAGES
# ==================================================

elif option == "Blend Two Images":
    st.header("🟣 Blend Two Images")
    st.write("Blend two images together using an adjustable transparency alpha ratio.")

    col1, col2 = st.columns(2)
    with col1:
        img1 = get_primary_image("blend_img1", "Upload First Image")
        if img1:
            st.image(img1, caption="Image 1", use_container_width=True)
    with col2:
        file2 = st.file_uploader(
            "Upload Second Image", type=["jpg", "jpeg", "png", "webp"], key="blend_img2"
        )
        img2 = load_image(file2) if file2 else None
        if img2:
            st.image(img2, caption="Image 2", use_container_width=True)

    alpha = st.slider("Blending Weight (Image 1 → Image 2)", 0.0, 1.0, 0.5, 0.05)

    if img1 and img2:
        img2_matched = img2.resize(img1.size, Image.Resampling.LANCZOS)
        blended = Image.blend(img1, img2_matched, alpha)
        st.subheader("Blended Output")
        show_download(blended, "blended_image.png")


# ==================================================
# 3. AI BACKGROUND CHANGER
# ==================================================

elif option == "AI Background Changer":
    st.header("🖼️ AI Background Changer")
    st.write(
        "Upload a photo of a **person/subject** and a **new scenery/background** photo. "
        "The AI extracts the subject and places them **in front of** the new scenery cleanly."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Subject / Person")
        fg_img = get_primary_image("fg_upload", "Upload Subject Photo (Person/Portrait)")
        if fg_img:
            st.image(fg_img, caption="Subject (Foreground)", use_container_width=True)
    with col2:
        st.subheader("2. New Background Scenery")
        bg_file = st.file_uploader("Upload Scenery Photo (Eiffel Tower/Nature)", type=["jpg", "jpeg", "png", "webp"], key="bg_upload")
        bg_img = load_image(bg_file) if bg_file else None
        if bg_img:
            st.image(bg_img, caption="Scenery (Background)", use_container_width=True)

    if fg_img and bg_img:
        st.markdown("---")
        st.subheader("Composition & Scale")

        col_s, col_x, col_y = st.columns(3)
        with col_s:
            scale = st.slider("Subject Scale", min_value=0.5, max_value=2.0, value=1.25, step=0.05)
        with col_x:
            shift_x = st.slider("Horizontal Position (Left ↔ Right)", min_value=-500, max_value=500, value=0, step=10)
        with col_y:
            shift_y = st.slider("Vertical Position (Up ↕ Down)", min_value=-500, max_value=500, value=0, step=10)

        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            match_lighting = st.checkbox("Harmonize Lighting & Color Tone", value=True)
        with col_opt2:
            depth_blur = st.checkbox("Subtle Background Blur (DSLR Depth)", value=True)

        if st.button("✨ Apply Background Change", key="exec_bg_change"):
            with st.spinner("Extracting subject with rembg and compositing..."):
                try:
                    from rembg import remove

                    fg_rgba = fg_img.convert("RGBA")
                    cutout = remove(fg_rgba)
                    if not isinstance(cutout, Image.Image):
                        cutout = Image.open(io.BytesIO(cutout)).convert("RGBA")
                    else:
                        cutout = cutout.convert("RGBA")

                    r, g, b, a = cutout.split()
                    a = a.filter(ImageFilter.GaussianBlur(radius=1))
                    a = a.point(lambda p: 255 if p > 210 else (0 if p < 40 else p))
                    cutout = Image.merge("RGBA", (r, g, b, a))

                    target_w, target_h = bg_img.size
                    bg_canvas = bg_img.convert("RGBA")

                    if depth_blur:
                        bg_canvas = bg_canvas.filter(ImageFilter.GaussianBlur(radius=3))

                    if match_lighting:
                        bg_thumb = bg_img.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
                        fg_thumb = fg_img.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))

                        r_fac = 1.0 + ((bg_thumb[0] / (fg_thumb[0] + 1e-4)) - 1.0) * 0.28
                        g_fac = 1.0 + ((bg_thumb[1] / (fg_thumb[1] + 1e-4)) - 1.0) * 0.28
                        b_fac = 1.0 + ((bg_thumb[2] / (fg_thumb[2] + 1e-4)) - 1.0) * 0.28

                        cr, cg, cb, ca = cutout.split()
                        cr = cr.point(lambda p: min(255, int(p * r_fac)))
                        cg = cg.point(lambda p: min(255, int(p * g_fac)))
                        cb = cb.point(lambda p: min(255, int(p * b_fac)))
                        cutout = Image.merge("RGBA", (cr, cg, cb, ca))

                    new_w = max(50, int(cutout.width * scale))
                    new_h = max(50, int(cutout.height * scale))
                    cutout = cutout.resize((new_w, new_h), Image.Resampling.LANCZOS)

                    pos_x = (target_w - cutout.width) // 2 + shift_x
                    pos_y = (target_h - cutout.height) + shift_y

                    bg_canvas.paste(cutout, (pos_x, pos_y), mask=cutout)
                    result = bg_canvas.convert("RGB")

                    st.success("Background replaced cleanly!")
                    show_download(result, "new_scenery_portrait.png")

                except ImportError:
                    st.error("The `rembg` library is required. Ensure `rembg>=2.0.50` and `onnxruntime` are in `requirements.txt`.")
                except Exception as e:
                    st.error(f"Error while processing background change: {e}")


# ==================================================
# 4. BLACK & WHITE CONVERTER
# ==================================================

elif option == "Black & White Converter":
    st.header("⚫ Black & White Converter")
    image = get_primary_image("bw_upload")

    if image:
        mode = st.radio(
            "Conversion Type", ["Standard Grayscale", "High-Contrast Monochrome"]
        )
        if mode == "Standard Grayscale":
            result = ImageOps.grayscale(image)
        else:
            gray = ImageOps.grayscale(image)
            enhancer = ImageEnhance.Contrast(gray)
            result = enhancer.enhance(1.8)
        show_download(result.convert("RGB"), "black_and_white.png")


# ==================================================
# 5. PENCIL SKETCH CONVERTER
# ==================================================

elif option == "Pencil Sketch Converter":
    st.header("✏️ Pencil Sketch Converter")
    image = get_primary_image("sketch_upload")

    if image:
        blur_radius = st.slider(
            "Sketch Softness / Detail",
            min_value=1,
            max_value=30,
            value=10,
            step=1,
        )
        gray = ImageOps.grayscale(image)
        inverted = ImageOps.invert(gray)
        blurred = inverted.filter(ImageFilter.GaussianBlur(radius=blur_radius))

        gray_np = np.array(gray).astype(float)
        blurred_np = np.array(blurred).astype(float)

        sketch_np = gray_np * 255.0 / (255.0 - blurred_np + 1.0)
        sketch_np = np.clip(sketch_np, 0, 255)
        sketch = Image.fromarray(sketch_np.astype(np.uint8))
        show_download(sketch.convert("RGB"), "pencil_sketch.png")


# ==================================================
# 6. PASSPORT PHOTO MAKER
# ==================================================

elif option == "Passport Photo Maker":
    st.header("🪪 Passport Photo Maker")
    image = get_primary_image("passport_upload")

    col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
    with col_cfg1:
        copies = st.number_input(
            "Number of Copies", min_value=1, max_value=36, value=8
        )
    with col_cfg2:
        photo_w = st.number_input(
            "Photo Width (px)", min_value=150, max_value=600, value=300
        )
    with col_cfg3:
        photo_h = st.number_input(
            "Photo Height (px)", min_value=150, max_value=800, value=350
        )

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
            draw.rectangle(
                [x, y, x + int(photo_w), y + int(photo_h)],
                outline="#999999",
                width=1,
            )

        show_download(sheet, "passport_sheet.png")


# ==================================================
# 7. CUSTOM SIZE RESIZER
# ==================================================

elif option == "Custom Size Resizer":
    st.header("📏 Custom Size Resizer")
    image = get_primary_image("stamp_upload")

    if image:
        col1, col2 = st.columns(2)
        with col1:
            w = st.number_input("Width (px)", min_value=20, max_value=2000, value=150)
        with col2:
            h = st.number_input(
                "Height (px)", min_value=20, max_value=2000, value=200
            )

        resized = image.resize((int(w), int(h)), Image.Resampling.LANCZOS)
        show_download(resized, "resized_photo.png")


# ==================================================
# 8. IMAGE COMPARISON (MATCH %)
# ==================================================

elif option == "Image Comparison (Match %)":
    st.header("🔍 Image Comparison (Match %)")
    st.write("Compare two images using the Structural Similarity Index (SSIM).")

    col1, col2 = st.columns(2)
    with col1:
        img1 = get_primary_image("sim_img1", "Upload First Image")
        if img1:
            st.image(img1, caption="Image 1", use_container_width=True)
    with col2:
        file2 = st.file_uploader(
            "Upload Second Image", type=["jpg", "jpeg", "png", "webp"], key="sim_img2"
        )
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
            mse = np.mean((arr1.astype(float) - arr2.astype(float)) ** 2)
            rmse_similarity = max(0.0, 100.0 - (np.sqrt(mse) / 255.0 * 100.0))
            st.metric(
                "Similarity Score (Pixel Distance Metric)", f"{rmse_similarity:.2f}%"
            )


# ==================================================
# 9. DRAG & DROP TEXT EDITOR
# ==================================================

elif option == "Drag & Drop Text Editor":
    st.header("✏️ Drag & Drop Text Editor")
    st.info("💡 **How it works:** Type your text below, then **click and drag** it anywhere on the image canvas. You can change colors, sizes, or lock it down before downloading!")

    image = get_primary_image("moveable_text_upload")
    user_text = st.text_area(
        "Enter Text / Caption (Emojis supported)",
        value="PragyanAI 🚀\nAwesome Edit! ✨",
        height=80,
    )

    if image:
        draggable_text_editor(
            image, user_text or "Enter text ✨", key="freeform_text_editor"
        )


# ==================================================
# 10. ADD DATE & STAMP
# ==================================================

elif option == "Add Date & Stamp":
    st.header("🔤 Add Date & Stamp")
    image = get_primary_image("date_text_upload")

    col_t, col_d = st.columns([2, 1])
    with col_t:
        caption = st.text_input(
            "Caption (Emojis supported)", placeholder="Vacation Memories 🏖️"
        )
    with col_d:
        chosen_date = st.date_input("Date", value=datetime.today().date())

    if image:
        combined_text = (
            f"{caption}\n📅 {chosen_date}" if caption else f"📅 {chosen_date}"
        )
        draggable_text_editor(image, combined_text, key="date_text_moveable_editor")


# ==================================================
# 11. ADJUST & ROTATE PHOTO
# ==================================================

elif option == "Adjust & Rotate Photo":
    st.header("🎨 Adjust & Rotate Photo")
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
# 12. ADD GPS LOCATION (GEO-TAG)
# ==================================================

elif option == "Add GPS Location (Geo-Tag)":
    st.header("📍 Add GPS Location (Geo-Tag)")
    st.write(
        "Embed EXIF GPS metadata and burn a **GPS Camera-style location badge** directly onto your photo."
    )

    image = get_primary_image("geotag_upload")

    if image:
        col_l, col_d = st.columns(2)
        with col_l:
            location = st.text_input(
                "Location Name / Landmark",
                value="Gateway of India, Mumbai, Maharashtra",
                placeholder="e.g. Marina Beach, Chennai"
            )
            lat = st.number_input("Latitude", -90.0, 90.0, 18.9220, format="%.5f", step=0.0001)
            lon = st.number_input("Longitude", -180.0, 180.0, 72.8347, format="%.5f", step=0.0001)
        with col_d:
            timestamp_str = st.text_input(
                "Date & Time",
                value=datetime.now().strftime("%d %b %Y, %I:%M %p")
            )
            badge_style = st.selectbox(
                "Badge Design",
                ["GPS Camera Card (Glassmorphism)", "Full Bottom Bar", "No Visible Stamp (EXIF Metadata Only)"]
            )
            position = st.selectbox("Stamp Position", ["Bottom Left", "Bottom Right", "Top Left"])
            export_format = st.selectbox(
                "Output File Format",
                ["JPEG (Embeds Binary EXIF GPS Tags)", "PNG (Embeds Metadata Chunks)"]
            )

        if st.button("📍 Generate Geo-Tagged Photo", key="btn_apply_geotag"):
            result = image.copy()
            if badge_style != "No Visible Stamp (EXIF Metadata Only)":
                style_key = "Full Bottom Bar" if badge_style == "Full Bottom Bar" else "GPS Camera Card"
                result = create_location_app_stamp(
                    result, location, lat, lon, timestamp_str, style_key, position
                )

            output = io.BytesIO()

            if "JPEG" in export_format:
                gps_ifd = {
                    piexif.GPSIFD.GPSLatitudeRef: "N" if lat >= 0 else "S",
                    piexif.GPSIFD.GPSLatitude: to_dms(lat),
                    piexif.GPSIFD.GPSLongitudeRef: "E" if lon >= 0 else "W",
                    piexif.GPSIFD.GPSLongitude: to_dms(lon),
                    piexif.GPSIFD.GPSDateStamp: datetime.now().strftime("%Y:%m:%d").encode("utf-8")
                }
                exif_bytes = piexif.dump({"GPS": gps_ifd})
                result.save(output, format="JPEG", quality=95, exif=exif_bytes)
                out_filename = "geotagged_camera_photo.jpg"
                mime_type = "image/jpeg"
            else:
                png_info = PngImagePlugin.PngInfo()
                png_info.add_text("Location", location)
                png_info.add_text("Latitude", str(lat))
                png_info.add_text("Longitude", str(lon))
                png_info.add_text("DateTime", timestamp_str)
                result.save(output, format="PNG", pnginfo=png_info)
                out_filename = "geotagged_camera_photo.png"
                mime_type = "image/png"

            st.success("Geo-Tag stamp applied successfully!")
            show_download(result, out_filename)


# ==================================================
# 13. PHOTO COLLAGE, WALLPAPER & FRAME STORY
# ==================================================

elif option == "Photo Collage, Wallpaper & Frame Story":
    st.header("🧩 Photo Collage, Wallpaper & Frame Story")
    st.write(
        "Upload photos, arrange their order, select a layout "
        "(or Full HD 1080p Wallpaper mode), and position your title/text freely across the finished frame."
    )

    files = st.file_uploader(
        "Upload Photos",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="collage_wallpaper_upload"
    )

    if files:
        file_map = {f.name: f for f in files}
        
        st.subheader("1. Arrange Photo Order")
        selected_order = st.multiselect(
            "Select sequence (1st photo, 2nd photo, etc.):",
            options=list(file_map.keys()),
            default=list(file_map.keys())
        )

        col_layout, col_space = st.columns(2)
        with col_layout:
            layout_style = st.selectbox(
                "Canvas Output Format",
                [
                    "Full HD 1080p Wallpaper (1920x1080)",
                    "Vertical Strip (Stacked)",
                    "Horizontal Strip (Side-by-Side)",
                    "2-Column Photo Grid"
                ]
            )
        with col_space:
            spacing = st.slider("Spacing Between Photos (px)", 0, 50, 15)

        story_text = st.text_area(
            "Headline Title / Caption (Emojis supported)",
            value="NATURE VIBES 🌿\nAdventure 2026",
            height=70
        )

        if selected_order and st.button("🖼️ Generate Combined Canvas / Wallpaper", key="btn_build_canvas"):
            ordered_imgs = [load_image(file_map[name]) for name in selected_order if file_map.get(name)]
            
            if layout_style == "Full HD 1080p Wallpaper (1920x1080)":
                total_w, total_h = 1920, 1080
                collage_canvas = Image.new("RGB", (total_w, total_h), (8, 15, 30))
                num_imgs = len(ordered_imgs)

                if num_imgs == 1:
                    collage_canvas = ImageOps.fit(ordered_imgs[0], (total_w, total_h), method=Image.Resampling.LANCZOS)
                elif num_imgs == 2:
                    cell_w = (total_w - (spacing * 3)) // 2
                    cell_h = total_h - (spacing * 2)
                    for i, im in enumerate(ordered_imgs[:2]):
                        cropped = ImageOps.fit(im, (cell_w, cell_h), method=Image.Resampling.LANCZOS)
                        x = spacing + i * (cell_w + spacing)
                        collage_canvas.paste(cropped, (x, spacing))
                elif num_imgs == 3:
                    hero_w = int(total_w * 0.6) - spacing
                    right_w = total_w - hero_w - (spacing * 3)
                    half_h = (total_h - (spacing * 3)) // 2

                    hero_img = ImageOps.fit(ordered_imgs[0], (hero_w, total_h - (spacing * 2)), method=Image.Resampling.LANCZOS)
                    collage_canvas.paste(hero_img, (spacing, spacing))

                    top_r = ImageOps.fit(ordered_imgs[1], (right_w, half_h), method=Image.Resampling.LANCZOS)
                    collage_canvas.paste(top_r, (hero_w + (spacing * 2), spacing))

                    bot_r = ImageOps.fit(ordered_imgs[2], (right_w, half_h), method=Image.Resampling.LANCZOS)
                    collage_canvas.paste(bot_r, (hero_w + (spacing * 2), half_h + (spacing * 2)))
                else:
                    cell_w = (total_w - (spacing * 3)) // 2
                    cell_h = (total_h - (spacing * 3)) // 2
                    for i, im in enumerate(ordered_imgs[:4]):
                        r_idx = i // 2
                        c_idx = i % 2
                        cropped = ImageOps.fit(im, (cell_w, cell_h), method=Image.Resampling.LANCZOS)
                        x = spacing + c_idx * (cell_w + spacing)
                        y = spacing + r_idx * (cell_h + spacing)
                        collage_canvas.paste(cropped, (x, y))

            elif layout_style == "Vertical Strip (Stacked)":
                target_w = 900
                resized_imgs = []
                for img in ordered_imgs:
                    ratio = target_w / float(img.width)
                    target_h = int(float(img.height) * float(ratio))
                    resized_imgs.append(img.resize((target_w, target_h), Image.Resampling.LANCZOS))

                total_w = target_w + (spacing * 2)
                total_h = sum(im.height for im in resized_imgs) + (spacing * (len(resized_imgs) + 1))
                collage_canvas = Image.new("RGB", (total_w, total_h), (8, 15, 30))

                curr_y = spacing
                for im in resized_imgs:
                    collage_canvas.paste(im, (spacing, curr_y))
                    curr_y += im.height + spacing

            elif layout_style == "Horizontal Strip (Side-by-Side)":
                fixed_h = 600
                horiz_resized = []
                for img in ordered_imgs:
                    r = fixed_h / float(img.height)
                    w = int(float(img.width) * float(r))
                    horiz_resized.append(img.resize((w, fixed_h), Image.Resampling.LANCZOS))

                total_w = sum(im.width for im in horiz_resized) + (spacing * (len(horiz_resized) + 1))
                total_h = fixed_h + (spacing * 2)
                collage_canvas = Image.new("RGB", (total_w, total_h), (8, 15, 30))

                curr_x = spacing
                for im in horiz_resized:
                    collage_canvas.paste(im, (curr_x, spacing))
                    curr_x += im.width + spacing

            else:
                cols = 2
                grid_cell_size = (600, 450)
                grid_imgs = [resize_crop(im, grid_cell_size) for im in ordered_imgs]
                
                rows = (len(grid_imgs) + cols - 1) // cols
                total_w = (grid_cell_size[0] * cols) + (spacing * (cols + 1))
                total_h = (grid_cell_size[1] * rows) + (spacing * (rows + 1))
                collage_canvas = Image.new("RGB", (total_w, total_h), (8, 15, 30))

                for i, im in enumerate(grid_imgs):
                    r_idx = i // cols
                    c_idx = i % cols
                    x = spacing + c_idx * (grid_cell_size[0] + spacing)
                    y = spacing + r_idx * (grid_cell_size[1] + spacing)
                    collage_canvas.paste(im, (x, y))

            st.session_state["active_collage"] = collage_canvas
            st.success("Canvas generated! Position your text title below.")

        if "active_collage" in st.session_state and st.session_state["active_collage"] is not None:
            st.markdown("---")
            st.subheader("2. Drag & Position Your Title Anywhere on the Frame")
            draggable_text_editor(
                st.session_state["active_collage"],
                story_text or "Wallpaper Title",
                key="collage_story_canvas"
            )


# ==================================================
# 14. THUMBNAIL GENERATOR
# ==================================================

elif option == "Thumbnail Generator":
    st.header("🖼️ Thumbnail Generator")
    image = get_primary_image("thumb_upload")

    if image:
        col1, col2 = st.columns(2)
        with col1:
            max_w = st.number_input(
                "Max Width (px)", min_value=50, max_value=1200, value=250
            )
        with col2:
            max_h = st.number_input(
                "Max Height (px)", min_value=50, max_value=1200, value=250
            )

        thumb = image.copy()
        thumb.thumbnail((int(max_w), int(max_h)), Image.Resampling.LANCZOS)
        st.write(
            f"Generated Thumbnail Dimensions: **{thumb.width} × {thumb.height} px**"
        )
        show_download(thumb, "thumbnail.png")
