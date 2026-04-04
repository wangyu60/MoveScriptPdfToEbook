"""
Interactive crop region selector for PDF pages using tkinter.
Lightweight and fast - no matplotlib overhead.
Features:
- Visible solid green rectangle while dragging
- Orange resize handles at corners and edges
- Real-time preview while dragging
"""

import fitz
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk
import json
import os

class CropSelector:
    """Interactive rectangle selector using tkinter Canvas."""
    
    def __init__(self, pdf_path, page_num, dpi=150):
        self.pdf_path = pdf_path
        self.page_num = page_num
        self.dpi = dpi
        self.selected_rect = None
        self.img = None
        self.photo = None
        self.canvas = None
        self.rect_id = None
        self.handle_ids = []
        self.start_x = None
        self.start_y = None
        self.current_rect = None  # (x0, y0, x1, y1)
        self.active_handle = None
        self.start_rect = None
        
    def render_page(self):
        """Render PDF page to image for display."""
        doc = None
        try:
            doc = fitz.open(self.pdf_path)
            
            if self.page_num >= len(doc):
                print(f"Error: Page {self.page_num} does not exist. PDF has {len(doc)} pages (0-{len(doc)-1}).")
                return None, None
            
            page = doc[self.page_num]
            if page is None:
                print(f"Error: Page {self.page_num} is None (possibly corrupted or blank).")
                return None, None
            
            print(f"Rendering page {self.page_num + 1} at {self.dpi} DPI (preview)...")
            pix = page.get_pixmap(dpi=self.dpi)
            
            if pix.alpha:
                img = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples).convert("RGB")
            else:
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            print(f"Page rendered successfully: {pix.width}x{pix.height} pixels")
            return img, page.rect
            
        except Exception as e:
            print(f"Error rendering page {self.page_num}: {e}")
            return None, None
        finally:
            if doc is not None:
                doc.close()
    
    def _create_handles(self, x0, y0, x1, y1):
        """Create resize handles at rectangle edges and corners."""
        # Remove existing handles
        for h in self.handle_ids:
            self.canvas.delete(h)
        self.handle_ids = []
        
        # Handle positions: corners and midpoints (radius=5)
        handle_positions = [
            (x0, y0),      # top-left
            ((x0+x1)/2, y0),  # top-center
            (x1, y0),      # top-right
            (x0, (y0+y1)/2),  # middle-left
            (x1, (y0+y1)/2),  # middle-right
            (x0, y1),      # bottom-left
            ((x0+x1)/2, y1),  # bottom-center
            (x1, y1),      # bottom-right
        ]
        
        for px, py in handle_positions:
            r = 5
            handle = self.canvas.create_oval(
                px - r, py - r, px + r, py + r,
                fill='#ff6600', outline='#cc5500', width=1
            )
            self.handle_ids.append(handle)
    
    def _get_nearest_handle(self, x, y, threshold=15):
        """Find the nearest handle within threshold distance."""
        if not self.handle_ids:
            return None
        
        min_dist = threshold
        nearest_idx = None
        
        for idx, handle_id in enumerate(self.handle_ids):
            coords = self.canvas.coords(handle_id)
            hx = (coords[0] + coords[2]) / 2
            hy = (coords[1] + coords[3]) / 2
            dist = ((x - hx)**2 + (y - hy)**2)**0.5
            if dist < min_dist:
                min_dist = dist
                nearest_idx = idx
        
        return nearest_idx
    
    def _update_rectangle(self, x0, y0, x1, y1):
        """Update rectangle position and handles."""
        if self.rect_id is None:
            return
        
        # Normalize coordinates
        rect_x0 = min(x0, x1)
        rect_y0 = min(y0, y1)
        rect_x1 = max(x0, x1)
        rect_y1 = max(y0, y1)
        
        # Update rectangle
        self.canvas.coords(self.rect_id, rect_x0, rect_y0, rect_x1, rect_y1)
        
        # Update handles
        self._create_handles(rect_x0, rect_y0, rect_x1, rect_y1)
        
        # Store current rect
        self.current_rect = (rect_x0, rect_y0, rect_x1, rect_y1)
        self.canvas.update_idletasks()
    
    def on_press(self, event):
        """Handle mouse press event."""
        self.start_x = event.x
        self.start_y = event.y
        
        # Check if clicking on a handle
        handle_idx = self._get_nearest_handle(event.x, event.y)
        
        if handle_idx is not None:
            # Dragging a handle to resize
            self.active_handle = handle_idx
            self.start_rect = self.current_rect
        else:
            # Start new rectangle
            self.active_handle = None
            self.start_rect = None
            
            # Remove previous rectangle if exists
            if self.rect_id:
                self.canvas.delete(self.rect_id)
                for h in self.handle_ids:
                    self.canvas.delete(h)
                self.handle_ids = []
            
            # Create new rectangle (initially zero size)
            self.rect_id = self.canvas.create_rectangle(
                event.x, event.y, event.x, event.y,
                outline='#00ff00', width=1
            )
    
    def on_motion(self, event):
        """Handle mouse motion event - update rectangle in real-time."""
        if self.start_x is None:
            return
        
        x, y = event.x, event.y
        
        if self.active_handle is not None and self.start_rect:
            # Resizing via handle
            x0, y0, x1, y1 = self.start_rect
            
            if self.active_handle == 0:  # top-left
                x0, y0 = x, y
            elif self.active_handle == 1:  # top-center
                y0 = y
            elif self.active_handle == 2:  # top-right
                x1, y0 = x, y
            elif self.active_handle == 3:  # middle-left
                x0 = x
            elif self.active_handle == 4:  # middle-right
                x1 = x
            elif self.active_handle == 5:  # bottom-left
                x0, y1 = x, y
            elif self.active_handle == 6:  # bottom-center
                y1 = y
            elif self.active_handle == 7:  # bottom-right
                x1, y1 = x, y
            
            self._update_rectangle(x0, y0, x1, y1)
            
        elif self.active_handle is None:
            # Drawing new rectangle - update in real-time
            self._update_rectangle(self.start_x, self.start_y, x, y)
    
    def on_release(self, event):
        """Handle mouse release event."""
        if self.active_handle is None and self.start_rect is None:
            # Finished drawing new rectangle
            self.selected_rect = self.current_rect
            if self.current_rect:
                x0, y0, x1, y1 = self.current_rect
                print(f"\nSelected region: ({x0:.1f}, {y0:.1f}) to ({x1:.1f}, {y1:.1f})")
                print("Drag orange handles to fine-tune | Press Enter to confirm, R to reselect, Q to quit")
        
        self.active_handle = None
        self.start_rect = None
        self.start_x = None
        self.start_y = None
    
    def on_key(self, event):
        """Handle key press events."""
        if event.keysym == 'Return':
            if self.selected_rect:
                print("Selection confirmed!")
                self.root.quit()
            else:
                print("Please select a region first (click and drag)")
        elif event.keysym.lower() == 'r':
            # Reset selection
            if self.rect_id:
                self.canvas.delete(self.rect_id)
                for h in self.handle_ids:
                    self.canvas.delete(h)
                self.rect_id = None
                self.handle_ids = []
                self.selected_rect = None
                self.current_rect = None
                print("Selection reset. Draw a new rectangle.")
        elif event.keysym.lower() == 'q':
            print("Cancelled.")
            self.selected_rect = None
            self.root.quit()
    
    def select(self):
        """Display the page and let user select crop region."""
        img, page_rect = self.render_page()
        
        if img is None:
            return None
        
        self.img = img
        
        # Create main window
        self.root = tk.Tk()
        self.root.title(f"Page {self.page_num + 1} - Select OCR Region")
        
        # Get screen dimensions
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        
        # Calculate max available size (leave room for UI)
        max_w = screen_w - 100
        max_h = screen_h - 150
        
        # Scale image if needed to fit screen
        scale = 1.0
        if img.width > max_w or img.height > max_h:
            scale = min(max_w / img.width, max_h / img.height)
            new_w = int(img.width * scale)
            new_h = int(img.height * scale)
            self.img = img.resize((new_w, new_h), Image.LANCZOS)
            print(f"Image scaled to {scale:.1%} ({new_w}x{new_h}) to fit screen")
        
        self.scale_factor = scale
        
        # Create canvas (no scrollbars needed - image fits)
        self.canvas = tk.Canvas(self.root, bg='white', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Convert image to PhotoImage
        self.photo = ImageTk.PhotoImage(self.img)
        
        # Set canvas size to image size
        self.canvas.configure(width=self.img.width, height=self.img.height)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        
        # Bind events
        self.canvas.bind('<ButtonPress-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_motion)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.root.bind('<KeyPress>', self.on_key)
        
        # Add instruction label
        instr = ttk.Label(self.root, 
            text="Click & drag to select | Drag handles to adjust | Enter=Confirm, R=Reset, Q=Quit",
            font=('Arial', 9))
        instr.pack(side=tk.BOTTOM, pady=5)
        
        # Maximize window and center
        self.root.attributes('-topmost', True)
        self.root.update_idletasks()
        win_w = self.img.width + 50
        win_h = self.img.height + 80
        x = (screen_w - win_w) // 2
        y = (screen_h - win_h) // 2
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")
        
        # Run main loop
        self.root.mainloop()
        self.root.destroy()
        
        # Convert coordinates from image space to PDF points
        if self.selected_rect:
            # img is the SCALED image displayed on screen
            # self.scale_factor = scaled_size / original_size
            # So: original_size = scaled_size / scale_factor
            # The original image was rendered at self.dpi DPI
            # PDF uses 72 DPI, so: pdf_coord = image_coord * (72 / dpi)
            
            # Combined: pdf_coord = scaled_coord / scale_factor * (72 / self.dpi)
            scale_to_pdf = 72.0 / (self.dpi * self.scale_factor)
            
            x0, y0, x1, y1 = self.selected_rect
            pdf_rect = fitz.Rect(
                x0 * scale_to_pdf,
                y0 * scale_to_pdf,
                x1 * scale_to_pdf,
                y1 * scale_to_pdf
            )
            print(f"Debug: scale_factor={self.scale_factor}, dpi={self.dpi}, scale_to_pdf={scale_to_pdf}")
            print(f"Debug: Screen coords ({x0:.1f}, {y0:.1f}) to ({x1:.1f}, {y1:.1f}) -> PDF {pdf_rect}")
            return pdf_rect
        
        return None


def select_crop_region(pdf_path, page_num, dpi=150):
    """
    Interactive function to select crop region on a PDF page.
    
    Args:
        pdf_path: Path to the PDF file
        page_num: Page number (0-indexed)
        dpi: DPI for rendering the preview image
        
    Returns:
        fitz.Rect object with selected coordinates, or None if cancelled
    """
    selector = CropSelector(pdf_path, page_num, dpi)
    return selector.select()


def save_crop_selection(rect, pdf_path, page_num, save_path=None):
    """
    Save crop selection to a JSON file for later use.
    """
    if save_path is None:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        save_path = f"Intermediates/{base_name}_page{page_num}_crop.json"
    
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    selection_data = {
        "pdf_path": pdf_path,
        "page_num": page_num,
        "crop_rect": {
            "x0": rect.x0,
            "y0": rect.y0,
            "x1": rect.x1,
            "y1": rect.y1
        }
    }
    
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(selection_data, f, indent=2)
    
    print(f"Crop selection saved to: {save_path}")
    return save_path


def load_crop_selection(load_path):
    """
    Load crop selection from a JSON file.
    """
    if not os.path.exists(load_path):
        return None
    
    with open(load_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    rect_data = data.get("crop_rect", {})
    return fitz.Rect(
        rect_data.get("x0", 0),
        rect_data.get("y0", 0),
        rect_data.get("x1", 0),
        rect_data.get("y1", 0)
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python select_crop_region.py <pdf_file> [page_num] [output_json]")
        print("  page_num is 0-indexed (default: 0)")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    
    # Quick PDF info
    doc = fitz.open(pdf_file)
    print(f"PDF: {pdf_file}")
    print(f"Total pages: {len(doc)} (page numbers: 0 to {len(doc)-1})")
    doc.close()
    
    page_num = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    output_json = sys.argv[3] if len(sys.argv) > 3 else None
    
    if page_num >= len(fitz.open(pdf_file)):
        print(f"Error: Page {page_num} does not exist. Please use a page number between 0 and {len(fitz.open(pdf_file))-1}")
        sys.exit(1)
    
    print(f"\nSelecting crop region for page {page_num + 1} (index {page_num})")
    rect = select_crop_region(pdf_file, page_num)
    
    if rect:
        print(f"Selected: {rect}")
        if output_json:
            save_crop_selection(rect, pdf_file, page_num, output_json)
    else:
        print("No selection made.")
