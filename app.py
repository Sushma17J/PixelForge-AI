def draggable_text_editor(image, initial_text, key="draggable_text_component"):
    """
    Interactive HTML5 canvas component:
    - Pure drag & drop text positioning using mouse / touch coordinates.
    - Uses standard ctx.rect fallback (avoids roundRect crash).
    - Robust multiline string handling via native JSON parsing.
    - Direct export and client-side download as high-res PNG.
    """
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_b64 = base64.b64encode(buffer.getvalue()).decode("ascii")

    base_dim = max(image.width, image.height)
    default_font_size = max(24, int(base_dim * 0.05))
    min_font_size = max(10, int(base_dim * 0.01))
    max_font_size = max(120, int(base_dim * 0.25))

    # Split lines in Python to avoid JS regex/newline escape bugs
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

            // Render original image
            ctx.drawImage(img, 0, 0);

            // Configure text styling
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

            // Optional background box (compatible cross-browser)
            if (showBg) {{
                ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
                ctx.fillRect(x - padX, y - padY, maxLineWidth + (padX * 2), totalHeight + (padY * 2));
            }}

            // Draw bounding selection stroke if unlocked
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

            // Render text lines with high-contrast shadow
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

        // Controls
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
