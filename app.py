import streamlit as st
from PIL import (
    Image, ImageOps, ImageDraw, ImageFont,
    ImageFilter, ImageChops, PngImagePlugin
)
import numpy as np
import io
import os
from datetime import datetime
import piexif


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="PragyanAI - Pixel_Forge-AI",
    page_icon="🖼️",
    layout="wide"
)


# ==================================================
# CUSTOM DARK THEME
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

h1, h2, h3 {
    color: #ffffff;
}

p, label {
    color: #d0d8eb;
}

div.stButton > button {
    background: linear-gradient(90deg, #1769ff, #713bff);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 10px 18px;
    font-weight: bold;
}

div.stButton > button:hover {
    background: linear-gradient(90deg, #4385ff, #925fff);
    color: white;
}

div[data-testid="stFileUploader"] {
    background: #152541;
    border-radius: 10px;
    padding: 10px;
}

div[data-testid="stMetric"] {
    background: #14233e;
    padding: 15px;
    border-radius: 10px;
}

.feature-card {
    background: linear-gradient(135deg, #172949, #101c35);
    border: 1px solid #2a4269;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 12px;
    min-height: 100px;
}

.feature-card h4 {
    color: #63b3ff;
    margin-bottom: 8px;
}

.feature-card p {
    color: #d4def2;
    font-size: 14px;
}

.hero-text {
    background: linear-gradient(135deg, #10254a, #142b55);
    padding: 25px;
    border-radius: 15px;
    border: 1px solid #294b81;
}

</style>
""", unsafe_allow_html=True)


# ==================================================
# HELPER FUNCTIONS
# ==================================================

def load_image(uploaded_file):
    """Load an uploaded image and convert to RGB."""
    return Image.open(uploaded_file).convert("RGB")


def get_font(size=30):
    """Load a font with fallback."""
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        return ImageFont.load_default()


def image_to_bytes(image, format="PNG"):
    """Convert image to downloadable bytes."""
    output = io.BytesIO()
    image.save(output, format=format)
    return output.getvalue()


def show_download(image, filename="processed_image.png"):
    """Display processed image and download button."""
    st.image(
        image,
        caption="Processed Image",
        use_container_width=True
    )

    st.download_button(
        label="⬇️ Download Image",
        data=image_to_bytes(image),
        file_name=filename,
        mime="image/png"
    )


def resize_crop(image, size):
    """Resize and crop image to exact dimensions."""
    return ImageOps.fit(image, size)


def to_dms(value):
    """Convert decimal GPS coordinate to degrees/minutes/seconds."""
    value = abs(value)

    degrees = int(value)
    minutes_float = (value - degrees) * 60
    minutes = int(minutes_float)

    seconds = round(
        (minutes_float - minutes) * 60 * 10000
    )

    return (
        (degrees, 1),
        (minutes, 1),
        (seconds, 10000)
    )


# ==================================================
# HEADER AND BANNER
# ==================================================

# Banner image should be in the same folder as app.py
banner_path = "banner.png"

if os.path.exists(banner_path):
    st.image(
        banner_path,
        use_container_width=True
    )
else:
    st.markdown("""
    <div class="hero-text">
        <h1>🖼️ PragyanAI</h1>
        <h3>Image Applications Studio</h3>
        <p>Transform Images • Explore Techniques • Learn by Doing</p>
    </div>
    """, unsafe_allow_html=True)


st.title("PragyanAI - Image Applications Studio")

st.write(
    "Upload images and apply different image processing "
    "and enhancement techniques."
)


# ==================================================
# SIDEBAR NAVIGATION
# ==================================================

st.sidebar.title("🖼️ PragyanAI")

st.sidebar.caption("Image Applications Studio")

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
    "Add Date and Text",
    "Geo-Tag Image",
    "Multiple Images with Text",
    "Thumbnail Generator",
    "Wallpaper with Title"
]

option = st.sidebar.selectbox(
    "Select Image Feature",
    features
)


# ==================================================
# HOME PAGE
# ==================================================

if option == "Home":

    st.markdown("""
    <div class="hero-text">
        <h2>Welcome to Image Applications Studio</h2>
        <p>
        Transform your images using different image processing
        and enhancement techniques.
        </p>
        <p>
        Select a feature from the sidebar to get started.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Explore Image Processing Tools")

    feature_data = [
        ("🟣 Image Blending", "Blend two images together."),
        ("🖼️ Background Change", "Replace an image background."),
        ("⚫ Black and White", "Convert color images to grayscale."),
        ("✏️ Sketch Effect", "Convert images into pencil sketches."),
        ("🪪 Passport Photo", "Create a passport-size photo sheet."),
        ("📏 Stamp Size Photo", "Resize images to stamp dimensions."),
        ("🔍 Image Similarity", "Compare two images."),
        ("🔤 Add Date and Text", "Add text and dates to images."),
        ("📍 Geo-Tag Image", "Add location information."),
        ("🧩 Multiple Images", "Arrange images with text."),
        ("🖼️ Thumbnail Generator", "Create image thumbnails."),
        ("🌄 Wallpaper with Title", "Create wallpapers with titles.")
    ]

    columns = st.columns(3)

    for i, (title, description) in enumerate(feature_data):

        with columns[i % 3]:

            st.markdown(f"""
            <div class="feature-card">
                <h4>{title}</h4>
                <p>{description}</p>
            </div>
            """, unsafe_allow_html=True)


# ==================================================
# IMAGE BLENDING
# ==================================================

elif option == "Image Blending":

    st.header("🟣 Image Blending")

    st.write("Blend two images using a selected blending ratio.")

    col1, col2 = st.columns(2)

    with col1:
        file1 = st.file_uploader(
            "Upload First Image",
            type=["jpg", "jpeg", "png"],
            key="blend1"
        )

    with col2:
        file2 = st.file_uploader(
            "Upload Second Image",
            type=["jpg", "jpeg", "png"],
            key="blend2"
        )

    alpha = st.slider(
        "Blending Ratio",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.05
    )

    if file1 and file2:

        img1 = load_image(file1)
        img2 = load_image(file2)

        img2 = img2.resize(img1.size)

        blended = Image.blend(
            img1,
            img2,
            alpha
        )

        st.subheader("Blended Image")

        show_download(
            blended,
            "blended_image.png"
        )


# ==================================================
# BACKGROUND CHANGE
# ==================================================

elif option == "Background Change":

    st.header("🖼️ Background Change")

    st.write(
        "Upload a foreground image and a new background image."
    )

    col1, col2 = st.columns(2)

    with col1:
        foreground_file = st.file_uploader(
            "Upload Foreground Image",
            type=["jpg", "jpeg", "png"],
            key="foreground"
        )

    with col2:
        background_file = st.file_uploader(
            "Upload New Background",
            type=["jpg", "jpeg", "png"],
            key="background"
        )

    if foreground_file and background_file:

        if st.button("✨ Change Background"):

            try:

                from rembg import remove

                foreground = Image.open(
                    foreground_file
                ).convert("RGBA")

                # Remove original background
                foreground_no_bg = remove(foreground)

                background = Image.open(
                    background_file
                ).convert("RGBA")

                # Resize background
                background = background.resize(
                    foreground_no_bg.size
                )

                # Combine images
                background.alpha_composite(
                    foreground_no_bg
                )

                result = background.convert("RGB")

                show_download(
                    result,
                    "background_changed.png"
                )

            except Exception as e:

                st.error(
                    "Background removal failed. "
                    "Check the rembg installation."
                )

                st.exception(e)


# ==================================================
# COLOR TO BLACK AND WHITE
# ==================================================

elif option == "Color to Black and White":

    st.header("⚫ Color to Black and White")

    file = st.file_uploader(
        "Upload Image",
        type=["jpg", "jpeg", "png"],
        key="bw"
    )

    if file:

        image = load_image(file)

        grayscale = ImageOps.grayscale(image)

        show_download(
            grayscale,
            "black_white.png"
        )


# ==================================================
# COLOR TO SKETCH
# ==================================================

elif option == "Color to Sketch":

    st.header("✏️ Color to Sketch")

    file = st.file_uploader(
        "Upload Image",
        type=["jpg", "jpeg", "png"],
        key="sketch"
    )

    if file:

        image = load_image(file)

        gray = ImageOps.grayscale(image)

        inverted = ImageOps.invert(gray)

        blurred = inverted.filter(
            ImageFilter.GaussianBlur(radius=10)
        )

        # Convert images to NumPy arrays for the sketch calculation
        gray_np = np.array(gray).astype(float)
        blurred_np = np.array(blurred).astype(float)

        # Create the pencil sketch effect (dodge blend)
        sketch_np = gray_np * 255 / (255 - blurred_np + 1)

        # Keep pixel values in the valid range
        sketch_np = np.clip(sketch_np, 0, 255)

        # Convert the NumPy array back to a PIL image
        sketch = Image.fromarray(sketch_np.astype(np.uint8))

        show_download(
            sketch,
            "sketch.png"
        )


# ==================================================
# PASSPORT SIZE PHOTO FRAME
# ==================================================

elif option == "Passport Size Photo Frame":

    st.header("🪪 Passport Size Photo Frame")

    st.write(
        "Create a sheet containing multiple passport-size photos."
    )

    file = st.file_uploader(
        "Upload Photo",
        type=["jpg", "jpeg", "png"],
        key="passport"
    )

    copies = st.number_input(
        "Number of Copies",
        min_value=1,
        max_value=30,
        value=8
    )

    if file:

        image = load_image(file)

        photo_width = 300
        photo_height = 350

        passport = resize_crop(
            image,
            (photo_width, photo_height)
        )

        cols = 3

        rows = (int(copies) + cols - 1) // cols

        margin = 30
        gap = 20

        sheet_width = (
            margin * 2
            + cols * photo_width
            + (cols - 1) * gap
        )

        sheet_height = (
            margin * 2
            + rows * photo_height
            + (rows - 1) * gap
        )

        sheet = Image.new(
            "RGB",
            (sheet_width, sheet_height),
            "white"
        )

        draw = ImageDraw.Draw(sheet)

        for i in range(int(copies)):

            row = i // cols
            col = i % cols

            x = margin + col * (
                photo_width + gap
            )

            y = margin + row * (
                photo_height + gap
            )

            sheet.paste(
                passport,
                (x, y)
            )

            draw.rectangle(
                [
                    x,
                    y,
                    x + photo_width,
                    y + photo_height
                ],
                outline="black",
                width=2
            )

        show_download(
            sheet,
            "passport_photo_sheet.png"
        )


# ==================================================
# STAMP SIZE PHOTO
# ==================================================

elif option == "Stamp Size Photo":

    st.header("📏 Stamp Size Photo")

    file = st.file_uploader(
        "Upload Image",
        type=["jpg", "jpeg", "png"],
        key="stamp"
    )

    if file:

        image = load_image(file)

        col1, col2 = st.columns(2)

        with col1:

            width = st.number_input(
                "Width in Pixels",
                min_value=50,
                max_value=2000,
                value=150
            )

        with col2:

            height = st.number_input(
                "Height in Pixels",
                min_value=50,
                max_value=2000,
                value=200
            )

        resized = image.resize(
            (int(width), int(height))
        )

        show_download(
            resized,
            "stamp_size.png"
        )


# ==================================================
# IMAGE SIMILARITY
# ==================================================

elif option == "Image Similarity":

    st.header("🔍 Image Similarity")

    st.write(
        "Upload two images to compare their similarity."
    )

    col1, col2 = st.columns(2)

    with col1:

        file1 = st.file_uploader(
            "Upload First Image",
            type=["jpg", "jpeg", "png"],
            key="similarity1"
        )

    with col2:

        file2 = st.file_uploader(
            "Upload Second Image",
            type=["jpg", "jpeg", "png"],
            key="similarity2"
        )

    if file1 and file2:

        img1 = load_image(file1).resize(
            (256, 256)
        )

        img2 = load_image(file2).resize(
            (256, 256)
        )

        img1_gray = np.array(
            ImageOps.grayscale(img1)
        )

        img2_gray = np.array(
            ImageOps.grayscale(img2)
        )

        try:

            from skimage.metrics import structural_similarity

            score = structural_similarity(
                img1_gray,
                img2_gray,
                data_range=255
            )

            st.metric(
                "Image Similarity",
                f"{score * 100:.2f}%"
            )

            col1, col2 = st.columns(2)

            with col1:
                st.image(
                    img1,
                    caption="Image 1",
                    use_container_width=True
                )

            with col2:
                st.image(
                    img2,
                    caption="Image 2",
                    use_container_width=True
                )

        except ImportError:

            st.error(
                "Install scikit-image to calculate similarity."
            )


# ==================================================
# ADD DATE AND TEXT
# ==================================================

elif option == "Add Date and Text":

    st.header("🔤 Add Date and Text")

    file = st.file_uploader(
        "Upload Image",
        type=["jpg", "jpeg", "png"],
        key="text"
    )

    text = st.text_input(
        "Enter Text",
        placeholder="Happy Birthday"
    )

    date = st.date_input(
        "Select Date",
        value=datetime.today().date()
    )

    if file:

        image = load_image(file)

        draw = ImageDraw.Draw(image)

        font = get_font(40)

        overlay_text = f"{text}\n{date}"

        draw.text(
            (30, 30),
            overlay_text,
            fill="white",
            font=font,
            stroke_width=2,
            stroke_fill="black"
        )

        show_download(
            image,
            "image_with_text.png"
        )


# ==================================================
# GEO-TAG IMAGE
# ==================================================

elif option == "Geo-Tag Image":

    st.header("📍 Geo-Tag Image")

    st.write(
        "Add location name, latitude, longitude, and date/time."
    )

    file = st.file_uploader(
        "Upload JPG or PNG Image",
        type=["jpg", "jpeg", "png"],
        key="geotag"
    )

    if file:

        image = load_image(file)

        st.image(
            image,
            caption="Original Image",
            use_container_width=True
        )

        location = st.text_input(
            "Location Name",
            placeholder="Example: Mysore Palace"
        )

        latitude = st.number_input(
            "Latitude",
            min_value=-90.0,
            max_value=90.0,
            value=12.2958
        )

        longitude = st.number_input(
            "Longitude",
            min_value=-180.0,
            max_value=180.0,
            value=76.6394
        )

        date_time = st.text_input(
            "Date and Time",
            value=datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

        visible_label = st.checkbox(
            "Display location details on image",
            value=True
        )

        if st.button("📍 Add Geo-Tag"):

            result = image.copy()

            if visible_label:

                draw = ImageDraw.Draw(result)

                label = (
                    f"Location: {location}\n"
                    f"Latitude: {latitude}\n"
                    f"Longitude: {longitude}\n"
                    f"Date: {date_time}"
                )

                draw.rectangle(
                    [
                        (10, 10),
                        (result.width - 10, 120)
                    ],
                    fill="black"
                )

                draw.text(
                    (20, 20),
                    label,
                    fill="white"
                )

            output = io.BytesIO()

            extension = file.name.lower().split(".")[-1]

            if extension in ["jpg", "jpeg"]:

                gps_ifd = {
                    piexif.GPSIFD.GPSLatitudeRef:
                        "N" if latitude >= 0 else "S",

                    piexif.GPSIFD.GPSLatitude:
                        to_dms(latitude),

                    piexif.GPSIFD.GPSLongitudeRef:
                        "E" if longitude >= 0 else "W",

                    piexif.GPSIFD.GPSLongitude:
                        to_dms(longitude)
                }

                exif_dict = {
                    "GPS": gps_ifd
                }

                exif_bytes = piexif.dump(
                    exif_dict
                )

                result.save(
                    output,
                    format="JPEG",
                    quality=95,
                    exif=exif_bytes
                )

                filename = "geotagged_image.jpg"

            else:

                png_info = PngImagePlugin.PngInfo()

                png_info.add_text(
                    "Location",
                    location
                )

                png_info.add_text(
                    "Latitude",
                    str(latitude)
                )

                png_info.add_text(
                    "Longitude",
                    str(longitude)
                )

                png_info.add_text(
                    "DateTime",
                    date_time
                )

                result.save(
                    output,
                    format="PNG",
                    pnginfo=png_info
                )

                filename = "geotagged_image.png"

            output.seek(0)

            st.success(
                "Geo-Tag added successfully!"
            )

            st.image(
                result,
                caption="Geo-Tagged Image",
                use_container_width=True
            )

            st.download_button(
                label="⬇️ Download Geo-Tagged Image",
                data=output.getvalue(),
                file_name=filename,
                mime=(
                    "image/jpeg"
                    if filename.endswith(".jpg")
                    else "image/png"
                )
            )


# ==================================================
# MULTIPLE IMAGES WITH TEXT
# ==================================================

elif option == "Multiple Images with Text":

    st.header("🧩 Multiple Images with Text")

    files = st.file_uploader(
        "Upload Multiple Images",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    title = st.text_input(
        "Enter Title",
        placeholder="My Memories"
    )

    if files:

        images = [
            load_image(file).resize(
                (300, 300)
            )
            for file in files
        ]

        columns = 3

        rows = (
            len(images) + columns - 1
        ) // columns

        canvas = Image.new(
            "RGB",
            (
                columns * 320,
                rows * 350 + 100
            ),
            "white"
        )

        draw = ImageDraw.Draw(canvas)

        draw.text(
            (20, 20),
            title,
            fill="black",
            font=get_font(40)
        )

        for i, image in enumerate(images):

            x = (
                i % columns
            ) * 320 + 10

            y = (
                i // columns
            ) * 350 + 100

            canvas.paste(
                image,
                (x, y)
            )

            draw.text(
                (x, y + 305),
                f"Image {i + 1}",
                fill="black"
            )

        show_download(
            canvas,
            "multiple_images.png"
        )


# ==================================================
# THUMBNAIL GENERATOR
# ==================================================

elif option == "Thumbnail Generator":

    st.header("🖼️ Thumbnail Generator")

    file = st.file_uploader(
        "Upload Image",
        type=["jpg", "jpeg", "png"],
        key="thumbnail"
    )

    if file:

        image = load_image(file)

        col1, col2 = st.columns(2)

        with col1:

            width = st.number_input(
                "Thumbnail Width",
                min_value=50,
                max_value=2000,
                value=200
            )

        with col2:

            height = st.number_input(
                "Thumbnail Height",
                min_value=50,
                max_value=2000,
                value=200
            )

        thumbnail = image.copy()

        thumbnail.thumbnail(
            (int(width), int(height))
        )

        show_download(
            thumbnail,
            "thumbnail.png"
        )


# ==================================================
# WALLPAPER WITH TITLE
# ==================================================

elif option == "Wallpaper with Title":

    st.header("🌄 Wallpaper with Title")

    file = st.file_uploader(
        "Upload Image",
        type=["jpg", "jpeg", "png"],
        key="wallpaper"
    )

    title = st.text_input(
        "Enter Wallpaper Title",
        placeholder="Nature Vibes"
    )

    if file:

        image = load_image(file)

        wallpaper = ImageOps.fit(
            image,
            (1920, 1080)
        )

        draw = ImageDraw.Draw(wallpaper)

        font = get_font(70)

        draw.text(
            (50, 50),
            title,
            fill="white",
            font=font,
            stroke_width=3,
            stroke_fill="black"
        )

        show_download(
            wallpaper,
            "wallpaper.png"
        )
