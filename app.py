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
# SIDEBAR NAVIGATION (LOGICAL STUDIO TERMINOLOGY)
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
    "Batch Text on Multiple Images",
    "Thumbnail Generator",
    "HD Wallpaper Maker"
]

option = st.sidebar.selectbox("Select Feature Module", features)


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
            An integrated toolkit providing neural subject extraction, chromatic harmonization,
            freeform client-side canvas typography, structural similarity diagnostics, and geographic metadata encoding.
        </p>
        <p>
            Choose a processing module from the sidebar or stream intermediate assets across tools via the <b>Active Workspace</b> pipeline.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Available Processing Modules")
    feature_data = [
        ("🟣 Alpha Channel Dual-Image Blending", "Linear interpolation and weighted alpha channel fusion across two image sources."),
        ("🖼️ Neural Subject Segmentation & Compositing", "U2Net neural boundary extraction, edge defringing, and environment lighting harmonization."),
        ("⚫ Monochrome & High-Contrast Desaturation", "Luminance-based grayscale conversion with dynamic range contrast mapping."),
        ("✏️ Color Inversion Pencil Sketching", "Inverted Gaussian convolution with dodge-blend matrix math for pencil sketch simulation."),
        ("🪪 Biometric Passport Photo Grid Matrix", "Automated aspect-ratio cropping and structured multi-tile matrix print layout generation."),
        ("📏 Custom Dimension Pixel Downscaling", "Precision bicubic/Lanczos pixel resizing targeted to explicit dimensional constraints."),
        ("🔍 Structural Similarity Index (SSIM) Analysis", "Luminance, contrast, and structural comparison providing true SSIM perceptual scoring."),
        ("✏️ Freeform Drag-and-Drop Typography Canvas", "Coordinate-independent interactive client-side typography overlay with bounding badge controls."),
        ("🔤 Interactive Chronological Watermarking", "Temporal date-stamping and moveable textual annotations rendered via HTML5 canvas."),
        ("🎨 Photometric Tuning & Spatial Transformation", "Parametric control over brightness, contrast, color saturation, sharpness, and rotational axes."),
        ("📍 EXIF Spatial Metadata & GPS Encoding", "Binary writing of geographical coordinates and timestamp tags directly into JPEG/PNG headers."),
        ("🧩 Batch Canvas Sequence Typography", "Sequential multi-image ordering pipeline with uniform typography overlay application."),
        ("🖼️ Constrained Aspect-Ratio Downsampling", "Maximum boundary-clamped thumbnail generation preserving geometric aspect ratios."),
        ("🌄 Full HD (1080p) Hero Wallpaper Compositor", "Standardized 1920×1080 canvas cropping with styled vector headline typography.")
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
# 2. ALPHA CHANNEL DUAL-IMAGE BLENDING
# ==================================================

elif option == "Alpha Channel Dual-Image Blending":
    st.header("🟣 Alpha Channel Dual-Image Blending")
    st.write("Perform weighted alpha interpolation between two distinct graphic matrices.")

    col1, col2 = st.columns(2)
    with col1:
        img1 = get_primary_image("blend_img1", "Upload Primary Image (Matrix A)")
        if img1:
            st.image(img1, caption="Matrix A", use_container_width=True)
    with col2:
        file2 = st.file_uploader(
            "Upload Secondary Image (Matrix B)", type=["jpg", "jpeg", "png", "webp"], key="blend_img2"
        )
        img2 = load_image(file2) if file2 else None
        if img2:
            st.image(img2, caption="Matrix B", use_container_width=True)

    alpha = st.slider("Alpha Interpolation Weight (Matrix A → Matrix B)", 0.0, 1.0, 0.5, 0.05)

    if img1 and img2:
        img2_matched = img2.resize(img1.size, Image.Resampling.LANCZOS)
        blended = Image.blend(img1, img2_matched, alpha)
        st.subheader("Blended Output")
        show_download(blended, "alpha_blended_image.png")


# ==================================================
# 3. NEURAL SUBJECT SEGMENTATION & COMPOSITING
# ==================================================

elif option == "Neural Subject Segmentation & Compositing":
    st.header("🖼️ Neural Subject Segmentation & Compositing")
    st.write(
        "Extract foreground human subjects using deep neural boundaries and layer them onto target backdrops with edge defringing and ambient color harmonization."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Primary Foreground Subject")
        fg_img = get_primary_image("fg_upload", "Upload Subject Photo (Portrait/Person)")
        if fg_img:
            st.image(fg_img, caption="Foreground Source", use_container_width=True)
    with col2:
        st.subheader("2. Destination Environment Backdrop")
        bg_file = st.file_uploader("Upload Environment Photo (Scenery/Backdrop)", type=["jpg", "jpeg", "png", "webp"], key="bg_upload")
        bg_img = load_image(bg_file) if bg_file else None
        if bg_img:
            st.image(bg_img, caption="Backdrop Source", use_container_width=True)

    if fg_img and bg_img:
        st.markdown("---")
        st.subheader("Spatial Composition & Color Harmonization")

        col_s, col_x, col_y = st.columns(3)
        with col_s:
            scale = st.slider("Subject Scale Ratio", min_value=0.5, max_value=2.0, value=1.25, step=0.05)
        with col_x:
            shift_x = st.slider("Horizontal Axis Translation (px)", min_value=-500, max_value=500, value=0, step=10)
        with col_y:
            shift_y = st.slider("Vertical Axis Translation (px)", min_value=-500, max_value=500, value=0, step=10)

        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            match_lighting = st.checkbox("Harmonize Ambient Lighting & Tone", value=True)
        with col_opt2:
            depth_blur = st.checkbox("Apply Depth-of-Field Blur to Backdrop", value=True)

        if st.button("✨ Execute Neural Composite", key="exec_bg_change"):
            with st.spinner("Executing neural segmentation and chromatic harmonization..."):
                try:
                    from rembg import remove

                    fg_rgba = fg_img.convert("RGBA")
                    cutout = remove(fg_rgba)
                    if not isinstance(cutout, Image.Image):
                        cutout = Image.open(io.BytesIO(cutout)).convert("RGBA")
                    else:
                        cutout = cutout.convert("RGBA")

                    # Edge defringing & alpha erosion
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

                    st.success("Composite rendered successfully!")
                    show_download(result, "neural_composite.png")

                except ImportError:
                    st.error("The `rembg` library is required. Verify that `rembg` and `onnxruntime` are present in `requirements.txt`.")
                except Exception as e:
                    st.error(f"Error during compositing execution: {e}")


# ==================================================
# 4. MONOCHROME & HIGH-CONTRAST DESATURATION
# ==================================================

elif option == "Monochrome & High-Contrast Desaturation":
    st.header("⚫ Monochrome & High-Contrast Desaturation")
    image = get_primary_image("bw_upload")

    if image:
        mode = st.radio(
            "Transfer Function", ["Standard Linear Grayscale", "High-Contrast Tonal Mapping"]
        )
        if mode == "Standard Linear Grayscale":
            result = ImageOps.grayscale(image)
        else:
            gray = ImageOps.grayscale(image)
            enhancer = ImageEnhance.Contrast(gray)
            result = enhancer.enhance(1.8)
        show_download(result.convert("RGB"), "monochrome_desaturated.png")


# ==================================================
# 5. COLOR INVERSION PENCIL SKETCHING
# ==================================================

elif option == "Color Inversion Pencil Sketching":
    st.header("✏️ Color Inversion Pencil Sketching")
    image = get_primary_image("sketch_upload")

    if image:
        blur_radius = st.slider(
            "Gaussian Convolution Radius",
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
# 6. BIOMETRIC PASSPORT PHOTO GRID MATRIX
# ==================================================

elif option == "Biometric Passport Photo Grid Matrix":
    st.header("🪪 Biometric Passport Photo Grid Matrix")
    image = get_primary_image("passport_upload")

    col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
    with col_cfg1:
        copies = st.number_input(
            "Grid Tile Cardinality (Copies)", min_value=1, max_value=36, value=8
        )
    with col_cfg2:
        photo_w = st.number_input(
            "Target Tile Width (px)", min_value=150, max_value=600, value=300
        )
    with col_cfg3:
        photo_h = st.number_input(
            "Target Tile Height (px)", min_value=150, max_value=800, value=350
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

        show_download(sheet, "passport_grid_matrix.png")


# ==================================================
# 7. CUSTOM DIMENSION PIXEL DOWNSCALING
# ==================================================

elif option == "Custom Dimension Pixel Downscaling":
    st.header("📏 Custom Dimension Pixel Downscaling")
    image = get_primary_image("stamp_upload")

    if image:
        col1, col2 = st.columns(2)
        with col1:
            w = st.number_input("Target Horizontal Resolution (px)", min_value=20, max_value=2000, value=150)
        with col2:
            h = st.number_input(
                "Target Vertical Resolution (px)", min_value=20, max_value=2000, value=200
            )

        resized = image.resize((int(w), int(h)), Image.Resampling.LANCZOS)
        show_download(resized, "downscaled_pixel_target.png")


# ==================================================
# 8. STRUCTURAL SIMILARITY INDEX (SSIM) ANALYSIS
# ==================================================

elif option == "Structural Similarity Index (SSIM) Analysis":
    st.header("🔍 Structural Similarity Index (SSIM) Analysis")
    st.write("Quantify perceptual similarity across luminance, contrast, and structure metrics.")

    col1, col2 = st.columns(2)
    with col1:
        img1 = get_primary_image("sim_img1", "Upload Baseline Image (Reference)")
        if img1:
            st.image(img1, caption="Baseline Reference", use_container_width=True)
    with col2:
        file2 = st.file_uploader(
            "Upload Comparison Image (Candidate)", type=["jpg", "jpeg", "png", "webp"], key="sim_img2"
        )
        img2 = load_image(file2) if file2 else None
        if img2:
            st.image(img2, caption="Candidate Asset", use_container_width=True)

    if img1 and img2:
        img1_eval = img1.resize((300, 300), Image.Resampling.LANCZOS)
        img2_eval = img2.resize((300, 300), Image.Resampling.LANCZOS)

        arr1 = np.array(ImageOps.grayscale(img1_eval))
        arr2 = np.array(ImageOps.grayscale(img2_eval))

        try:
            from skimage.metrics import structural_similarity
            score = structural_similarity(arr1, arr2, data_range=255)
            similarity_pct = max(0.0, float(score) * 100.0)
            st.metric("Perceptual SSIM Score", f"{similarity_pct:.2f}%")
        except ImportError:
            mse = np.mean((arr1.astype(float) - arr2.astype(float)) ** 2)
            rmse_similarity = max(0.0, 100.0 - (np.sqrt(mse) / 255.0 * 100.0))
            st.metric(
                "Pixel Euclidean Distance Metric", f"{rmse_similarity:.2f}%"
            )


# ==================================================
# 9. FREEFORM DRAG-AND-DROP TYPOGRAPHY CANVAS
# ==================================================

elif option == "Freeform Drag-and-Drop Typography Canvas":
    st.header("✏️ Freeform Drag-and-Drop Typography Canvas")
    st.info("💡 **Interactive Canvas**: Drag and drop text across the viewport. Real-time font size, color, and semi-transparent bounding controls update without refreshing the Python server.")

    image = get_primary_image("moveable_text_upload")
    user_text = st.text_area(
        "Typography Payload (Multiline supported)",
        value="PragyanAI 🚀\nPrecision Creative Engine ✨",
        height=80,
    )

    if image:
        draggable_text_editor(
            image, user_text or "Typography payload", key="freeform_text_editor"
        )


# ==================================================
# 10. INTERACTIVE CHRONOLOGICAL WATERMARKING
# ==================================================

elif option == "Interactive Chronological Watermarking":
    st.header("🔤 Interactive Chronological Watermarking")
    image = get_primary_image("date_text_upload")

    col_t, col_d = st.columns([2, 1])
    with col_t:
        caption = st.text_input(
            "Annotation Header", placeholder="Archival Document Record"
        )
    with col_d:
        chosen_date = st.date_input("Temporal Timestamp", value=datetime.today().date())

    if image:
        combined_text = (
            f"{caption}\n📅 {chosen_date}" if caption else f"📅 {chosen_date}"
        )
        draggable_text_editor(image, combined_text, key="date_text_moveable_editor")


# ==================================================
# 11. PHOTOMETRIC TUNING & SPATIAL TRANSFORMATION
# ==================================================

elif option == "Photometric Tuning & Spatial Transformation":
    st.header("🎨 Photometric Tuning & Spatial Transformation")
    image = get_primary_image("enhance_upload")

    if image:
        col_ctl, col_rot = st.columns(2)
        with col_ctl:
            brightness = st.slider("Photometric Luminance (Brightness)", 0.2, 2.5, 1.0, 0.05)
            contrast = st.slider("Dynamic Range Contrast", 0.2, 2.5, 1.0, 0.05)
            sharpness = st.slider("High-Frequency Edge Sharpness", 0.0, 3.0, 1.0, 0.1)
            color_sat = st.slider("Chromatic Saturation", 0.0, 3.0, 1.0, 0.1)

        with col_rot:
            st.write("Spatial Geometry Adjustments")
            rotate_angle = st.selectbox("Orthogonal Rotation Angle", [0, 90, 180, 270])
            flip_h = st.checkbox("Reflect Along Vertical Axis (Horizontal Mirror)")
            flip_v = st.checkbox("Reflect Along Horizontal Axis (Vertical Flip)")

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

        show_download(enhanced, "transformed_asset.png")


# ==================================================
# 12. EXIF SPATIAL METADATA & GPS ENCODING
# ==================================================

elif option == "EXIF Spatial Metadata & GPS Encoding":
    st.header("📍 EXIF Spatial Metadata & GPS Encoding")
    st.write(
        "Inject geographic coordinates and ISO timestamps directly into binary EXIF/PNG chunks, with an optional visible telemetry badge."
    )

    image = get_primary_image("geotag_upload")

    if image:
        col_l, col_d = st.columns(2)
        with col_l:
            location = st.text_input(
                "Geographic Location Label", placeholder="e.g. Gateway of India, Mumbai"
            )
            lat = st.number_input("Decimal Latitude (°N/S)", -90.0, 90.0, 18.9220, format="%.5f")
            lon = st.number_input("Decimal Longitude (°E/W)", -180.0, 180.0, 72.8347, format="%.5f")
        with col_d:
            timestamp_str = st.text_input(
                "ISO Timestamp String", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            burn_label = st.checkbox(
                "Burn Visible Telemetry Badge onto Image Buffer", value=True
            )
            export_format = st.selectbox(
                "Container Format",
                ["JPEG (Binary EXIF GPS IFD)", "PNG (tEXt Textual Metadata)"],
            )

        if st.button("📍 Write Spatial Metadata"):
            result = image.copy()
            if burn_label:
                draw = ImageDraw.Draw(result)
                badge_text = (
                    f"📍 {location}\nLAT: {lat:.4f} | LON: {lon:.4f}\nTIME: {timestamp_str}"
                )
                badge_font = get_font(max(16, int(result.width * 0.025)))

                draw.rectangle(
                    [(10, 10), (int(result.width * 0.6), int(result.height * 0.18))],
                    fill="rgba(0,0,0,180)",
                )
                draw.text((20, 20), badge_text, fill="white", font=badge_font)

            output = io.BytesIO()

            if "JPEG" in export_format:
                gps_ifd = {
                    piexif.GPSIFD.GPSLatitudeRef: "N" if lat >= 0 else "S",
                    piexif.GPSIFD.GPSLatitude: to_dms(lat),
                    piexif.GPSIFD.GPSLongitudeRef: "E" if lon >= 0 else "W",
                    piexif.GPSIFD.GPSLongitude: to_dms(lon),
                    piexif.GPSIFD.GPSDateStamp: timestamp_str.split()[0].replace("-", ":"),
                }
                exif_bytes = piexif.dump({"GPS": gps_ifd})
                result.save(output, format="JPEG", quality=95, exif=exif_bytes)
                out_filename = "geotagged_spatial_image.jpg"
                mime_type = "image/jpeg"
            else:
                png_info = PngImagePlugin.PngInfo()
                png_info.add_text("Location", location)
                png_info.add_text("Latitude", str(lat))
                png_info.add_text("Longitude", str(lon))
                png_info.add_text("DateTime", timestamp_str)
                result.save(output, format="PNG", pnginfo=png_info)
                out_filename = "geotagged_spatial_image.png"
                mime_type = "image/png"

            st.success("Spatial EXIF encoded successfully!")
            st.image(result, caption="Tagged Output", use_container_width=True)
            st.download_button(
                label="⬇️ Download Encoded Asset",
                data=output.getvalue(),
                file_name=out_filename,
                mime=mime_type,
                use_container_width=True
            )


# ==================================================
# 13. BATCH CANVAS SEQUENCE TYPOGRAPHY
# ==================================================

elif option == "Batch Canvas Sequence Typography":
    st.header("🧩 Batch Canvas Sequence Typography")
    st.write(
        "Upload and reorder an array of graphic assets, interactively compositing draggable typography across each sequential canvas."
    )

    files = st.file_uploader(
        "Upload Batch Asset Array",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="batch_upload",
    )
    shared_text = st.text_input(
        "Default Sequence Caption", placeholder="Studio Series 2026 ✨"
    )

    if files:
        file_map = {f.name: f for f in files}
        selected_order = st.multiselect(
            "Sequence Pipeline Reorder",
            options=list(file_map.keys()),
            default=list(file_map.keys()),
        )

        for idx, filename in enumerate(selected_order):
            st.markdown(f"### 📷 Asset [{idx + 1}]: `{filename}`")
            img = load_image(file_map[filename])
            if img:
                draggable_text_editor(
                    img,
                    shared_text or f"Asset {idx+1}",
                    key=f"batch_canvas_{idx}_{filename}",
                )


# ==================================================
# 14. CONSTRAINED ASPECT-RATIO DOWNSAMPLING
# ==================================================

elif option == "Constrained Aspect-Ratio Downsampling":
    st.header("🖼️ Constrained Aspect-Ratio Downsampling")
    image = get_primary_image("thumb_upload")

    if image:
        col1, col2 = st.columns(2)
        with col1:
            max_w = st.number_input(
                "Bounding Box Width Ceiling (px)", min_value=50, max_value=1200, value=250
            )
        with col2:
            max_h = st.number_input(
                "Bounding Box Height Ceiling (px)", min_value=50, max_value=1200, value=250
            )

        thumb = image.copy()
        thumb.thumbnail((int(max_w), int(max_h)), Image.Resampling.LANCZOS)
        st.write(
            f"Calculated Aspect-Constrained Dimensions: **{thumb.width} × {thumb.height} px**"
        )
        show_download(thumb, "aspect_constrained_thumbnail.png")


# ==================================================
# 15. FULL HD (1080P) HERO WALLPAPER COMPOSITOR
# ==================================================

elif option == "Full HD (1080p) Hero Wallpaper Compositor":
    st.header("🌄 Full HD (1080p) Hero Wallpaper Compositor")
    image = get_primary_image("wallpaper_upload")
    title = st.text_input("Prominent Hero Title Typography", value="NEO TOKYO 2026")

    if image:
        wallpaper = ImageOps.fit(
            image, (1920, 1080), method=Image.Resampling.LANCZOS
        )
        draw = ImageDraw.Draw(wallpaper)
        font = get_font(size=72)

        draw.text(
            (80, 80),
            title,
            fill="white",
            font=font,
            stroke_width=4,
            stroke_fill="black",
        )
        show_download(wallpaper, "hero_wallpaper_1080p.png")
