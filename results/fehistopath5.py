import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
from PIL import Image, ImageTk, ImageOps, ImageEnhance, ImageDraw, ImageFilter
import numpy as np
import cv2
import os
import json
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import webbrowser
import uuid

class HistoPathAnalyst:
    def __init__(self, root):
        self.root = root
        self.root.title("FECORO | HistoPath Analyst v0.6")
        self.root.geometry("1600x1000")
        self.root.configure(bg="#f0f2f5")
        try:
            self.root.state('zoomed')
        except tk.TclError:
            try:
                self.root.attributes('-zoomed', True)
            except:
                self.root.geometry("1400x900")

        # --- Configuración de estilo moderno ---
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.primary_color = "#1a3c5e"
        self.secondary_color = "#2980b9"
        self.accent_color = "#e74c3c"
        self.light_bg = "#f0f2f5"
        self.dark_text = "#2c3e50"
        self.style.configure(".", background=self.light_bg, foreground=self.dark_text)
        self.style.configure("TFrame", background=self.light_bg)
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=8,
                            background=self.secondary_color, foreground="white")
        self.style.map("TButton",
                      background=[('active', self.primary_color), ('pressed', self.accent_color)],
                      foreground=[('active', 'white'), ('pressed', 'white')])
        self.style.configure("TLabel", background=self.light_bg, font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), foreground=self.primary_color)
        self.style.configure("Tool.TRadiobutton", font=("Segoe UI", 10), padding=5,
                            indicatorrelief=tk.FLAT, background=self.light_bg)
        self.style.map("Tool.TRadiobutton", background=[('active', '#e0e0e0')])
        self.style.configure("TLabelframe", font=("Segoe UI", 10, "bold"),
                            foreground=self.primary_color, background=self.light_bg)
        self.style.configure("TLabelframe.Label", foreground=self.primary_color)
        self.style.configure("TScale", background=self.light_bg)
        self.style.configure("TEntry", font=("Segoe UI", 10))

        # Variables de estado
        self.image_path = None
        self.original_image = None
        self.display_image = None
        self.tk_image = None
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.brightness_factor = 1.0
        self.contrast_factor = 1.0
        self.gamma_factor = 1.0
        self.rotation_angle = 0
        self.flip_horizontal = False
        self.flip_vertical = False
        self.filter_type = "NONE"
        self.ki67_points = []
        self.mitosis_points = []
        self.negative_points = []
        self.action_history = []
        self.redo_stack = []
        self.annotation_mode = tk.StringVar(value="ki67")
        self.ki67_color = tk.StringVar(value="#ff4d4d")
        self.mitosis_color = tk.StringVar(value="#4d4dff")
        self.negative_color = tk.StringVar(value="#4dff4d")
        self.calibration_scale = 0.25  # µm/pixel
        self.current_project_name = tk.StringVar(value="Sin título")

        # Crear interfaz
        self.create_menu()
        self.create_widgets()
        self.update_color_buttons()
        self.create_shortcuts()
        self.load_recent_projects()

    def create_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Nuevo Proyecto", command=self.new_project, accelerator="Ctrl+N")
        file_menu.add_command(label="Abrir Imagen", command=self.open_image, accelerator="Ctrl+O")
        file_menu.add_command(label="Abrir Proyecto (.hpa)", command=self.open_project)
        file_menu.add_command(label="Cargar Anotaciones (JSON)", command=self.load_annotations, accelerator="Ctrl+L")
        file_menu.add_command(label="Guardar Anotaciones (JSON)", command=self.save_annotations, accelerator="Ctrl+J")
        self.recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Proyectos Recientes", menu=self.recent_menu)
        file_menu.add_separator()
        file_menu.add_command(label="Guardar Proyecto", command=self.save_project, accelerator="Ctrl+S")
        file_menu.add_command(label="Guardar Proyecto Como...", command=self.save_project_as, accelerator="Ctrl+Shift+S")
        file_menu.add_command(label="Exportar Imagen con Marcadores", command=self.export_results)
        file_menu.add_command(label="Exportar Métricas", command=self.calculate_metrics)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.root.quit)
        menubar.add_cascade(label="Archivo", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Deshacer", command=self.undo_last_action, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Rehacer", command=self.redo_action, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Limpiar Todos los Marcadores", command=self.clear_markers)
        menubar.add_cascade(label="Editar", menu=edit_menu)

        image_menu = tk.Menu(menubar, tearoff=0)
        image_menu.add_command(label="Ajustar Brillo", command=self.adjust_brightness)
        image_menu.add_command(label="Ajustar Contraste", command=self.adjust_contrast)
        image_menu.add_command(label="Ajustar Gamma", command=self.adjust_gamma)
        image_menu.add_separator()
        image_menu.add_command(label="Rotar 90° Derecha", command=lambda: self.rotate_image(90))
        image_menu.add_command(label="Rotar 90° Izquierda", command=lambda: self.rotate_image(-90))
        image_menu.add_command(label="Voltear Horizontalmente", command=self.flip_image_horizontal)
        image_menu.add_command(label="Voltear Verticalmente", command=self.flip_image_vertical)
        image_menu.add_separator()
        filter_menu = tk.Menu(image_menu, tearoff=0)
        filter_menu.add_command(label="Sin Filtro", command=lambda: self.apply_filter("NONE"))
        filter_menu.add_command(label="Desenfoque", command=lambda: self.apply_filter("BLUR"))
        filter_menu.add_command(label="Enfoque", command=lambda: self.apply_filter("SHARPEN"))
        filter_menu.add_command(label="Detectar Bordes", command=lambda: self.apply_filter("EDGE"))
        image_menu.add_cascade(label="Filtros", menu=filter_menu)
        image_menu.add_command(label="Restablecer Imagen", command=self.reset_image)
        menubar.add_cascade(label="Imagen", menu=image_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Calibrar Escala", command=self.calibrate_scale)
        tools_menu.add_command(label="Conteo Automático (Ki-67 IHC)", command=lambda: self.run_pathonet("ki67"))
        tools_menu.add_command(label="Conteo Automático (H&E Mitosis)", command=lambda: self.run_pathonet("mitosis"))
        menubar.add_cascade(label="Herramientas", menu=tools_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Documentación", command=self.show_documentation)
        help_menu.add_command(label="Tutorial Rápido", command=self.show_quick_tutorial, accelerator="F1")
        help_menu.add_command(label="Verificar Actualizaciones", command=self.check_for_updates)
        help_menu.add_separator()
        help_menu.add_command(label="Acerca de", command=self.show_about)
        menubar.add_cascade(label="Ayuda", menu=help_menu)
        self.root.config(menu=menubar)

    def create_shortcuts(self):
        self.root.bind("<Control-n>", lambda event: self.new_project())
        self.root.bind("<Control-o>", lambda event: self.open_image())
        self.root.bind("<Control-s>", lambda event: self.save_project())
        self.root.bind("<Control-Shift-S>", lambda event: self.save_project_as())
        self.root.bind("<Control-l>", lambda event: self.load_annotations())
        self.root.bind("<Control-j>", lambda event: self.save_annotations())
        self.root.bind("<Control-z>", lambda event: self.undo_last_action())
        self.root.bind("<Control-y>", lambda event: self.redo_action())
        self.root.bind("<Control-plus>", lambda event: self.adjust_zoom(1.25))
        self.root.bind("<Control-minus>", lambda event: self.adjust_zoom(0.8))
        self.root.bind("<Control-0>", lambda event: self.zoom_fit())
        self.root.bind("<F1>", lambda event: self.show_quick_tutorial())
        self.root.bind("<F2>", lambda e: self.annotation_mode.set("ki67"))
        self.root.bind("<F3>", lambda e: self.annotation_mode.set("mitosis"))
        self.root.bind("<F4>", lambda e: self.annotation_mode.set("negative"))
        self.root.bind("<F5>", lambda e: self.annotation_mode.set("eraser"))

    def create_widgets(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # --- Panel izquierdo (controles) con scrollbar ---
        control_canvas = tk.Canvas(main_frame, width=320, bg=self.light_bg, highlightthickness=0)
        control_canvas.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        v_scroll = ttk.Scrollbar(main_frame, orient="vertical", command=control_canvas.yview)
        v_scroll.pack(side=tk.LEFT, fill=tk.Y)
        control_canvas.configure(yscrollcommand=v_scroll.set)
        control_frame = ttk.Frame(control_canvas, style="TFrame")
        control_canvas.create_window((0, 0), window=control_frame, anchor="nw", width=320)
        control_frame.bind("<Configure>", lambda e: control_canvas.configure(scrollregion=control_canvas.bbox("all")))
        control_canvas.bind_all("<MouseWheel>", lambda e: control_canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        # --- Project Name ---
        project_lf = ttk.LabelFrame(control_frame, text="Proyecto", padding=(10, 5))
        project_lf.pack(fill=tk.X, pady=5)
        ttk.Label(project_lf, text="Nombre:").pack(anchor=tk.W, pady=2)
        ttk.Entry(project_lf, textvariable=self.current_project_name, width=30).pack(fill=tk.X, pady=2)

        # --- Herramientas de Anotación ---
        tools_lf = ttk.LabelFrame(control_frame, text="Herramientas de Anotación", padding=(10, 5))
        tools_lf.pack(fill=tk.X, pady=5)
        tool_frame = ttk.Frame(tools_lf)
        tool_frame.pack(fill=tk.X)
        ttk.Radiobutton(tool_frame, text="Ki-67 (+) [F2]", variable=self.annotation_mode,
                        value="ki67", style="Tool.TRadiobutton").pack(anchor=tk.W, fill=tk.X, pady=2)
        ttk.Radiobutton(tool_frame, text="Mitosis [F3]", variable=self.annotation_mode,
                        value="mitosis", style="Tool.TRadiobutton").pack(anchor=tk.W, fill=tk.X, pady=2)
        ttk.Radiobutton(tool_frame, text="Negativo (-) [F4]", variable=self.annotation_mode,
                        value="negative", style="Tool.TRadiobutton").pack(anchor=tk.W, fill=tk.X, pady=2)
        ttk.Radiobutton(tool_frame, text="Goma de Borrar [F5]", variable=self.annotation_mode,
                        value="eraser", style="Tool.TRadiobutton").pack(anchor=tk.W, fill=tk.X, pady=2)

        # --- Contadores ---
        counter_lf = ttk.LabelFrame(control_frame, text="Contadores", padding=(10, 5))
        counter_lf.pack(fill=tk.X, pady=5)
        self.ki67_count_label = ttk.Label(counter_lf, text="Ki-67 (+): 0",
                                         font=("Segoe UI", 10, "bold"), foreground=self.ki67_color.get())
        self.ki67_count_label.pack(anchor=tk.W, pady=2)
        self.mitosis_count_label = ttk.Label(counter_lf, text="Mitosis: 0",
                                            font=("Segoe UI", 10, "bold"), foreground=self.mitosis_color.get())
        self.mitosis_count_label.pack(anchor=tk.W, pady=2)
        self.negative_count_label = ttk.Label(counter_lf, text="Negativo (-): 0",
                                             font=("Segoe UI", 10, "bold"), foreground=self.negative_color.get())
        self.negative_count_label.pack(anchor=tk.W, pady=2)
        self.total_count = ttk.Label(counter_lf, text="Total: 0",
                                    font=("Segoe UI", 10, "bold"), foreground=self.primary_color)
        self.total_count.pack(anchor=tk.W, pady=(5, 0))

        # --- Auto-Conteo ---
        autocount_lf = ttk.LabelFrame(control_frame, text="Conteo Automático", padding=(10, 5))
        autocount_lf.pack(fill=tk.X, pady=5)
        ttk.Button(autocount_lf, text="Conteo Ki-67 IHC", command=lambda: self.run_pathonet("ki67")).pack(fill=tk.X, pady=2)
        ttk.Button(autocount_lf, text="Conteo H&E Mitosis", command=lambda: self.run_pathonet("mitosis")).pack(fill=tk.X, pady=2)

        # --- Acciones rápidas ---
        actions_lf = ttk.LabelFrame(control_frame, text="Acciones Rápidas", padding=(10, 5))
        actions_lf.pack(fill=tk.X, pady=5)
        ttk.Button(actions_lf, text="Deshacer (Ctrl+Z)", command=self.undo_last_action).pack(fill=tk.X, pady=2)
        ttk.Button(actions_lf, text="Rehacer (Ctrl+Y)", command=self.redo_action).pack(fill=tk.X, pady=2)
        ttk.Button(actions_lf, text="Limpiar Marcadores", command=self.clear_markers).pack(fill=tk.X, pady=2)

        # --- Personalización ---
        custom_lf = ttk.LabelFrame(control_frame, text="Personalización", padding=(10, 5))
        custom_lf.pack(fill=tk.X, pady=5)
        self.ki67_color_btn = ttk.Button(custom_lf, text="Color Ki-67",
                                         command=lambda: self.change_color('ki67'))
        self.ki67_color_btn.pack(fill=tk.X, pady=2)
        self.mitosis_color_btn = ttk.Button(custom_lf, text="Color Mitosis",
                                           command=lambda: self.change_color('mitosis'))
        self.mitosis_color_btn.pack(fill=tk.X, pady=2)
        self.negative_color_btn = ttk.Button(custom_lf, text="Color Negativo",
                                            command=lambda: self.change_color('negative'))
        self.negative_color_btn.pack(fill=tk.X, pady=2)

        # --- Herramientas de zoom ---
        zoom_lf = ttk.LabelFrame(control_frame, text="Zoom y Navegación", padding=(10, 5))
        zoom_lf.pack(fill=tk.X, pady=5)
        zoom_frame = ttk.Frame(zoom_lf)
        zoom_frame.pack(fill=tk.X, pady=5)
        ttk.Button(zoom_frame, text="+", width=3, command=lambda: self.adjust_zoom(1.25)).pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_frame, text="-", width=3, command=lambda: self.adjust_zoom(0.8)).pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_frame, text="100%", command=self.zoom_100).pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_frame, text="Ajustar", command=self.zoom_fit).pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_frame, text="↻", width=3, command=lambda: self.rotate_image(90)).pack(side=tk.RIGHT, padx=2)
        ttk.Button(zoom_frame, text="↺", width=3, command=lambda: self.rotate_image(-90)).pack(side=tk.RIGHT, padx=2)
        self.zoom_label = ttk.Label(zoom_lf, text="Zoom: 100%")
        self.zoom_label.pack(anchor=tk.W)

        # --- Información de imagen ---
        info_lf = ttk.LabelFrame(control_frame, text="Información de Imagen", padding=(10, 5))
        info_lf.pack(fill=tk.X, pady=5)
        self.info_label = ttk.Label(info_lf, text="Cargue una imagen para ver detalles.", wraplength=280)
        self.info_label.pack(anchor=tk.W)
        self.scale_label = ttk.Label(info_lf, text=f"Escala: {self.calibration_scale:.4f} µm/pixel",
                                    font=("Segoe UI", 9, "italic"))
        self.scale_label.pack(anchor=tk.W)

        # --- Panel de visualización ---
        vis_frame = ttk.Frame(main_frame)
        vis_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.canvas_frame = ttk.Frame(vis_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(self.canvas_frame, bg="#2c3e50", cursor="cross")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll_canvas = ttk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        v_scroll_canvas.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll = ttk.Scrollbar(vis_frame, orient="horizontal", command=self.canvas.xview)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.configure(yscrollcommand=v_scroll_canvas.set, xscrollcommand=h_scroll.set)

        # Eventos del canvas
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<ButtonPress-3>", self.on_right_click)
        self.canvas.bind("<ButtonPress-2>", self.start_pan)
        self.canvas.bind("<B2-Motion>", self.on_pan)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Motion>", self.update_mouse_coords)

        # --- Barra de estado ---
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar = ttk.Label(status_frame, text="Listo", relief=tk.SUNKEN, anchor=tk.W, padding=5)
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.coord_label = ttk.Label(status_frame, text="x: 0, y: 0", relief=tk.SUNKEN, anchor=tk.E, width=25, padding=5)
        self.coord_label.pack(side=tk.RIGHT, fill=tk.Y)
        self.tool_label = ttk.Label(status_frame, text="Herramienta: Ki-67 (+)", relief=tk.SUNKEN, anchor=tk.E, width=20, padding=5)
        self.tool_label.pack(side=tk.RIGHT, fill=tk.Y)
        self.annotation_mode.trace_add("write", self.update_tool_label)

    def update_tool_label(self, *args):
        tool_text = {
            "ki67": "Ki-67 (+)",
            "mitosis": "Mitosis",
            "negative": "Negativo (-)",
            "eraser": "Goma de Borrar"
        }
        self.tool_label.config(text=f"Herramienta: {tool_text[self.annotation_mode.get()]}")

    def new_project(self):
        if self.image_path and messagebox.askyesno("Nuevo Proyecto",
                                                 "¿Está seguro que desea crear un nuevo proyecto?\nSe perderán los cambios no guardados."):
            self.image_path = None
            self.original_image = None
            self.display_image = None
            self.tk_image = None
            self.canvas.delete("all")
            self.clear_markers()
            self.zoom_factor = 1.0
            self.pan_x = 0
            self.pan_y = 0
            self.brightness_factor = 1.0
            self.contrast_factor = 1.0
            self.gamma_factor = 1.0
            self.rotation_angle = 0
            self.flip_horizontal = False
            self.flip_vertical = False
            self.filter_type = "NONE"
            self.current_project_name.set("Sin título")
            self.info_label.config(text="Cargue una imagen para ver detalles.")
            self.status_bar.config(text="Nuevo proyecto creado")

    def open_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Imágenes", "*.tif *.tiff *.jpg *.jpeg *.png *.svs *.bmp"),
                       ("Todos los archivos", "*.*")]
        )
        if not file_path:
            return
        try:
            self.image_path = file_path
            self.original_image = Image.open(file_path)
            self.clear_markers()
            self.zoom_factor = 1.0
            self.pan_x = 0
            self.pan_y = 0
            self.rotation_angle = 0
            self.flip_horizontal = False
            self.flip_vertical = False
            self.filter_type = "NONE"
            self.brightness_factor = 1.0
            self.contrast_factor = 1.0
            self.gamma_factor = 1.0
            if self.original_image.mode == 'RGBA':
                self.original_image = self.original_image.convert('RGB')
            self.display_image = self.original_image.copy()
            self.current_project_name.set(os.path.splitext(os.path.basename(file_path))[0])
            self.show_image_info()
            self.display_image_on_canvas(fit_to_screen=True)
            self.status_bar.config(text=f"Imagen cargada: {os.path.basename(file_path)}")
            self.add_to_recent(file_path)
        except Exception as e:
            messagebox.showerror("Error al Abrir Imagen", f"No se pudo abrir o procesar la imagen:\n{str(e)}")

    def open_project(self):
        file_path = filedialog.askopenfilename(
            title="Abrir proyecto HistoPath Analyst",
            filetypes=[("HistoPath Analyst Project", "*.hpa"), ("Todos los archivos", "*.*")]
        )
        if not file_path:
            return
        try:
            with open(file_path, 'r') as f:
                project_data = json.load(f)
            version = project_data.get("version", "1.0")
            if version != "1.3":
                if not messagebox.askyesno("Versión de Proyecto",
                                          f"Este proyecto fue creado con la versión {version}. "
                                          "¿Desea intentar cargarlo de todos modos?"):
                    return
            image_path = project_data.get("image_path")
            if not image_path or not os.path.exists(image_path):
                image_path = filedialog.askopenfilename(
                    title="Seleccione la imagen del proyecto (no encontrada)",
                    filetypes=[("Imágenes", "*.tif *.tiff *.jpg *.jpeg *.png *.svs"), ("Todos los archivos", "*.*")]
                )
                if not image_path:
                    return
            self.image_path = image_path
            self.original_image = Image.open(self.image_path)
            if self.original_image.mode == 'RGBA':
                self.original_image = self.original_image.convert('RGB')
            self.clear_markers()
            self.zoom_factor = 1.0
            self.pan_x = 0
            self.pan_y = 0
            self.rotation_angle = project_data.get("rotation", 0)
            self.flip_horizontal = project_data.get("flip_h", False)
            self.flip_vertical = project_data.get("flip_v", False)
            self.brightness_factor = project_data.get("brightness", 1.0)
            self.contrast_factor = project_data.get("contrast", 1.0)
            self.gamma_factor = project_data.get("gamma", 1.0)
            self.filter_type = project_data.get("filter", "NONE")
            self.display_image = self.original_image.copy()
            self.apply_all_transforms()
            self.calibration_scale = project_data.get("calibration_scale", 0.25)
            self.current_project_name.set(project_data.get("project_name", "Sin título"))
            self.scale_label.config(text=f"Escala: {self.calibration_scale:.4f} µm/pixel")
            annotations = project_data.get("annotations", [])
            label_map = {
                1: self.ki67_points,
                2: self.negative_points,
                3: self.mitosis_points
            }
            for ann in annotations:
                x, y, label_id = ann.get('x'), ann.get('y'), ann.get('label_id')
                if x is not None and y is not None and label_id in label_map:
                    label_map[label_id].append((x, y, None))
            self.display_image_on_canvas(fit_to_screen=True)
            self.update_all_counts()
            self.redraw_markers()
            self.show_image_info()
            self.status_bar.config(text=f"Proyecto cargado: {os.path.basename(file_path)}")
            self.add_to_recent(file_path, is_image=False)
        except Exception as e:
            messagebox.showerror("Error al cargar proyecto", f"Error: {str(e)}")

    def load_annotations(self):
        if not self.original_image:
            messagebox.showwarning("Sin Imagen", "Por favor, cargue una imagen antes de cargar anotaciones.")
            return
        file_path = filedialog.askopenfilename(
            title="Cargar archivo de anotaciones JSON",
            filetypes=[("JSON files", "*.json"), ("Todos los archivos", "*.*")]
        )
        if not file_path:
            return
        try:
            with open(file_path, 'r') as f:
                annotations = json.load(f)
            if not isinstance(annotations, list):
                raise ValueError("El archivo JSON debe contener una lista de anotaciones.")
            self.clear_markers()
            label_map = {
                1: self.ki67_points,
                2: self.negative_points,
                3: self.mitosis_points
            }
            for ann in annotations:
                x, y, label_id = ann.get('x'), ann.get('y'), ann.get('label_id')
                if x is not None and y is not None and label_id in label_map:
                    label_map[label_id].append((x, y, None))
            self.update_all_counts()
            self.redraw_markers()
            self.status_bar.config(text=f"{len(annotations)} anotaciones cargadas desde {os.path.basename(file_path)}")
            self.add_to_recent(file_path, is_image=False)
            messagebox.showinfo("Éxito", "Anotaciones cargadas correctamente.")
        except Exception as e:
            messagebox.showerror("Error de Carga", f"No se pudo cargar o procesar el archivo JSON:\n{str(e)}")

    def save_annotations(self):
        if not self.original_image:
            messagebox.showwarning("Sin Imagen", "Por favor, cargue una imagen para guardar anotaciones.")
            return
        file_path = filedialog.asksaveasfilename(
            title="Guardar Anotaciones como JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("Todos los archivos", "*.*")]
        )
        if not file_path:
            return
        try:
            all_annotations = []
            for x, y, _ in self.ki67_points:
                all_annotations.append({"x": int(x), "y": int(y), "label_id": 1})
            for x, y, _ in self.negative_points:
                all_annotations.append({"x": int(x), "y": int(y), "label_id": 2})
            for x, y, _ in self.mitosis_points:
                all_annotations.append({"x": int(x), "y": int(y), "label_id": 3})
            with open(file_path, 'w') as f:
                json.dump(all_annotations, f, indent=4)
            self.status_bar.config(text=f"Anotaciones guardadas en: {file_path}")
            self.add_to_recent(file_path, is_image=False)
            messagebox.showinfo("Guardado Exitoso", "Las anotaciones se guardaron correctamente en formato JSON.")
        except Exception as e:
            messagebox.showerror("Error al Guardar", f"No se pudo guardar el archivo JSON:\n{str(e)}")

    def save_project(self):
        if not self.image_path:
            self.save_project_as()
            return
        self._save_project_to_file(self.image_path.replace(os.path.splitext(self.image_path)[1], ".hpa"))

    def save_project_as(self):
        if not self.image_path:
            messagebox.showwarning("Proyecto Vacío", "No hay un proyecto activo para guardar.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".hpa",
            filetypes=[("HistoPath Analyst Project", "*.hpa"), ("Todos los archivos", "*.*")]
        )
        if not file_path:
            return
        self._save_project_to_file(file_path)

    def _save_project_to_file(self, file_path):
        try:
            all_annotations = []
            for x, y, _ in self.ki67_points:
                all_annotations.append({"x": int(x), "y": int(y), "label_id": 1})
            for x, y, _ in self.negative_points:
                all_annotations.append({"x": int(x), "y": int(y), "label_id": 2})
            for x, y, _ in self.mitosis_points:
                all_annotations.append({"x": int(x), "y": int(y), "label_id": 3})
            project_data = {
                "version": "1.3",
                "project_name": self.current_project_name.get(),
                "image_path": self.image_path,
                "calibration_scale": self.calibration_scale,
                "rotation": self.rotation_angle,
                "flip_h": self.flip_horizontal,
                "flip_v": self.flip_vertical,
                "brightness": self.brightness_factor,
                "contrast": self.contrast_factor,
                "gamma": self.gamma_factor,
                "filter": self.filter_type,
                "annotations": all_annotations,
                "timestamp": datetime.now().isoformat()
            }
            with open(file_path, 'w') as f:
                json.dump(project_data, f, indent=4)
            self.status_bar.config(text=f"Proyecto guardado en: {file_path}")
            self.add_to_recent(file_path, is_image=False)
            messagebox.showinfo("Guardado Exitoso", "El proyecto se guardó correctamente.")
        except Exception as e:
            messagebox.showerror("Error al Guardar", f"No se pudo guardar el proyecto:\n{str(e)}")

    def export_results(self):
        if not self.original_image:
            messagebox.showwarning("Sin Imagen", "Por favor, cargue una imagen para exportar los resultados.")
            return
        file_path = filedialog.asksaveasfilename(
            title="Exportar Imagen con Marcadores",
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("TIFF files", "*.tif"), ("Todos los archivos", "*.*")]
        )
        if not file_path:
            return
        try:
            result_img = self.original_image.copy().convert("RGB")
            draw = ImageDraw.Draw(result_img)
            radius = 12
            width = 3
            for x, y, _ in self.ki67_points:
                draw.ellipse([x - radius, y - radius, x + radius, y + radius],
                             outline=self.ki67_color.get(), width=width)
            for x, y, _ in self.mitosis_points:
                draw.ellipse([x - radius, y - radius, x + radius, y + radius],
                             outline=self.mitosis_color.get(), width=width)
            for x, y, _ in self.negative_points:
                draw.ellipse([x - radius, y - radius, x + radius, y + radius],
                             outline=self.negative_color.get(), width=width)
            result_img = self.apply_transforms_to_image(result_img)
            result_img.save(file_path)
            self.status_bar.config(text=f"Resultados exportados a: {file_path}")
            messagebox.showinfo("Exportación Exitosa", f"La imagen con los marcadores se guardó correctamente en:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error de Exportación", f"No se pudo guardar la imagen:\n{str(e)}")

    def display_image_on_canvas(self, fit_to_screen=False):
        if not self.original_image:
            return
        self.root.update_idletasks()
        canvas_width = max(1, self.canvas.winfo_width())
        canvas_height = max(1, self.canvas.winfo_height())
        img_width, img_height = self.display_image.size
        if fit_to_screen:
            ratio = min(canvas_width / img_width, canvas_height / img_height, 1.0)
            self.zoom_factor = ratio
            self.pan_x = 0
            self.pan_y = 0
        new_size = (int(img_width * self.zoom_factor), int(img_height * self.zoom_factor))
        if new_size[0] < 1 or new_size[1] < 1:
            return
        display_img = self.display_image.resize(new_size, Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(display_img)
        self.canvas.delete("all")
        self.canvas.create_image(self.pan_x, self.pan_y, anchor=tk.NW, image=self.tk_image, tags="image")
        self.canvas.config(scrollregion=(0, 0, new_size[0], new_size[1]))
        self.redraw_markers()
        self.draw_scale_bar()
        self.update_zoom_label()

    def redraw_markers(self):
        if not self.display_image or not self.original_image:
            return
        self.canvas.delete("marker")
        scale_x = self.display_image.width / self.original_image.width
        scale_y = self.display_image.height / self.original_image.height
        radius = max(5, min(8, int(8 / self.zoom_factor)))  # Dynamic radius
        for points_list, color, tag in [
            (self.ki67_points, self.ki67_color.get(), "ki67_marker"),
            (self.mitosis_points, self.mitosis_color.get(), "mitosis_marker"),
            (self.negative_points, self.negative_color.get(), "negative_marker")
        ]:
            for i, (x, y, _) in enumerate(points_list):
                display_x = x * self.zoom_factor * scale_x + self.pan_x
                display_y = y * self.zoom_factor * scale_y + self.pan_y
                marker_id = self.canvas.create_oval(
                    display_x - radius, display_y - radius,
                    display_x + radius, display_y + radius,
                    outline=color, width=2, tags=("marker", tag)
                )
                points_list[i] = (x, y, marker_id)

    def draw_scale_bar(self):
        if not self.original_image or self.zoom_factor < 0.01:
            return
        self.canvas.delete("scale_bar")
        target_um = 100
        if self.original_image.width * self.calibration_scale < 200:
            target_um = 50
        if self.original_image.width * self.calibration_scale < 100:
            target_um = 20
        length_px_orig = target_um / self.calibration_scale
        length_px_display = length_px_orig * self.zoom_factor
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        x0 = canvas_width - length_px_display - 20
        y0 = canvas_height - 20
        x1 = canvas_width - 20
        if x0 < 10 or length_px_display < 20:
            return
        self.canvas.create_line(x0, y0, x1, y0, fill="white", width=3, tags="scale_bar")
        self.canvas.create_rectangle(x0-2, y0-3, x1+2, y0+3, fill="white", outline="", tags="scale_bar")
        self.canvas.create_text(x0 + length_px_display / 2, y0 - 10,
                                text=f"{target_um} µm", fill="white",
                                font=("Segoe UI", 10, "bold"), tags="scale_bar")

    def on_mouse_press(self, event):
        if not self.original_image:
            return
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        orig_x = (canvas_x - self.pan_x) / self.zoom_factor
        orig_y = (canvas_y - self.pan_y) / self.zoom_factor
        if 0 <= orig_x < self.original_image.width and 0 <= orig_y < self.original_image.height:
            mode = self.annotation_mode.get()
            if mode in ["ki67", "mitosis", "negative"]:
                self.add_marker(orig_x, orig_y, mode)
            elif mode == "eraser":
                self.erase_marker_at(orig_x, orig_y)

    def on_right_click(self, event):
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Ajustar a Ventana", command=self.zoom_fit)
        context_menu.add_command(label="Zoom 100%", command=self.zoom_100)
        context_menu.add_separator()
        context_menu.add_command(label="Deshacer (Ctrl+Z)", command=self.undo_last_action)
        context_menu.add_command(label="Rehacer (Ctrl+Y)", command=self.redo_action)
        context_menu.add_command(label="Limpiar Marcadores", command=self.clear_markers)
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def add_marker(self, x, y, marker_type):
        point_data = (x, y, None)
        target_list = getattr(self, f"{marker_type}_points")
        target_list.append(point_data)
        self.action_history.append(('add', marker_type, point_data))
        self.redo_stack = []
        self.update_all_counts()
        self.redraw_markers()
        self.status_bar.config(text=f"Marcador '{marker_type}' añadido en ({int(x)}, {int(y)})")

    def erase_marker_at(self, x, y):
        search_radius = 15 / self.zoom_factor
        closest_marker = None
        min_dist = float('inf')
        marker_list_ref = None
        marker_index = -1
        marker_type_str = ""
        for mtype, lst in [("ki67", self.ki67_points), ("mitosis", self.mitosis_points), ("negative", self.negative_points)]:
            for i, (px, py, cid) in enumerate(lst):
                dist = np.sqrt((x - px)**2 + (y - py)**2)
                if dist < search_radius and dist < min_dist:
                    min_dist = dist
                    closest_marker = (px, py, cid)
                    marker_list_ref = lst
                    marker_index = i
                    marker_type_str = mtype
        if closest_marker:
            marker_list_ref.pop(marker_index)
            self.canvas.delete(closest_marker[2])
            self.action_history.append(('delete', marker_type_str, closest_marker))
            self.redo_stack = []
            self.update_all_counts()
            self.status_bar.config(text=f"Marcador eliminado en ({int(closest_marker[0])}, {int(closest_marker[1])})")

    def undo_last_action(self):
        if not self.action_history:
            self.status_bar.config(text="Nada que deshacer.")
            return
        action, marker_type, data = self.action_history.pop()
        self.redo_stack.append((action, marker_type, data))
        if action == 'add':
            target_list = getattr(self, f"{marker_type}_points")
            for i, point in enumerate(target_list):
                if point[0] == data[0] and point[1] == data[1]:
                    del target_list[i]
                    break
            self.status_bar.config(text=f"Deshecho: Añadir marcador '{marker_type}'")
        elif action == 'delete':
            target_list = getattr(self, f"{marker_type}_points")
            target_list.append(data)
            self.status_bar.config(text=f"Deshecho: Eliminar marcador '{marker_type}'")
        self.update_all_counts()
        self.redraw_markers()

    def redo_action(self):
        if not self.redo_stack:
            self.status_bar.config(text="Nada que rehacer.")
            return
        action, marker_type, data = self.redo_stack.pop()
        self.action_history.append((action, marker_type, data))
        if action == 'add':
            target_list = getattr(self, f"{marker_type}_points")
            target_list.append(data)
            self.status_bar.config(text=f"Rehecho: Añadir marcador '{marker_type}'")
        elif action == 'delete':
            target_list = getattr(self, f"{marker_type}_points")
            for i, point in enumerate(target_list):
                if point[0] == data[0] and point[1] == data[1]:
                    del target_list[i]
                    break
            self.status_bar.config(text=f"Rehecho: Eliminar marcador '{marker_type}'")
        self.update_all_counts()
        self.redraw_markers()

    def on_mouse_wheel(self, event):
        if not self.original_image:
            return
        factor = 1.1 if event.delta > 0 else 0.9
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        img_x = (canvas_x - self.pan_x) / self.zoom_factor
        img_y = (canvas_y - self.pan_y) / self.zoom_factor
        self.zoom_factor *= factor
        self.zoom_factor = max(0.01, min(self.zoom_factor, 20.0))
        self.pan_x = canvas_x - img_x * self.zoom_factor
        self.pan_y = canvas_y - img_y * self.zoom_factor
        self.display_image_on_canvas()
        self.update_zoom_label()

    def start_pan(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def on_pan(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self.pan_x = self.canvas.canvasx(0)
        self.pan_y = self.canvas.canvasy(0)
        self.redraw_markers()
        self.draw_scale_bar()

    def update_mouse_coords(self, event):
        if self.original_image:
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            orig_x = (canvas_x - self.pan_x) / self.zoom_factor
            orig_y = (canvas_y - self.pan_y) / self.zoom_factor
            coord_text = f"Pixel: ({int(orig_x)}, {int(orig_y)})"
            if self.calibration_scale > 0:
                um_x = orig_x * self.calibration_scale
                um_y = orig_y * self.calibration_scale
                coord_text = f"µm: ({um_x:.1f}, {um_y:.1f}) | Pixel: ({int(orig_x)}, {int(orig_y)})"
            self.coord_label.config(text=coord_text)

    def clear_markers(self):
        self.canvas.delete("marker")
        self.ki67_points.clear()
        self.mitosis_points.clear()
        self.negative_points.clear()
        self.action_history = []
        self.redo_stack = []
        self.update_all_counts()
        if self.original_image:
            self.status_bar.config(text="Marcadores eliminados.")

    def update_all_counts(self):
        n_ki67 = len(self.ki67_points)
        n_mitosis = len(self.mitosis_points)
        n_negative = len(self.negative_points)
        self.ki67_count_label.config(text=f"Ki-67 (+): {n_ki67}")
        self.mitosis_count_label.config(text=f"Mitosis: {n_mitosis}")
        self.negative_count_label.config(text=f"Negativo (-): {n_negative}")
        self.total_count.config(text=f"Total: {n_ki67 + n_mitosis + n_negative}")

    def show_image_info(self):
        if self.original_image:
            width, height = self.original_image.size
            info_text = f"Dimensiones: {width} × {height} px\n"
            info_text += f"Archivo: {os.path.basename(self.image_path)}\n"
            info_text += f"Tamaño: {(os.path.getsize(self.image_path) / 1024 / 1024):.2f} MB\n"
            if self.rotation_angle != 0:
                info_text += f"Rotación: {self.rotation_angle}°\n"
            if self.flip_horizontal:
                info_text += "Volteo Horizontal\n"
            if self.flip_vertical:
                info_text += "Volteo Vertical\n"
            if self.filter_type != "NONE":
                info_text += f"Filtro: {self.filter_type}\n"
            if self.brightness_factor != 1.0:
                info_text += f"Brillo: {self.brightness_factor:.2f}\n"
            if self.contrast_factor != 1.0:
                info_text += f"Contraste: {self.contrast_factor:.2f}\n"
            if self.gamma_factor != 1.0:
                info_text += f"Gamma: {self.gamma_factor:.2f}"
            self.info_label.config(text=info_text)

    def calibrate_scale(self):
        scale = simpledialog.askfloat("Calibrar Escala",
                                      "Ingrese la escala en micrómetros por píxel (µm/pixel):",
                                      minvalue=0.001, maxvalue=10.0,
                                      initialvalue=self.calibration_scale)
        if scale is not None:
            self.calibration_scale = scale
            self.scale_label.config(text=f"Escala: {self.calibration_scale:.4f} µm/pixel")
            self.status_bar.config(text=f"Escala calibrada: {scale:.4f} µm/pixel")
            self.draw_scale_bar()

    def change_color(self, marker_type):
        current_color = getattr(self, f"{marker_type}_color").get()
        new_color = colorchooser.askcolor(title=f"Elija el color para {marker_type}", initialcolor=current_color)
        if new_color and new_color[1]:
            color_var = getattr(self, f"{marker_type}_color")
            color_var.set(new_color[1])
            self.update_color_buttons()
            self.redraw_markers()

    def update_color_buttons(self):
        self.ki67_count_label.config(foreground=self.ki67_color.get())
        self.mitosis_count_label.config(foreground=self.mitosis_color.get())
        self.negative_count_label.config(foreground=self.negative_color.get())
        for mtype, btn in [('ki67', self.ki67_color_btn), ('mitosis', self.mitosis_color_btn), ('negative', self.negative_color_btn)]:
            color = getattr(self, f"{mtype}_color").get()
            style_name = f"{mtype.capitalize()}.TButton"
            self.style.configure(style_name, background=color, foreground="white")
            btn.config(style=style_name)

    def adjust_zoom(self, factor):
        if self.original_image:
            canvas_x = self.canvas.canvasx(self.canvas.winfo_width() / 2)
            canvas_y = self.canvas.canvasy(self.canvas.winfo_height() / 2)
            img_x = (canvas_x - self.pan_x) / self.zoom_factor
            img_y = (canvas_y - self.pan_y) / self.zoom_factor
            self.zoom_factor *= factor
            self.zoom_factor = max(0.01, min(self.zoom_factor, 20.0))
            self.pan_x = canvas_x - img_x * self.zoom_factor
            self.pan_y = canvas_y - img_y * self.zoom_factor
            self.display_image_on_canvas()
            self.update_zoom_label()

    def zoom_fit(self):
        if self.original_image:
            self.display_image_on_canvas(fit_to_screen=True)
            self.update_zoom_label()

    def zoom_100(self):
        if self.original_image:
            self.zoom_factor = 1.0
            self.pan_x = 0
            self.pan_y = 0
            self.display_image_on_canvas()
            self.update_zoom_label()

    def update_zoom_label(self):
        if self.original_image:
            self.zoom_label.config(text=f"Zoom: {self.zoom_factor*100:.0f}%")

    def adjust_brightness(self):
        brightness = simpledialog.askfloat("Ajustar Brillo", "Factor de brillo (0.1 - 3.0):",
                                          minvalue=0.1, maxvalue=3.0, initialvalue=self.brightness_factor)
        if brightness is not None:
            self.brightness_factor = brightness
            self.apply_all_transforms()
            self.display_image_on_canvas()
            self.status_bar.config(text=f"Brillo ajustado a: {brightness:.2f}")
            self.show_image_info()

    def adjust_contrast(self):
        contrast = simpledialog.askfloat("Ajustar Contraste", "Factor de contraste (0.1 - 3.0):",
                                        minvalue=0.1, maxvalue=3.0, initialvalue=self.contrast_factor)
        if contrast is not None:
            self.contrast_factor = contrast
            self.apply_all_transforms()
            self.display_image_on_canvas()
            self.status_bar.config(text=f"Contraste ajustado a: {contrast:.2f}")
            self.show_image_info()

    def adjust_gamma(self):
        gamma = simpledialog.askfloat("Ajustar Gamma", "Factor gamma (0.1 - 3.0):",
                                     minvalue=0.1, maxvalue=3.0, initialvalue=self.gamma_factor)
        if gamma is not None:
            self.gamma_factor = gamma
            self.apply_all_transforms()
            self.display_image_on_canvas()
            self.status_bar.config(text=f"Gamma ajustado a: {gamma:.2f}")
            self.show_image_info()

    def rotate_image(self, angle):
        self.rotation_angle = (self.rotation_angle + angle) % 360
        self.apply_all_transforms()
        self.display_image_on_canvas()
        self.status_bar.config(text=f"Imagen rotada {angle}°. Rotación actual: {self.rotation_angle}°")
        self.show_image_info()

    def flip_image_horizontal(self):
        self.flip_horizontal = not self.flip_horizontal
        self.apply_all_transforms()
        self.display_image_on_canvas()
        self.status_bar.config(text=f"Volteo horizontal {'activado' if self.flip_horizontal else 'desactivado'}")
        self.show_image_info()

    def flip_image_vertical(self):
        self.flip_vertical = not self.flip_vertical
        self.apply_all_transforms()
        self.display_image_on_canvas()
        self.status_bar.config(text=f"Volteo vertical {'activado' if self.flip_vertical else 'desactivado'}")
        self.show_image_info()

    def apply_filter(self, filter_type):
        self.filter_type = filter_type
        self.apply_all_transforms()
        self.display_image_on_canvas()
        self.status_bar.config(text=f"Filtro aplicado: {filter_type}")
        self.show_image_info()

    def reset_image(self):
        self.brightness_factor = 1.0
        self.contrast_factor = 1.0
        self.gamma_factor = 1.0
        self.rotation_angle = 0
        self.flip_horizontal = False
        self.flip_vertical = False
        self.filter_type = "NONE"
        if self.original_image:
            self.display_image = self.original_image.copy()
            self.display_image_on_canvas()
            self.status_bar.config(text="Imagen restablecida a su estado original")
            self.show_image_info()

    def apply_all_transforms(self):
        if not self.original_image:
            return
        img = self.original_image.copy()
        if self.rotation_angle != 0:
            img = img.rotate(-self.rotation_angle, expand=True)
        if self.flip_horizontal:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if self.flip_vertical:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(self.brightness_factor)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(self.contrast_factor)
        if self.gamma_factor != 1.0:
            img = self.apply_gamma(img, self.gamma_factor)
        if self.filter_type == "BLUR":
            img = img.filter(ImageFilter.BLUR)
        elif self.filter_type == "SHARPEN":
            img = img.filter(ImageFilter.SHARPEN)
        elif self.filter_type == "EDGE":
            img = img.filter(ImageFilter.FIND_EDGES)
        self.display_image = img
        self.show_image_info()

    def apply_gamma(self, image, gamma):
        np_img = np.array(image)
        np_img = np.power(np_img / 255.0, gamma) * 255.0
        np_img = np.clip(np_img, 0, 255).astype(np.uint8)
        return Image.fromarray(np_img)

    def apply_transforms_to_image(self, image):
        img = image.copy()
        if self.rotation_angle != 0:
            img = img.rotate(-self.rotation_angle, expand=True)
        if self.flip_horizontal:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if self.flip_vertical:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(self.brightness_factor)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(self.contrast_factor)
        if self.gamma_factor != 1.0:
            img = self.apply_gamma(img, self.gamma_factor)
        if self.filter_type == "BLUR":
            img = img.filter(ImageFilter.BLUR)
        elif self.filter_type == "SHARPEN":
            img = img.filter(ImageFilter.SHARPEN)
        elif self.filter_type == "EDGE":
            img = img.filter(ImageFilter.FIND_EDGES)
        return img

    def run_pathonet(self, model_type):
        if not self.original_image:
            messagebox.showwarning("Sin imagen", "Por favor cargue una imagen primero.")
            return
        if not messagebox.askyesno("Confirmar Auto-Conteo",
                                  "Esto limpiará todos los marcadores actuales y los reemplazará con los resultados simulados. ¿Desea continuar?"):
            return
        self.status_bar.config(text="Ejecutando simulación de Auto-Conteo...")
        self.root.update_idletasks()
        self.root.after(1500, lambda: self.simulate_pathonet_results(model_type))

    def simulate_pathonet_results(self, model_type):
        self.clear_markers()
        img_width, img_height = self.original_image.size
        if model_type == "ki67":
            for _ in range(np.random.randint(100, 300)):
                self.add_marker(np.random.randint(0.05 * img_width, 0.95 * img_width),
                               np.random.randint(0.05 * img_height, 0.95 * img_height), 'ki67')
            for _ in range(np.random.randint(300, 600)):
                self.add_marker(np.random.randint(0.05 * img_width, 0.95 * img_width),
                               np.random.randint(0.05 * img_height, 0.95 * img_height), 'negative')
            for _ in range(np.random.randint(5, 15)):
                self.add_marker(np.random.randint(0.05 * img_width, 0.95 * img_width),
                               np.random.randint(0.05 * img_height, 0.95 * img_height), 'mitosis')
        elif model_type == "mitosis":
            for _ in range(np.random.randint(50, 150)):
                self.add_marker(np.random.randint(0.05 * img_width, 0.95 * img_width),
                               np.random.randint(0.05 * img_height, 0.95 * img_height), 'ki67')
            for _ in range(np.random.randint(100, 300)):
                self.add_marker(np.random.randint(0.05 * img_width, 0.95 * img_width),
                               np.random.randint(0.05 * img_height, 0.95 * img_height), 'negative')
            for _ in range(np.random.randint(20, 50)):
                self.add_marker(np.random.randint(0.05 * img_width, 0.95 * img_width),
                               np.random.randint(0.05 * img_height, 0.95 * img_height), 'mitosis')
        self.action_history = []
        total_detected = len(self.ki67_points) + len(self.mitosis_points) + len(self.negative_points)
        self.status_bar.config(text=f"Simulación completada: {total_detected} núcleos detectados.")
        messagebox.showinfo("Auto-Conteo Completado",
                           f"La simulación de PathoNet ha finalizado, detectando {total_detected} núcleos.\n\n"
                           f"Modelo usado: {'Ki-67 IHC' if model_type == 'ki67' else 'H&E Mitosis'}")

    def calculate_metrics(self):
        total_ki67 = len(self.ki67_points)
        total_mitosis = len(self.mitosis_points)
        total_negative = len(self.negative_points)
        total_nuclei = total_ki67 + total_mitosis + total_negative
        if total_nuclei == 0:
            messagebox.showwarning("Sin Datos", "No hay marcadores para calcular métricas.")
            return
        ki67_base_count = total_ki67 + total_negative
        ki67_index = (total_ki67 / ki67_base_count) * 100 if ki67_base_count > 0 else 0
        img_width, img_height = self.original_image.size
        area_mm2 = (img_width * self.calibration_scale) * (img_height * self.calibration_scale) / 1e6
        mitosis_per_mm2 = total_mitosis / area_mm2 if area_mm2 > 0 else 0
        result_window = tk.Toplevel(self.root)
        result_window.title("Resultados del Análisis")
        result_window.geometry("600x600")
        result_window.transient(self.root)
        result_window.grab_set()
        notebook = ttk.Notebook(result_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        summary_frame = ttk.Frame(notebook, padding=10)
        notebook.add(summary_frame, text="Resumen")
        metrics = [
            ("Núcleos Ki-67 (+)", total_ki67),
            ("Núcleos Negativos (-)", total_negative),
            ("Figuras de Mitosis", total_mitosis),
            ("Total de Marcadores", total_nuclei),
            ("Índice de Proliferación Ki-67", f"{ki67_index:.2f}%"),
            ("Conteo Mitótico", f"{mitosis_per_mm2:.2f} mitosis/mm²"),
            ("Área Analizada", f"{area_mm2:.2f} mm²"),
            ("Escala", f"{self.calibration_scale:.4f} µm/pixel"),
            ("Nombre del Proyecto", self.current_project_name.get())
        ]
        for i, (label, value) in enumerate(metrics):
            ttk.Label(summary_frame, text=label, font=("Segoe UI", 10, "bold")).grid(row=i, column=0, sticky=tk.W, pady=2)
            ttk.Label(summary_frame, text=str(value), font=("Segoe UI", 10)).grid(row=i, column=1, sticky=tk.W, pady=2, padx=10)
        if total_nuclei > 0:
            hist_frame = ttk.Frame(notebook, padding=10)
            notebook.add(hist_frame, text="Distribución")
            fig = plt.Figure(figsize=(5, 4), dpi=100)
            ax = fig.add_subplot(111)
            categories = ['Ki-67 (+)', 'Negativo (-)', 'Mitosis']
            counts = [total_ki67, total_negative, total_mitosis]
            ax.bar(categories, counts, color=[
                self.ki67_color.get(),
                self.negative_color.get(),
                self.mitosis_color.get()
            ])
            ax.set_title('Distribución de Núcleos Identificados')
            ax.set_ylabel('Cantidad')
            canvas = FigureCanvasTkAgg(fig, master=hist_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        export_frame = ttk.Frame(result_window)
        export_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(export_frame, text="Exportar a CSV",
                  command=lambda: self.export_metrics_to_csv(metrics)).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="Copiar al Portapapeles",
                  command=lambda: self.copy_metrics_to_clipboard(metrics)).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="Cerrar",
                  command=result_window.destroy).pack(side=tk.RIGHT, padx=5)
        self.status_bar.config(text="Métricas calculadas.")

    def export_metrics_to_csv(self, metrics):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Todos los archivos", "*.*")]
        )
        if not file_path:
            return
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("Métrica,Valor\n")
                for label, value in metrics:
                    f.write(f"{label},{value}\n")
            self.status_bar.config(text=f"Métricas exportadas a: {file_path}")
            messagebox.showinfo("Exportación Exitosa", "Las métricas se exportaron correctamente a formato CSV.")
        except Exception as e:
            messagebox.showerror("Error de Exportación", f"No se pudo exportar el archivo CSV:\n{str(e)}")

    def copy_metrics_to_clipboard(self, metrics):
        text = "Métrica\tValor\n"
        for label, value in metrics:
            text += f"{label}\t{value}\n"
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_bar.config(text="Métricas copiadas al portapapeles")

    def load_recent_projects(self):
        self.recent_projects = []
        try:
            if os.path.exists("recent_projects.json"):
                with open("recent_projects.json", "r") as f:
                    self.recent_projects = json.load(f)
        except:
            pass
        self.update_recent_menu()

    def update_recent_menu(self):
        self.recent_menu.delete(0, tk.END)
        if not self.recent_projects:
            self.recent_menu.add_command(label="No hay proyectos recientes", state=tk.DISABLED)
            return
        for i, project in enumerate(self.recent_projects[:10]):
            name = os.path.basename(project['path'])
            if project['type'] == 'project':
                display = f"{i+1}. {name} [Proyecto]"
            elif project['type'] == 'annotation':
                display = f"{i+1}. {name} [Anotaciones]"
            else:
                display = f"{i+1}. {name} [Imagen]"
            self.recent_menu.add_command(
                label=display,
                command=lambda p=project['path'], t=project['type']: self.open_recent(p, t)
            )

    def add_to_recent(self, path, is_image=True):
        ext = os.path.splitext(path)[1].lower()
        if ext == '.hpa':
            project_type = 'project'
        elif ext == '.json':
            project_type = 'annotation'
        else:
            project_type = 'image'
        self.recent_projects = [p for p in self.recent_projects if p['path'] != path]
        self.recent_projects.insert(0, {
            'path': path,
            'type': project_type,
            'timestamp': datetime.now().isoformat()
        })
        try:
            with open("recent_projects.json", "w") as f:
                json.dump(self.recent_projects, f)
        except:
            pass
        self.update_recent_menu()

    def open_recent(self, path, project_type):
        if project_type == 'project':
            try:
                with open(path, 'r') as f:
                    project_data = json.load(f)
                image_path = project_data.get("image_path")
                if not image_path or not os.path.exists(image_path):
                    image_path = filedialog.askopenfilename(
                        title="Seleccione la imagen del proyecto (no encontrada)",
                        filetypes=[("Imágenes", "*.tif *.tiff *.jpg *.jpeg *.png *.svs"), ("Todos los archivos", "*.*")]
                    )
                    if not image_path:
                        return
                self.image_path = image_path
                self.original_image = Image.open(self.image_path)
                if self.original_image.mode == 'RGBA':
                    self.original_image = self.original_image.convert('RGB')
                self.clear_markers()
                self.zoom_factor = 1.0
                self.pan_x = 0
                self.pan_y = 0
                self.rotation_angle = project_data.get("rotation", 0)
                self.flip_horizontal = project_data.get("flip_h", False)
                self.flip_vertical = project_data.get("flip_v", False)
                self.brightness_factor = project_data.get("brightness", 1.0)
                self.contrast_factor = project_data.get("contrast", 1.0)
                self.gamma_factor = project_data.get("gamma", 1.0)
                self.filter_type = project_data.get("filter", "NONE")
                self.display_image = self.original_image.copy()
                self.apply_all_transforms()
                self.calibration_scale = project_data.get("calibration_scale", 0.25)
                self.current_project_name.set(project_data.get("project_name", "Sin título"))
                self.scale_label.config(text=f"Escala: {self.calibration_scale:.4f} µm/pixel")
                annotations = project_data.get("annotations", [])
                label_map = {
                    1: self.ki67_points,
                    2: self.negative_points,
                    3: self.mitosis_points
                }
                for ann in annotations:
                    x, y, label_id = ann.get('x'), ann.get('y'), ann.get('label_id')
                    if x is not None and y is not None and label_id in label_map:
                        label_map[label_id].append((x, y, None))
                self.display_image_on_canvas(fit_to_screen=True)
                self.update_all_counts()
                self.redraw_markers()
                self.show_image_info()
                self.status_bar.config(text=f"Proyecto reciente cargado: {os.path.basename(path)}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar el proyecto:\n{str(e)}")
                self.recent_projects = [p for p in self.recent_projects if p['path'] != path]
                self.update_recent_menu()
        elif project_type == 'annotation':
            self.load_annotations_file(path)
        else:
            self.open_image_file(path)

    def load_annotations_file(self, path):
        if not self.original_image:
            messagebox.showwarning("Sin Imagen", "Por favor, cargue una imagen antes de cargar anotaciones.")
            return
        try:
            with open(path, 'r') as f:
                annotations = json.load(f)
            if not isinstance(annotations, list):
                raise ValueError("El archivo JSON debe contener una lista de anotaciones.")
            self.clear_markers()
            label_map = {
                1: self.ki67_points,
                2: self.negative_points,
                3: self.mitosis_points
            }
            for ann in annotations:
                x, y, label_id = ann.get('x'), ann.get('y'), ann.get('label_id')
                if x is not None and y is not None and label_id in label_map:
                    label_map[label_id].append((x, y, None))
            self.update_all_counts()
            self.redraw_markers()
            self.status_bar.config(text=f"Anotaciones recientes cargadas: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar las anotaciones:\n{str(e)}")
            self.recent_projects = [p for p in self.recent_projects if p['path'] != path]
            self.update_recent_menu()

    def open_image_file(self, path):
        try:
            self.image_path = path
            self.original_image = Image.open(self.image_path)
            self.clear_markers()
            self.zoom_factor = 1.0
            self.pan_x = 0
            self.pan_y = 0
            self.rotation_angle = 0
            self.flip_horizontal = False
            self.flip_vertical = False
            self.filter_type = "NONE"
            self.brightness_factor = 1.0
            self.contrast_factor = 1.0
            self.gamma_factor = 1.0
            if self.original_image.mode == 'RGBA':
                self.original_image = self.original_image.convert('RGB')
            self.display_image = self.original_image.copy()
            self.current_project_name.set(os.path.splitext(os.path.basename(path))[0])
            self.show_image_info()
            self.display_image_on_canvas(fit_to_screen=True)
            self.status_bar.config(text=f"Imagen reciente cargada: {os.path.basename(path)}")
            self.add_to_recent(path)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la imagen:\n{str(e)}")
            self.recent_projects = [p for p in self.recent_projects if p['path'] != path]
            self.update_recent_menu()

    def show_documentation(self):
        doc_url = "https://github.com/HistoPathAnalyst/docs"
        webbrowser.open(doc_url)
        self.status_bar.config(text="Documentación abierta en navegador")

    def show_quick_tutorial(self):
        tutorial = (
            "HistoPath Analyst - Tutorial Rápido\n\n"
            "1. Cargar una imagen (Archivo > Abrir imagen, Ctrl+O)\n"
            "2. Usar las herramientas de anotación (F2-F5) para marcar núcleos\n"
            "3. Calibrar la escala si es necesario (Herramientas > Calibrar Escala)\n"
            "4. Usar conteo automático (Herramientas > Conteo Automático)\n"
            "5. Calcular métricas (Archivo > Exportar Métricas)\n"
            "6. Guardar proyecto (Ctrl+S) o anotaciones (Ctrl+J)\n\n"
            "Atajos de teclado:\n"
            "Ctrl+N: Nuevo proyecto\n"
            "Ctrl+O: Abrir imagen\n"
            "Ctrl+S: Guardar proyecto\n"
            "Ctrl+J: Guardar anotaciones\n"
            "Ctrl+Z: Deshacer\n"
            "Ctrl+Y: Rehacer\n"
            "Ctrl++: Zoom in\n"
            "Ctrl+-: Zoom out\n"
            "F1: Mostrar este tutorial\n"
            "F2: Herramienta Ki-67 (+)\n"
            "F3: Herramienta Mitosis\n"
            "F4: Herramienta Negativo (-)\n"
            "F5: Herramienta Goma de Borrar"
        )
        messagebox.showinfo("Tutorial Rápido", tutorial, parent=self.root)

    def check_for_updates(self):
        messagebox.showinfo("Actualizaciones",
                          "HistoPath Analyst v0.6 es la versión más reciente.\n"
                          "Las actualizaciones se notificarán automáticamente cuando estén disponibles.",
                          parent=self.root)

    def show_about(self):
        about_text = (
            "HistoPath Analyst v0.6\n\n"
            "Herramienta soporte para el análisis cuantitativo en histopatología digital.\n"
            "Desarrollado para la optimización y estandarización de diagnósticos.\n\n"
            "Características principales:\n"
            "- Anotación precisa de núcleos celulares\n"
            "- Cálculo de índices de proliferación\n"
            "- Conteo de figuras mitóticas\n"
            "- Herramientas avanzadas de edición de imágenes\n"
            "- Modelos de IA simulados para análisis automatizado\n"
            "- Exportación de métricas y resultados\n"
            "- Interfaz optimizada para patólogos\n\n"
            "© 2025-2026 FECORO\n"
            "Colaboración: Universidad de O'Higgins, AGENs-Lab\n"
            "Colaboración: Hospital Dr. Franco Ravera Zunino\n\n"
            "Licencia: GPLv3"
        )
        messagebox.showinfo("Acerca de HistoPath Analyst", about_text, parent=self.root)

if __name__ == "__main__":
    root = tk.Tk()
    app = HistoPathAnalyst(root)
    root.mainloop()
