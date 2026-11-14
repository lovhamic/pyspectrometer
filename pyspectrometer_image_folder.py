#!/usr/bin/python3
'''
PySpectrometer - Image Folder Edition
Based on: Python Picam/Webcam Spectrometer, Les Wright May 2021
          V3.1 modifications, Florian Ragwitz

*** MODIFIED VERSION ***
This version replaces the live camera feed with static spectrum images
loaded from a folder or single file on disk. This lets you calibrate and analyze
previously captured spectrum photos when you don't have a spectrometer
unit connected.

Usage:
    python pyspectrometer_image_folder.py --folder /path/to/images
    python pyspectrometer_image_folder.py --folder /path/to/image.png
    python pyspectrometer_image_folder.py --folder /path/to/images -c 72:400,304:530

Controls:
    Open Folder   - choose a folder of images
    Open Image    - choose a single image file
    < Prev / Next >  - step through images in the folder
    Click graph   - set calibration points
    Calibrate     - lock in wavelength calibration from two points/values
    Clear         - reset calibration points to click new ones
    Peak Width / Threshold / Filter - peak-detection controls
    Peak Hold     - accumulate max intensity across images
    Snapshot      - save current graph as .jpg and data as .csv
'''

import os
import csv
import glob
import re
import tkinter
import tkinter.font as tkFont
from tkinter import filedialog, messagebox
import cv2
import PIL.Image
import PIL.ImageTk
import PIL.ImageOps
import time
import numpy as np
from scipy.signal import savgol_filter
import peakutils
import argparse

IMAGE_EXTENSIONS = (
    '.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff',
    '.webp', '.jfif', '.ppm', '.pgm', '.pbm', '.gif'
)


class App:
    DEFAULT_CALIBRATION = ((72, 405), (304, 532))

    def __init__(self, args, window, window_title):
        self.window = window

        self.window.geometry("660x615")
        self.window.resizable(width=False, height=False)
        self.window.title(window_title)
        self.def_font = tkinter.font.nametofont("TkDefaultFont")
        self.def_font.config(size=9)

        initial_cal = args.calibration or App.DEFAULT_CALIBRATION
        self.src = ImageSpectrometer(initial_cal)

        # Canvas image IDs for efficient item reuse
        self.img_id0 = None
        self.img_id1 = None
        self.photo = None
        self.photo2 = None

        # Calibration point tracking
        self.point1 = initial_cal[0][0]
        self.point2 = initial_cal[1][0]

        def select_points(event):
            if self.marker1.cget("text") == "Click graph to add point!":
                self.marker1.configure(text=str(event.x))
                self.point1 = int(event.x)
            elif self.marker2.cget("text") == "Click graph to add point!":
                self.marker2.configure(text=str(event.x))
                self.point2 = int(event.x)

        def clear_points():
            self.marker1.configure(text="Click graph to add point!")
            self.marker2.configure(text="Click graph to add point!")
            self.txt1.delete(0, tkinter.END)
            self.txt2.delete(0, tkinter.END)
            self.point1 = 'x'
            self.point2 = 'x'
            self.calbutton.configure(text="Calibrate", fg="yellow", bg="red", activebackground='red')

        def peakwidth(event):
            setattr(self.src, 'mindist', event)

        def peakthresh(event):
            setattr(self.src, 'thresh', event)

        def savfilter(event):
            setattr(self.src, 'savpoly', event)

        def snapshot():
            ret, graphdata = self.src.get_graph()
            if ret:
                now = time.strftime("%d-%m-%Y-%H-%M-%S")
                curr_file = self.src.current_filename()
                base = os.path.splitext(curr_file)[0] if curr_file else "spectrum"
                outname = f"{base}-{now}"

                # Save JPG graph in RGB -> BGR format
                cv2.imwrite(outname + ".jpg", cv2.cvtColor(graphdata[0], cv2.COLOR_RGB2BGR))

                # Save CSV data with proper newline handling for all platforms
                with open(outname + ".csv", 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Wavelength', 'Intensity'])
                    for wl, intensity in zip(graphdata[1], graphdata[2]):
                        wl_formatted = f"{wl:.2f}" if isinstance(wl, float) else str(wl)
                        writer.writerow([wl_formatted, intensity])

                abs_jpg = os.path.abspath(outname + ".jpg")
                abs_csv = os.path.abspath(outname + ".csv")
                messagebox.showinfo("Saved", f"Saved snapshot:\n{abs_jpg}\n{abs_csv}")
            else:
                messagebox.showwarning("No image loaded", "No spectrum image loaded to capture snapshot.")

        def peakhold():
            if self.peakholdbtn.cget("bg") == 'yellow':
                self.peakholdbtn.configure(fg="yellow", bg="red", activebackground='red', activeforeground="yellow")
                setattr(self.src, 'holdpeaks', True)
                self.filt.configure(state="disabled")
            else:
                self.peakholdbtn.configure(fg="black", bg="yellow", activebackground='yellow', activeforeground="black")
                setattr(self.src, 'holdpeaks', False)
                self.filt.configure(state="active")

        def prev_image():
            self.src.prev_image()
            self.update_filename_label()

        def next_image():
            self.src.next_image()
            self.update_filename_label()

        # ---------------- Frames ----------------
        self.top_frame = tkinter.Frame(window, width=640, height=240)
        self.top_frame.grid(row=0, column=0, padx=10, pady=5)
        self.mid_frame = tkinter.Frame(window, width=640, height=30)
        self.mid_frame.grid(row=1, column=0, padx=10, pady=0)
        self.bottom_frame = tkinter.Frame(window, width=640, height=255)
        self.bottom_frame.grid(row=2, column=0, padx=10, pady=5)

        # Control frame (calibration UI)
        self.control_frame = tkinter.Frame(self.top_frame, width=324)
        self.control_frame.grid(row=0, column=0, padx=0, pady=0)

        # Folder & file picker buttons
        self.btn_subframe = tkinter.Frame(self.control_frame)
        self.btn_subframe.grid(row=0, column=0, columnspan=3, pady=(0, 10), sticky='we')
        self.folderbtn = tkinter.Button(self.btn_subframe, text="Open Folder...", width=14, command=self.open_folder)
        self.folderbtn.pack(side=tkinter.LEFT, padx=(0, 4), expand=True, fill=tkinter.X)
        self.filebtn = tkinter.Button(self.btn_subframe, text="Open Image...", width=14, command=self.open_file)
        self.filebtn.pack(side=tkinter.LEFT, padx=(4, 0), expand=True, fill=tkinter.X)

        self.lbl1 = tkinter.Label(self.control_frame, text="Wavelength 1:")
        self.lbl1.grid(row=1, column=0)
        self.lbl2 = tkinter.Label(self.control_frame, text="Wavelength 2:")
        self.lbl2.grid(row=2, column=0)
        self.txt1 = tkinter.Entry(self.control_frame, width=6)
        self.txt1.grid(row=1, column=1, sticky='w')
        self.txt2 = tkinter.Entry(self.control_frame, width=6)
        self.txt2.grid(row=2, column=1, sticky='w')
        self.marker1 = tkinter.Label(self.control_frame, text=str(initial_cal[0][0]), width=19, borderwidth=2, relief="sunken")
        self.marker1.grid(row=1, column=2, padx=0, pady=5)
        self.marker2 = tkinter.Label(self.control_frame, text=str(initial_cal[1][0]), width=19, borderwidth=2, relief="sunken")
        self.marker2.grid(row=2, column=2, padx=0, pady=5)
        self.txt1.insert(0, str(initial_cal[0][1]))
        self.txt2.insert(0, str(initial_cal[1][1]))

        self.calbutton = tkinter.Button(self.control_frame, text="Calibrate", width=8, fg="yellow", bg="red", activebackground='red', command=self.calibrate)
        self.calbutton.grid(row=4, column=0, columnspan=1, pady=8)
        self.clrbutton = tkinter.Button(self.control_frame, text="Clear", command=clear_points)
        self.clrbutton.grid(row=4, column=2, pady=8)

        # Loaded-image preview canvas
        self.canvas0 = tkinter.Canvas(self.top_frame, width=317, height=238, borderwidth=2, relief="sunken")
        self.canvas0.grid(row=0, column=2, padx=(10, 0))

        # ---------------- Image navigation row ----------------
        self.prevbtn = tkinter.Button(self.mid_frame, text="< Prev", width=8, command=prev_image)
        self.prevbtn.grid(row=0, column=0, padx=4)
        self.filename_lbl = tkinter.Label(self.mid_frame, text="No folder loaded", width=60, anchor="center")
        self.filename_lbl.grid(row=0, column=1, padx=4)
        self.nextbtn = tkinter.Button(self.mid_frame, text="Next >", width=8, command=next_image)
        self.nextbtn.grid(row=0, column=2, padx=4)

        # ---------------- Graph canvas ----------------
        self.canvas1 = tkinter.Canvas(self.bottom_frame, width=634, height=252, borderwidth=2, relief="sunken", cursor="tcross")
        self.canvas1.bind("<Button-1>", select_points)
        self.canvas1.grid(row=0, column=0, padx=0, pady=0, columnspan=8)

        self.lbpeak = tkinter.Label(self.bottom_frame, text="Peak Width:")
        self.lbpeak.grid(row=1, column=0, pady=20, sticky="nw")
        self.peakwidth = tkinter.Scale(self.bottom_frame, from_=0, to=100, orient="horizontal", command=peakwidth)
        self.peakwidth.grid(row=1, column=1, padx=0, pady=2, sticky="n")
        self.peakwidth.set(50)

        self.lbthresh = tkinter.Label(self.bottom_frame, text="Threshold:")
        self.lbthresh.grid(row=1, column=2, pady=20, sticky="n")
        self.thresh = tkinter.Scale(self.bottom_frame, from_=0, to=100, orient="horizontal", command=peakthresh)
        self.thresh.grid(row=1, column=3, padx=0, pady=2, sticky="n")
        self.thresh.set(20)

        self.lbfilt = tkinter.Label(self.bottom_frame, text="Filter:")
        self.lbfilt.grid(row=1, column=4, pady=20, sticky="n")
        self.filt = tkinter.Scale(self.bottom_frame, from_=0, to=16, orient="horizontal", command=savfilter)
        self.filt.grid(row=1, column=5, padx=0, pady=2, sticky="n")
        self.filt.set(7)

        self.peakholdbtn = tkinter.Button(self.bottom_frame, text="Peak Hold", width=6, fg="black", bg="yellow", activebackground='yellow', command=peakhold)
        self.peakholdbtn.grid(row=1, column=6, padx=0, pady=0)

        self.snapshotbtn = tkinter.Button(self.bottom_frame, text="Snapshot", width=6, command=snapshot)
        self.snapshotbtn.grid(row=1, column=7, padx=0, pady=0)

        # Load initial folder/file if provided, else prompt
        start_path = args.folder
        if start_path and (os.path.isdir(start_path) or os.path.isfile(start_path)):
            self.src.load_folder(start_path)
        else:
            self.window.after(100, self.open_folder)

        self.update_filename_label()
        self.calibrate()

        self.delay = 100
        self.update()
        self.window.mainloop()

    def open_folder(self):
        folder = filedialog.askdirectory(title="Select folder containing spectrum images")
        if folder:
            ok = self.src.load_folder(folder)
            if not ok:
                messagebox.showwarning("No images found", "No supported image files found in that folder.")
            self.update_filename_label()

    def open_file(self):
        filetypes = [
            ("All supported images", "*.jpg;*.jpeg;*.png;*.bmp;*.tif;*.tiff;*.webp;*.jfif;*.ppm;*.pgm;*.gif"),
            ("JPEG images", "*.jpg;*.jpeg;*.jfif"),
            ("PNG images", "*.png"),
            ("WebP images", "*.webp"),
            ("All files", "*.*")
        ]
        filepath = filedialog.askopenfilename(title="Select spectrum image", filetypes=filetypes)
        if filepath:
            ok = self.src.load_folder(filepath)
            if not ok:
                messagebox.showwarning("Error", "Could not load the selected image file.")
            self.update_filename_label()

    def update_filename_label(self):
        name = self.src.current_filename()
        count = self.src.image_count()
        idx = self.src.current_index() + 1 if count else 0
        if name:
            self.filename_lbl.configure(text=f"[{idx}/{count}]  {name}")
        else:
            self.filename_lbl.configure(text="No folder loaded")

    def calibrate(self):
        try:
            p1 = int(round(float(self.point1)))
            p2 = int(round(float(self.point2)))
        except (ValueError, TypeError):
            messagebox.showwarning("Calibration error", "Please select two points on the graph by clicking on it before calibrating.")
            return

        try:
            wl1 = float(self.txt1.get().strip())
            wl2 = float(self.txt2.get().strip())
            if wl1.is_integer():
                wl1 = int(wl1)
            if wl2.is_integer():
                wl2 = int(wl2)
        except ValueError:
            messagebox.showerror("Calibration error", "Please enter valid numeric wavelengths for both points.")
            return

        if p1 == p2:
            messagebox.showerror("Calibration error", "Calibration points cannot be at the same pixel position.")
            return
        if wl1 == wl2:
            messagebox.showerror("Calibration error", "Calibration wavelengths must be different values.")
            return

        calibration = ((p1, wl1), (p2, wl2))
        self.src.recalibrate(calibration)
        self.calbutton.configure(text="Calibrated", fg="black", bg="yellow", activebackground='yellow')

    def update(self):
        ret, frame = self.src.get_frame()
        ret2, graphdata = self.src.get_graph()
        if ret:
            self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
            if self.img_id0 is None:
                self.img_id0 = self.canvas0.create_image(0, 0, image=self.photo, anchor=tkinter.NW)
            else:
                self.canvas0.itemconfig(self.img_id0, image=self.photo)
        if ret2:
            self.photo2 = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(graphdata[0]))
            if self.img_id1 is None:
                self.img_id1 = self.canvas1.create_image(0, 0, image=self.photo2, anchor=tkinter.NW)
            else:
                self.canvas1.itemconfig(self.img_id1, image=self.photo2)
        self.window.after(self.delay, self.update)


class ImageSpectrometer:
    '''
    Drop-in replacement for MyVideoCapture class.
    Loads static images from disk and performs spectrometer analysis
    on the current loaded image.
    '''

    def __init__(self, calibration):
        self.calibration = calibration

        # Peak-detection & filter settings
        self.mindist = 50
        self.thresh = 20
        self.savpoly = 7
        self.holdpeaks = False

        self.image_paths = []
        self.index = 0
        self.frame = None          # Currently loaded BGR image (full size)
        self.intensity = [0] * 636  # Persists across images when Peak Hold is on

    # ---------- Folder / file handling ----------

    def load_folder(self, target):
        if not target:
            return False

        target = os.path.abspath(target)
        selected_file = None
        if os.path.isfile(target):
            selected_file = target
            folder = os.path.dirname(target)
        elif os.path.isdir(target):
            folder = target
        else:
            return False

        try:
            entries = os.listdir(folder)
        except Exception:
            return False

        valid_exts = set(IMAGE_EXTENSIONS)
        paths = []
        for entry in entries:
            ext = os.path.splitext(entry)[1].lower()
            if ext in valid_exts:
                paths.append(os.path.join(folder, entry))

        # Natural alphanumeric sorting
        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', os.path.basename(s))]

        paths = sorted(paths, key=natural_sort_key)
        if not paths:
            return False

        self.image_paths = paths
        if selected_file and selected_file in paths:
            self.index = paths.index(selected_file)
        else:
            self.index = 0
        self.intensity = [0] * 636
        self._load_current()
        return True

    def _load_current(self):
        if not self.image_paths:
            self.frame = None
            return
        path = self.image_paths[self.index]
        img = None

        # 1. Try decoding binary stream (handles Windows unicode/spaces in path)
        try:
            img_data = np.fromfile(path, dtype=np.uint8)
            img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
        except Exception:
            pass

        # 2. Try PIL with EXIF orientation correction
        if img is None:
            try:
                with PIL.Image.open(path) as pil_img:
                    pil_img = PIL.ImageOps.exif_transpose(pil_img)
                    pil_img = pil_img.convert('RGB')
                    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            except Exception:
                pass

        # 3. Standard OpenCV fallback
        if img is None:
            try:
                img = cv2.imread(path, cv2.IMREAD_COLOR)
            except Exception:
                img = None

        # Format normalization: Ensure 3-channel BGR format
        if img is not None:
            if len(img.shape) == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            elif img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        self.frame = img

    def next_image(self):
        if not self.image_paths:
            return
        self.index = (self.index + 1) % len(self.image_paths)
        self._load_current()

    def prev_image(self):
        if not self.image_paths:
            return
        self.index = (self.index - 1) % len(self.image_paths)
        self._load_current()

    def current_filename(self):
        if not self.image_paths:
            return None
        return os.path.basename(self.image_paths[self.index])

    def current_index(self):
        return self.index

    def image_count(self):
        return len(self.image_paths)

    def recalibrate(self, calibration):
        self.calibration = calibration

    # ---------- Preview frame ----------

    def get_frame(self):
        if self.frame is None:
            return (False, None)
        frame = cv2.resize(self.frame, (320, 240))
        cv2.line(frame, (0, 120), (320, 120), (255, 255, 255), 1)
        return (True, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    # ---------- Wavelength to RGB ----------

    def wavelength_to_rgb(self, nm):
        gamma = 0.8
        max_intensity = 255
        factor = 0
        rgb = {"R": 0, "G": 0, "B": 0}

        if 380 <= nm <= 439:
            rgb["R"] = -(nm - 440) / (440 - 380)
            rgb["G"] = 0.0
            rgb["B"] = 1.0
        elif 440 <= nm <= 489:
            rgb["R"] = 0.0
            rgb["G"] = (nm - 440) / (490 - 440)
            rgb["B"] = 1.0
        elif 490 <= nm <= 509:
            rgb["R"] = 0.0
            rgb["G"] = 1.0
            rgb["B"] = -(nm - 510) / (510 - 490)
        elif 510 <= nm <= 579:
            rgb["R"] = (nm - 510) / (580 - 510)
            rgb["G"] = 1.0
            rgb["B"] = 0.0
        elif 580 <= nm <= 644:
            rgb["R"] = 1.0
            rgb["G"] = -(nm - 645) / (645 - 580)
            rgb["B"] = 0.0
        elif 645 <= nm <= 780:
            rgb["R"] = 1.0
            rgb["G"] = 0.0
            rgb["B"] = 0.0

        if 380 <= nm <= 419:
            factor = 0.3 + 0.7 * (nm - 380) / (420 - 380)
        elif 420 <= nm <= 700:
            factor = 1.0
        elif 701 <= nm <= 780:
            factor = 0.3 + 0.7 * (780 - nm) / (780 - 700)

        for k in rgb:
            if rgb[k] > 0:
                rgb[k] = int(max_intensity * ((rgb[k] * factor) ** gamma))
            else:
                rgb[k] = 0

        return (rgb["R"], rgb["G"], rgb["B"])

    # ---------- Core analysis ----------

    def get_graph(self):
        if self.frame is None:
            return (False, None)

        piwidth = 636
        bwimage = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
        rows, cols = bwimage.shape

        # Ensure image width matches spectrometer analysis width (640 px = 636 px graph + 4 px margin)
        if cols != piwidth + 4:
            scale = (piwidth + 4) / cols
            new_height = max(1, int(rows * scale))
            bwimage = cv2.resize(bwimage, (piwidth + 4, new_height))
            rows, cols = bwimage.shape

        graph = np.zeros([255, piwidth, 3], dtype=np.uint8)
        graph.fill(255)

        pxrange = abs(self.calibration[0][0] - self.calibration[1][0])
        nmrange = abs(self.calibration[0][1] - self.calibration[1][1])
        if pxrange == 0 or nmrange == 0:
            return (False, None)
        pxpernm = pxrange / nmrange
        nmperpx = nmrange / pxrange
        zero = self.calibration[0][1] - (self.calibration[0][0] / pxpernm)
        scalezero = zero
        prevposition = 0
        textoffset = 12
        font = cv2.FONT_HERSHEY_SIMPLEX

        for i in range(piwidth):
            position = round(zero)
            if position != prevposition:
                if position % 10 == 0:
                    cv2.line(graph, (i, 15), (i, 255), (200, 200, 200), 1)
                if position % 50 == 0:
                    cv2.line(graph, (i, 15), (i, 255), (0, 0, 0), 1)
                    cv2.putText(graph, str(position) + 'nm', (i - textoffset, 12), font, 0.4, (0, 0, 0), 1, cv2.LINE_AA)
            zero += nmperpx
            prevposition = position

        for i in range(255):
            if i != 0 and i % 51 == 0:
                cv2.line(graph, (0, i), (piwidth, i), (100, 100, 100), 1)

        halfway = int(rows / 2)
        for i in range(cols - 4):
            data = int(bwimage[halfway, i])
            if self.holdpeaks:
                if data > self.intensity[i]:
                    self.intensity[i] = data
            else:
                self.intensity[i] = data

        if not self.holdpeaks:
            self.intensity = savgol_filter(self.intensity, 17, int(self.savpoly))
        self.intensity = np.clip(np.array(self.intensity).astype(int), 0, 255)

        wavelengthdata = []
        index = 0
        for i in self.intensity:
            wavelength = (scalezero + (index / pxpernm))
            wl_display = round(wavelength, 1)
            wavelength = round(wavelength)
            wavelengthdata.append(wl_display)
            r, g, b = self.wavelength_to_rgb(wavelength)
            cv2.line(graph, (index, 255), (index, 255 - i), (r, g, b), 1)
            cv2.line(graph, (index, 254 - i), (index, 255 - i), (0, 0, 0), 1, cv2.LINE_AA)
            index += 1

        thresh = int(self.thresh)
        max_intensity = max(self.intensity) if max(self.intensity) > 0 else 1
        indexes = peakutils.indexes(self.intensity, thres=thresh / max_intensity, min_dist=int(self.mindist))
        for i in indexes:
            height = self.intensity[i]
            height = 245 - height
            wavelength = scalezero + (i / pxpernm)
            wl_str = f"{wavelength:.1f}" if wavelength % 1 >= 0.05 and wavelength % 1 <= 0.95 else f"{int(round(wavelength))}"
            label_text = f"{wl_str}nm"
            text_size = cv2.getTextSize(label_text, font, 0.4, 1)[0]
            box_w = text_size[0] + 6
            cv2.rectangle(graph, ((i - textoffset) - 2, height + 3), ((i - textoffset) + box_w, height - 11), (255, 255, 0), -1)
            cv2.rectangle(graph, ((i - textoffset) - 2, height + 3), ((i - textoffset) + box_w, height - 11), (0, 0, 0), 1)
            cv2.putText(graph, label_text, (i - textoffset, height), font, 0.4, (0, 0, 0), 1, cv2.LINE_AA)

        return (True, [graph, wavelengthdata, self.intensity])


def arg_parser() -> argparse.ArgumentParser:
    def parse_calibration(s):
        try:
            s = s.strip(" ()[]{}")
            sep = ';' if ';' in s else ','
            parts = [p.strip() for p in s.split(sep)]
            if len(parts) != 2:
                raise ValueError
            pts = []
            for p in parts:
                p = p.strip(" ()[]{}")
                sub_sep = ':' if ':' in p else (',' if ',' in p else None)
                if sub_sep:
                    sub_parts = [float(x.strip()) for x in p.split(sub_sep)]
                else:
                    sub_parts = [float(x.strip()) for x in p.split()]
                if len(sub_parts) != 2:
                    raise ValueError
                p_val = int(round(sub_parts[0]))
                wl_val = sub_parts[1] if sub_parts[1] % 1 != 0 else int(sub_parts[1])
                pts.append((p_val, wl_val))
            return tuple(pts)
        except Exception:
            raise argparse.ArgumentTypeError(
                "Calibration must be in the format pixel:nm,pixel:nm (e.g. 72:400,304:530 or 72:404.7,304:532.0)"
            )

    parser = argparse.ArgumentParser(description="Analyze pre-captured spectrum images from a folder or file.")
    parser.add_argument('-c', '--calibration', type=parse_calibration,
                        help="e.g. -c 72:400,304:530 (pixel:nm,pixel:nm)")
    parser.add_argument('-f', '--folder', type=str,
                        help="Folder containing spectrum images or specific image file to analyze")
    return parser


def main():
    """Main entry point for PySpectrometer Image Folder Edition."""
    parser = arg_parser()
    args = parser.parse_args()
    root = tkinter.Tk()
    App(args, root, "PySpectrometer - Image Folder Edition")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
