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
from matplotlib.colors import LinearSegmentedColormap
import webbrowser
import uuid
from scipy import ndimage
from scipy.spatial import distance
from scipy.cluster.vq import kmeans, vq
import pandas as pd
from math import sqrt
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from collections import Counter

class HistoPathAnalyst:
    def __init__(self, root):
        self.root = root
        self.root.title("FECORO | HistoPath Analyst v1.1")
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
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.pan_x = 0
        self.pan_y = 0
        self.is_panning = False
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
        self.mitosis_color = tk.StringVar(value="#4dff4d")
        self.negative_color = tk.StringVar(value="#4d4dff")
        self.calibration_scale = 0.25  # µm/pixel
        self.current_project_name = tk.StringVar(value="Sin título")
        self.marker_size = tk.IntVar(value=8)
        self.show_scale_bar = tk.BooleanVar(value=True)
        self.show_markers = tk.BooleanVar(value=True)
        self.auto_save = tk.BooleanVar(value=False)
        self.last_save_path = None

        # Crear interfaz
        self.create_menu()
        self.create_widgets()
        self.update_color_buttons()
        self.create_shortcuts()
        self.load_recent_projects()

        # Inicializar estado del zoom
        self.zoom_state = "fit"  # fit, 100, custom

    def create_menu(self):
        menubar = tk.Menu(self.root)

        # Menú Archivo
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

        # Menú Editar
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Deshacer", command=self.undo_last_action, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Rehacer", command=self.redo_action, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Limpiar Todos los Marcadores", command=self.clear_markers)
        edit_menu.add_command(label="Seleccionar Región", command=self.select_region)
        menubar.add_cascade(label="Editar", menu=edit_menu)

        # Menú Imagen
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
        filter_menu.add_command(label="Filtro Gaussiano", command=lambda: self.apply_filter("GAUSSIAN"))
        filter_menu.add_command(label="Realce de Bordes", command=lambda: self.apply_filter("EDGE_ENHANCE"))
        image_menu.add_cascade(label="Filtros", menu=filter_menu)
        image_menu.add_command(label="Restablecer Imagen", command=self.reset_image)
        menubar.add_cascade(label="Imagen", menu=image_menu)

        # Menú Herramientas
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Calibrar Escala", command=self.calibrate_scale)
        tools_menu.add_command(label="Conteo Automático (Ki-67 IHC)", command=lambda: self.run_pathonet("ki67"))
        tools_menu.add_command(label="Conteo Automático (H&E Mitosis)", command=lambda: self.run_pathonet("mitosis"))
        tools_menu.add_separator()
        tools_menu.add_command(label="Análisis de Densidad", command=self.analyze_density)
        tools_menu.add_command(label="Análisis de Distribución", command=self.analyze_distribution)
        tools_menu.add_command(label="Análisis de Agrupamiento", command=self.analyze_clustering)
        tools_menu.add_command(label="Análisis de Color", command=self.analyze_color)
        menubar.add_cascade(label="Herramientas", menu=tools_menu)

        # Menú Vista
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_checkbutton(label="Mostrar Barra de Escala", variable=self.show_scale_bar,
                                 command=self.toggle_scale_bar)
        view_menu.add_checkbutton(label="Mostrar Marcadores", variable=self.show_markers,
                                 command=self.toggle_markers)
        view_menu.add_separator()
        view_menu.add_command(label="Zoom +", command=lambda: self.adjust_zoom(1.25), accelerator="Ctrl++")
        view_menu.add_command(label="Zoom -", command=lambda: self.adjust_zoom(0.8), accelerator="Ctrl+-")
        view_menu.add_command(label="Zoom 100%", command=self.zoom_100, accelerator="Ctrl+0")
        view_menu.add_command(label="Ajustar a Ventana", command=self.zoom_fit, accelerator="Ctrl+F")
        menubar.add_cascade(label="Vista", menu=view_menu)

        # Menú Ayuda
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
        self.root.bind("<Control-0>", lambda event: self.zoom_100())
        self.root.bind("<Control-f>", lambda event: self.zoom_fit())
        self.root.bind("<F1>", lambda event: self.show_quick_tutorial())
        self.root.bind("<F2>", lambda e: self.annotation_mode.set("ki67"))
        self.root.bind("<F3>", lambda e: self.annotation_mode.set("mitosis"))
        self.root.bind("<F4>", lambda e: self.annotation_mode.set("negative"))
        self.root.bind("<F5>", lambda e: self.annotation_mode.set("eraser"))
        self.root.bind("<F6>", lambda e: self.calculate_metrics())
        self.root.bind("<F7>", lambda e: self.analyze_density())
        self.root.bind("<F8>", lambda e: self.analyze_color())

        # Bindings para pan con teclado
        self.root.bind("<Left>", lambda e: self.pan_image(10, 0))
        self.root.bind("<Right>", lambda e: self.pan_image(-10, 0))
        self.root.bind("<Up>", lambda e: self.pan_image(0, 10))
        self.root.bind("<Down>", lambda e: self.pan_image(0, -10))

    def create_widgets(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # --- Panel izquierdo (controles) con scrollbar ---
        control_canvas = tk.Canvas(main_frame, width=350, bg=self.light_bg, highlightthickness=0)
        control_canvas.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        v_scroll = ttk.Scrollbar(main_frame, orient="vertical", command=control_canvas.yview)
        v_scroll.pack(side=tk.LEFT, fill=tk.Y)
        control_canvas.configure(yscrollcommand=v_scroll.set)

        control_frame = ttk.Frame(control_canvas, style="TFrame")
        control_canvas.create_window((0, 0), window=control_frame, anchor="nw", width=350)

        control_frame.bind("<Configure>", lambda e: control_canvas.configure(scrollregion=control_canvas.bbox("all")))
        control_canvas.bind_all("<MouseWheel>", lambda e: control_canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        # --- Project Name ---
        project_lf = ttk.LabelFrame(control_frame, text="Proyecto", padding=(10, 5))
        project_lf.pack(fill=tk.X, pady=5)
        ttk.Label(project_lf, text="Nombre:").pack(anchor=tk.W, pady=2)
        ttk.Entry(project_lf, textvariable=self.current_project_name, width=30).pack(fill=tk.X, pady=2)

        # --- Configuración de Marcadores ---
        marker_config_lf = ttk.LabelFrame(control_frame, text="Configuración de Marcadores", padding=(10, 5))
        marker_config_lf.pack(fill=tk.X, pady=5)
        ttk.Label(marker_config_lf, text="Tamaño de Marcadores:").pack(anchor=tk.W, pady=2)
        ttk.Scale(marker_config_lf, from_=4, to=20, variable=self.marker_size,
                 orient=tk.HORIZONTAL, command=self.on_marker_size_change).pack(fill=tk.X, pady=2)
        ttk.Checkbutton(marker_config_lf, text="Mostrar Marcadores", variable=self.show_markers,
                       command=self.toggle_markers).pack(anchor=tk.W, pady=2)

        # --- Herramientas de Anotación ---
        tools_lf = ttk.LabelFrame(control_frame, text="Herramientas de Anotación", padding=(10, 5))
        tools_lf.pack(fill=tk.X, pady=5)
        tool_frame = ttk.Frame(tools_lf)
        tool_frame.pack(fill=tk.X)
        ttk.Radiobutton(tool_frame, text="Ki-67 Positivo (+) [F2]", variable=self.annotation_mode,
                        value="ki67", style="Tool.TRadiobutton").pack(anchor=tk.W, fill=tk.X, pady=2)
        ttk.Radiobutton(tool_frame, text="Ki-67 Negativo (-) [F4]", variable=self.annotation_mode,
                        value="negative", style="Tool.TRadiobutton").pack(anchor=tk.W, fill=tk.X, pady=2)
        ttk.Radiobutton(tool_frame, text="Infiltrante (TIL) [F3]", variable=self.annotation_mode,
                        value="mitosis", style="Tool.TRadiobutton").pack(anchor=tk.W, fill=tk.X, pady=2)
        ttk.Radiobutton(tool_frame, text="Goma de Borrar [F5]", variable=self.annotation_mode,
                        value="eraser", style="Tool.TRadiobutton").pack(anchor=tk.W, fill=tk.X, pady=2)

        # --- Contadores ---
        counter_lf = ttk.LabelFrame(control_frame, text="Contadores", padding=(10, 5))
        counter_lf.pack(fill=tk.X, pady=5)
        self.ki67_count_label = ttk.Label(counter_lf, text="Ki-67 Positivo (+): 0",
                                         font=("Segoe UI", 10, "bold"), foreground=self.ki67_color.get())
        self.ki67_count_label.pack(anchor=tk.W, pady=2)
        self.mitosis_count_label = ttk.Label(counter_lf, text="Infiltrante (TIL): 0",
                                            font=("Segoe UI", 10, "bold"), foreground=self.mitosis_color.get())
        self.mitosis_count_label.pack(anchor=tk.W, pady=2)
        self.negative_count_label = ttk.Label(counter_lf, text="Ki-67 Negativo (-): 0",
                                             font=("Segoe UI", 10, "bold"), foreground=self.negative_color.get())
        self.negative_count_label.pack(anchor=tk.W, pady=2)
        self.total_count = ttk.Label(counter_lf, text="Total: 0",
                                    font=("Segoe UI", 10, "bold"), foreground=self.primary_color)
        self.total_count.pack(anchor=tk.W, pady=(5, 0))

        # --- Métricas Rápidas ---
        metrics_lf = ttk.LabelFrame(control_frame, text="Métricas Rápidas", padding=(10, 5))
        metrics_lf.pack(fill=tk.X, pady=5)
        self.density_label = ttk.Label(metrics_lf, text="Densidad: -- núcleos/mm²", font=("Segoe UI", 9))
        self.density_label.pack(anchor=tk.W, pady=1)
        self.ki67_index_label = ttk.Label(metrics_lf, text="Índice Ki-67: --%", font=("Segoe UI", 9))
        self.ki67_index_label.pack(anchor=tk.W, pady=1)
        self.mitotic_count_label = ttk.Label(metrics_lf, text="Conteo TIL: -- citos/mm²", font=("Segoe UI", 9))
        self.mitotic_count_label.pack(anchor=tk.W, pady=1)
        ttk.Button(metrics_lf, text="Calcular Todas las Métricas [F6]",
                  command=self.calculate_metrics).pack(fill=tk.X, pady=5)
        ttk.Button(metrics_lf, text="Análisis de Color [F8]",
                  command=self.analyze_color).pack(fill=tk.X, pady=2)

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
        ttk.Button(actions_lf, text="Seleccionar Región", command=self.select_region).pack(fill=tk.X, pady=2)

        # --- Personalización ---
        custom_lf = ttk.LabelFrame(control_frame, text="Personalización", padding=(10, 5))
        custom_lf.pack(fill=tk.X, pady=5)
        self.ki67_color_btn = ttk.Button(custom_lf, text="Color Ki-67",
                                         command=lambda: self.change_color('ki67'))
        self.ki67_color_btn.pack(fill=tk.X, pady=2)
        self.negative_color_btn = ttk.Button(custom_lf, text="Color Negativo",
                                            command=lambda: self.change_color('negative'))
        self.negative_color_btn.pack(fill=tk.X, pady=2)
        self.mitosis_color_btn = ttk.Button(custom_lf, text="Color TIL",
                                           command=lambda: self.change_color('mitosis'))
        self.mitosis_color_btn.pack(fill=tk.X, pady=2)

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
        ttk.Checkbutton(zoom_lf, text="Mostrar Barra de Escala", variable=self.show_scale_bar,
                       command=self.toggle_scale_bar).pack(anchor=tk.W, pady=2)

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

        # Frame para el canvas con scrollbars
        self.canvas_frame = ttk.Frame(vis_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas para la imagen
        self.canvas = tk.Canvas(self.canvas_frame, bg="#2c3e50", cursor="cross")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbars
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
        self.canvas.bind("<ButtonRelease-2>", self.end_pan)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)  # Windows
        self.canvas.bind("<Button-4>", self.on_mouse_wheel_linux)  # Linux zoom in
        self.canvas.bind("<Button-5>", self.on_mouse_wheel_linux)  # Linux zoom out
        self.canvas.bind("<Motion>", self.update_mouse_coords)
        self.canvas.bind("<Configure>", self.on_canvas_configure)

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
            "ki67": "Ki-67 Positivo (+)",
            "mitosis": "Infiltrante (TIL)",
            "negative": "Ki-67 Negativo (-)",
            "eraser": "Goma de Borrar"
        }
        self.tool_label.config(text=f"Herramienta: {tool_text[self.annotation_mode.get()]}")

    def on_canvas_configure(self, event):
        """Redibuja la imagen cuando el canvas cambia de tamaño"""
        if self.tk_image:
            self.display_image_on_canvas()

    def on_marker_size_change(self, value):
        """Actualiza el tamaño de los marcadores cuando se cambia el slider"""
        if self.original_image:
            self.redraw_markers()

    def toggle_scale_bar(self):
        """Muestra u oculta la barra de escala"""
        if self.show_scale_bar.get():
            self.draw_scale_bar()
        else:
            self.canvas.delete("scale_bar")

    def toggle_markers(self):
        """Muestra u oculta los marcadores"""
        if self.show_markers.get():
            self.redraw_markers()
        else:
            self.canvas.delete("marker")

    def pan_image(self, dx, dy):
        """Desplaza la imagen con las teclas de flecha"""
        if self.original_image:
            self.pan_x += dx
            self.pan_y += dy
            self.display_image_on_canvas()

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
            self.update_quick_metrics()

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
            self.zoom_fit()
            self.status_bar.config(text=f"Imagen cargada: {os.path.basename(file_path)}")
            self.add_to_recent(file_path)
            self.update_quick_metrics()
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
            self.zoom_fit()
            self.update_all_counts()
            self.redraw_markers()
            self.show_image_info()
            self.status_bar.config(text=f"Proyecto cargado: {os.path.basename(file_path)}")
            self.add_to_recent(file_path, is_image=False)
            self.update_quick_metrics()
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
            self.update_quick_metrics()
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
                "marker_size": self.marker_size.get(),
                "annotations": all_annotations,
                "timestamp": datetime.now().isoformat()
            }
            with open(file_path, 'w') as f:
                json.dump(project_data, f, indent=4)
            self.last_save_path = file_path
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
            radius = max(8, self.marker_size.get())
            width = max(2, int(radius / 4))

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

        # Obtener dimensiones del canvas
        canvas_width = max(1, self.canvas.winfo_width())
        canvas_height = max(1, self.canvas.winfo_height())

        # Aplicar transformaciones a la imagen
        img_to_display = self.apply_transforms_to_image(self.display_image)
        img_width, img_height = img_to_display.size

        if fit_to_screen:
            # Calcular zoom para ajustar a la pantalla
            x_ratio = canvas_width / img_width
            y_ratio = canvas_height / img_height
            self.zoom_factor = min(x_ratio, y_ratio, 1.0)  # No hacer zoom más allá del 100% al ajustar
            self.pan_x = (canvas_width - img_width * self.zoom_factor) / 2
            self.pan_y = (canvas_height - img_height * self.zoom_factor) / 2
            self.zoom_state = "fit"

        # Asegurar que el zoom esté dentro de límites razonables
        self.zoom_factor = max(0.01, min(self.zoom_factor, 20.0))

        # Calcular nuevas dimensiones
        new_width = max(1, int(img_width * self.zoom_factor))
        new_height = max(1, int(img_height * self.zoom_factor))

        # Redimensionar imagen para display
        display_img = img_to_display.resize((new_width, new_height), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(display_img)

        # Limpiar canvas y mostrar imagen
        self.canvas.delete("all")
        self.canvas.create_image(self.pan_x, self.pan_y, anchor=tk.NW, image=self.tk_image, tags="image")

        # Configurar región de scroll
        self.canvas.config(scrollregion=(0, 0, new_width, new_height))

        # Redibujar elementos
        if self.show_markers.get():
            self.redraw_markers()
        if self.show_scale_bar.get():
            self.draw_scale_bar()

        self.update_zoom_label()

    def redraw_markers(self):
        if not self.display_image or not self.original_image:
            return

        self.canvas.delete("marker")

        if not self.show_markers.get():
            return

        # Calcular factores de escala
        scale_x = self.display_image.width / self.original_image.width
        scale_y = self.display_image.height / self.original_image.height

        # Radio dinámico basado en zoom y tamaño configurado
        base_radius = self.marker_size.get()
        radius = max(3, min(20, int(base_radius / self.zoom_factor)))

        for points_list, color, tag in [
            (self.ki67_points, self.ki67_color.get(), "ki67_marker"),
            (self.mitosis_points, self.mitosis_color.get(), "mitosis_marker"),
            (self.negative_points, self.negative_color.get(), "negative_marker")
        ]:
            for i, (x, y, _) in enumerate(points_list):
                # Convertir coordenadas originales a coordenadas de display
                display_x = x * self.zoom_factor * scale_x + self.pan_x
                display_y = y * self.zoom_factor * scale_y + self.pan_y

                # Crear marcador solo si están dentro del área visible
                if (0 <= display_x <= self.canvas.winfo_width() and
                    0 <= display_y <= self.canvas.winfo_height()):
                    marker_id = self.canvas.create_oval(
                        display_x - radius, display_y - radius,
                        display_x + radius, display_y + radius,
                        outline=color, width=2, tags=("marker", tag)
                    )
                    points_list[i] = (x, y, marker_id)

    def draw_scale_bar(self):
        if not self.original_image or self.zoom_factor < 0.01 or not self.show_scale_bar.get():
            return

        self.canvas.delete("scale_bar")

        # Determinar tamaño apropiado para la barra (en micrómetros)
        target_um = 100
        image_width_um = self.original_image.width * self.calibration_scale

        if image_width_um < 500:
            target_um = 50
        if image_width_um < 200:
            target_um = 20
        if image_width_um < 100:
            target_um = 10

        # Calcular longitud en píxeles
        length_px_orig = target_um / self.calibration_scale
        length_px_display = length_px_orig * self.zoom_factor

        # Posición en el canvas (esquina inferior derecha)
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        x0 = canvas_width - length_px_display - 20
        y0 = canvas_height - 30
        x1 = canvas_width - 20
        y1 = y0 + 4

        # Solo dibujar si la barra cabe
        if x0 > 10 and length_px_display > 10:
            # Barra principal
            self.canvas.create_rectangle(x0, y0, x1, y1, fill="white", outline="black", width=1, tags="scale_bar")

            # Texto
            self.canvas.create_text((x0 + x1) / 2, y0 - 10,
                                   text=f"{target_um} µm",
                                   fill="white", font=("Segoe UI", 10, "bold"),
                                   tags="scale_bar")

    def on_mouse_press(self, event):
        if not self.original_image:
            return

        # Convertir coordenadas del canvas a coordenadas de imagen
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        # Calcular coordenadas en la imagen original
        scale_x = self.display_image.width / self.original_image.width
        scale_y = self.display_image.height / self.original_image.height

        orig_x = (canvas_x - self.pan_x) / (self.zoom_factor * scale_x)
        orig_y = (canvas_y - self.pan_y) / (self.zoom_factor * scale_y)

        # Verificar que las coordenadas estén dentro de la imagen
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
        context_menu.add_separator()
        context_menu.add_command(label="Calcular Métricas", command=self.calculate_metrics)
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def start_pan(self, event):
        self.is_panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.canvas.config(cursor="fleur")

    def on_pan(self, event):
        if self.is_panning:
            dx = event.x - self.pan_start_x
            dy = event.y - self.pan_start_y
            self.pan_start_x = event.x
            self.pan_start_y = event.y

            self.pan_x += dx
            self.pan_y += dy

            self.display_image_on_canvas()

    def end_pan(self, event):
        self.is_panning = False
        self.canvas.config(cursor="cross")

    def on_mouse_wheel(self, event):
        # Zoom con rueda del mouse (Windows)
        if event.delta > 0:
            self.adjust_zoom_centered(1.25, event.x, event.y)
        else:
            self.adjust_zoom_centered(0.8, event.x, event.y)

    def on_mouse_wheel_linux(self, event):
        # Zoom con rueda del mouse (Linux)
        if event.num == 4:  # Scroll up
            self.adjust_zoom_centered(1.25, event.x, event.y)
        elif event.num == 5:  # Scroll down
            self.adjust_zoom_centered(0.8, event.x, event.y)

    def adjust_zoom_centered(self, factor, mouse_x, mouse_y):
        """Ajusta el zoom centrado en la posición del mouse"""
        if not self.original_image:
            return

        # Convertir coordenadas del mouse a coordenadas del canvas
        canvas_x = self.canvas.canvasx(mouse_x)
        canvas_y = self.canvas.canvasy(mouse_y)

        # Calcular coordenadas en la imagen original
        scale_x = self.display_image.width / self.original_image.width
        scale_y = self.display_image.height / self.original_image.height

        img_x = (canvas_x - self.pan_x) / (self.zoom_factor * scale_x)
        img_y = (canvas_y - self.pan_y) / (self.zoom_factor * scale_y)

        # Aplicar zoom
        old_zoom = self.zoom_factor
        self.zoom_factor *= factor
        self.zoom_factor = max(0.01, min(self.zoom_factor, 20.0))

        # Ajustar pan para mantener el punto bajo el mouse
        self.pan_x = canvas_x - img_x * self.zoom_factor * scale_x
        self.pan_y = canvas_y - img_y * self.zoom_factor * scale_y

        self.zoom_state = "custom"
        self.display_image_on_canvas()

    def adjust_zoom(self, factor):
        """Ajusta el zoom centrado en el centro de la imagen"""
        if not self.original_image:
            return

        canvas_center_x = self.canvas.winfo_width() / 2
        canvas_center_y = self.canvas.winfo_height() / 2

        self.adjust_zoom_centered(factor, canvas_center_x, canvas_center_y)

    def zoom_fit(self):
        """Ajusta la imagen para que quepa en la ventana"""
        if self.original_image:
            self.zoom_state = "fit"
            self.display_image_on_canvas(fit_to_screen=True)

    def zoom_100(self):
        """Muestra la imagen al 100%"""
        if self.original_image:
            self.zoom_factor = 1.0
            self.zoom_state = "100"

            # Centrar la imagen
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            scale_x = self.display_image.width / self.original_image.width
            scale_y = self.display_image.height / self.original_image.height

            img_display_width = self.original_image.width * self.zoom_factor * scale_x
            img_display_height = self.original_image.height * self.zoom_factor * scale_y

            self.pan_x = (canvas_width - img_display_width) / 2
            self.pan_y = (canvas_height - img_display_height) / 2

            self.display_image_on_canvas()

    def update_zoom_label(self):
        if self.original_image:
            zoom_percent = self.zoom_factor * 100
            state_text = {
                "fit": " (Ajustado)",
                "100": " (100%)",
                "custom": ""
            }.get(self.zoom_state, "")

            self.zoom_label.config(text=f"Zoom: {zoom_percent:.0f}%{state_text}")

    def add_marker(self, x, y, marker_type):
        point_data = (x, y, None)
        target_list = getattr(self, f"{marker_type}_points")
        target_list.append(point_data)
        self.action_history.append(('add', marker_type, point_data))
        self.redo_stack = []
        self.update_all_counts()
        if self.show_markers.get():
            self.redraw_markers()
        self.status_bar.config(text=f"Marcador '{marker_type}' añadido en ({int(x)}, {int(y)})")
        self.update_quick_metrics()

    def erase_marker_at(self, x, y):
        search_radius = 20 / self.zoom_factor  # Radio de búsqueda adaptativo
        closest_marker = None
        min_dist = float('inf')
        marker_list_ref = None
        marker_index = -1
        marker_type_str = ""

        for mtype, lst in [("ki67", self.ki67_points), ("mitosis", self.mitosis_points), ("negative", self.negative_points)]:
            for i, (px, py, cid) in enumerate(lst):
                dist = sqrt((x - px)**2 + (y - py)**2)
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
            self.update_quick_metrics()

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
        if self.show_markers.get():
            self.redraw_markers()
        self.update_quick_metrics()

    def redo_action(self):
        if not self.redo_stack:
            self.status_bar.config(text="Nada que rehacer.")
            return

        action, marker_type, data = self.redo_stack.pop()
        self.action_history.append((action, marker_type, data))

        if action == 'add':
            target_list = getattr(self, f"{marker_type}_points")
            target_list.append(data)
            self.status_bar.config(text=f"Rehecho: Añadir marcadores '{marker_type}'")
        elif action == 'delete':
            target_list = getattr(self, f"{marker_type}_points")
            for i, point in enumerate(target_list):
                if point[0] == data[0] and point[1] == data[1]:
                    del target_list[i]
                    break
            self.status_bar.config(text=f"Rehecho: Eliminar marcadores '{marker_type}'")

        self.update_all_counts()
        if self.show_markers.get():
            self.redraw_markers()
        self.update_quick_metrics()

    def update_mouse_coords(self, event):
        if self.original_image:
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)

            scale_x = self.display_image.width / self.original_image.width
            scale_y = self.display_image.height / self.original_image.height

            orig_x = (canvas_x - self.pan_x) / (self.zoom_factor * scale_x)
            orig_y = (canvas_y - self.pan_y) / (self.zoom_factor * scale_y)

            if 0 <= orig_x < self.original_image.width and 0 <= orig_y < self.original_image.height:
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
        self.update_quick_metrics()

    def update_all_counts(self):
        n_ki67 = len(self.ki67_points)
        n_mitosis = len(self.mitosis_points)
        n_negative = len(self.negative_points)
        self.ki67_count_label.config(text=f"Ki-67 (+): {n_ki67}")
        self.mitosis_count_label.config(text=f"Mitosis: {n_mitosis}")
        self.negative_count_label.config(text=f"Negativo (-): {n_negative}")
        self.total_count.config(text=f"Total: {n_ki67 + n_mitosis + n_negative}")

    def update_quick_metrics(self):
        """Actualiza las métricas rápidas en el panel lateral"""
        if not self.original_image:
            self.density_label.config(text="Densidad: -- núcleos/mm²")
            self.ki67_index_label.config(text="Índice Ki-67: --%")
            self.mitotic_count_label.config(text="Conteo Otros: -- citos/mm²")
            return

        total_ki67 = len(self.ki67_points)
        total_mitosis = len(self.mitosis_points)
        total_negative = len(self.negative_points)
        total_nuclei = total_ki67 + total_mitosis + total_negative

        # Calcular área en mm²
        img_width, img_height = self.original_image.size
        area_mm2 = (img_width * self.calibration_scale) * (img_height * self.calibration_scale) / 1e6

        if area_mm2 > 0:
            density = total_nuclei / area_mm2
            self.density_label.config(text=f"Densidad: {density:.1f} núcleos/mm²")

            mitotic_count = total_mitosis / area_mm2
            self.mitotic_count_label.config(text=f"Conteo Otros: {mitotic_count:.2f} citos/mm²")
        else:
            self.density_label.config(text="Densidad: -- núcleos/mm²")
            self.mitotic_count_label.config(text="Conteo Otros: -- citos/mm²")

        # Índice Ki-67
        ki67_base_count = total_ki67 + total_negative
        if ki67_base_count > 0:
            ki67_index = (total_ki67 / ki67_base_count) * 100
            self.ki67_index_label.config(text=f"Índice Ki-67: {ki67_index:.1f}%")
        else:
            self.ki67_index_label.config(text="Índice Ki-67: --%")

    def show_image_info(self):
        if self.original_image:
            width, height = self.original_image.size
            area_mm2 = (width * self.calibration_scale) * (height * self.calibration_scale) / 1e6

            info_text = f"Dimensiones: {width} × {height} px\n"
            info_text += f"Área: {area_mm2:.2f} mm²\n"
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
            if self.show_scale_bar.get():
                self.draw_scale_bar()
            self.update_quick_metrics()
            self.show_image_info()

    def change_color(self, marker_type):
        current_color = getattr(self, f"{marker_type}_color").get()
        new_color = colorchooser.askcolor(title=f"Elija el color para {marker_type}", initialcolor=current_color)
        if new_color and new_color[1]:
            color_var = getattr(self, f"{marker_type}_color")
            color_var.set(new_color[1])
            self.update_color_buttons()
            if self.show_markers.get():
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
        elif self.filter_type == "GAUSSIAN":
            img = img.filter(ImageFilter.GaussianBlur(radius=2))
        elif self.filter_type == "EDGE_ENHANCE":
            img = img.filter(ImageFilter.EDGE_ENHANCE)
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
        elif self.filter_type == "GAUSSIAN":
            img = img.filter(ImageFilter.GaussianBlur(radius=2))
        elif self.filter_type == "EDGE_ENHANCE":
            img = img.filter(ImageFilter.EDGE_ENHANCE)
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

        # Simular resultados más realistas basados en el tipo de modelo
        if model_type == "ki67":
            # Para Ki-67, más células positivas y negativas, pocas mitosis
            for _ in range(np.random.randint(80, 200)):
                self.add_marker(np.random.randint(0.05 * img_width, 0.95 * img_width),
                               np.random.randint(0.05 * img_height, 0.95 * img_height), 'ki67')
            for _ in range(np.random.randint(200, 400)):
                self.add_marker(np.random.randint(0.05 * img_width, 0.95 * img_width),
                               np.random.randint(0.05 * img_height, 0.95 * img_height), 'negative')
            for _ in range(np.random.randint(3, 8)):
                self.add_marker(np.random.randint(0.05 * img_width, 0.95 * img_width),
                               np.random.randint(0.05 * img_height, 0.95 * img_height), 'mitosis')
        elif model_type == "mitosis":
            # Para mitosis, más figuras mitóticas
            for _ in range(np.random.randint(30, 80)):
                self.add_marker(np.random.randint(0.05 * img_width, 0.95 * img_width),
                               np.random.randint(0.05 * img_height, 0.95 * img_height), 'ki67')
            for _ in range(np.random.randint(60, 150)):
                self.add_marker(np.random.randint(0.05 * img_width, 0.95 * img_width),
                               np.random.randint(0.05 * img_height, 0.95 * img_height), 'negative')
            for _ in range(np.random.randint(15, 40)):
                self.add_marker(np.random.randint(0.05 * img_width, 0.95 * img_width),
                               np.random.randint(0.05 * img_height, 0.95 * img_height), 'mitosis')

        self.action_history = []
        total_detected = len(self.ki67_points) + len(self.mitosis_points) + len(self.negative_points)
        self.status_bar.config(text=f"Simulación completada: {total_detected} núcleos detectados.")
        messagebox.showinfo("Auto-Conteo Completado",
                           f"La simulación de PathoNet ha finalizado, detectando {total_detected} núcleos.\n\n"
                           f"Modelo usado: {'Ki-67 IHC' if model_type == 'ki67' else 'H&E Mitosis'}")

    def calculate_metrics(self):
        """Calcula y muestra métricas detalladas"""
        if not self.original_image:
            messagebox.showwarning("Sin Imagen", "Por favor, cargue una imagen para calcular métricas.")
            return

        total_ki67 = len(self.ki67_points)
        total_mitosis = len(self.mitosis_points)
        total_negative = len(self.negative_points)
        total_nuclei = total_ki67 + total_mitosis + total_negative

        if total_nuclei == 0:
            messagebox.showwarning("Sin Datos", "No hay marcadores para calcular métricas.")
            return

        # Calcular área en mm²
        img_width, img_height = self.original_image.size
        area_mm2 = (img_width * self.calibration_scale) * (img_height * self.calibration_scale) / 1e6

        # Métricas básicas
        ki67_base_count = total_ki67 + total_negative
        ki67_index = (total_ki67 / ki67_base_count) * 100 if ki67_base_count > 0 else 0
        mitosis_per_mm2 = total_mitosis / area_mm2 if area_mm2 > 0 else 0
        density_total = total_nuclei / area_mm2 if area_mm2 > 0 else 0
        density_ki67 = total_ki67 / area_mm2 if area_mm2 > 0 else 0
        density_negative = total_negative / area_mm2 if area_mm2 > 0 else 0

        # Métricas avanzadas de distribución
        distribution_metrics = self.calculate_distribution_metrics()
        clustering_metrics = self.calculate_clustering_metrics()

        # Crear ventana de resultados
        result_window = tk.Toplevel(self.root)
        result_window.title("Resultados del Análisis - Métricas Detalladas")
        result_window.geometry("800x700")
        result_window.transient(self.root)
        result_window.grab_set()

        # Notebook para pestañas
        notebook = ttk.Notebook(result_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Pestaña de resumen
        summary_frame = ttk.Frame(notebook, padding=15)
        notebook.add(summary_frame, text="Resumen General")

        # Métricas básicas
        metrics_frame = ttk.LabelFrame(summary_frame, text="Métricas Básicas", padding=10)
        metrics_frame.pack(fill=tk.X, pady=5)

        metrics = [
            ("Núcleos Ki-67 (+)", f"{total_ki67}"),
            ("Núcleos Negativos (-)", f"{total_negative}"),
            ("Figuras Infiltrantes", f"{total_mitosis}"),
            ("Total de Núcleos", f"{total_nuclei}"),
            ("", ""),
            ("Índice de Proliferación Ki-67", f"{ki67_index:.2f}%"),
            ("Densidad Total", f"{density_total:.1f} núcleos/mm²"),
            ("Densidad Ki-67", f"{density_ki67:.1f} núcleos/mm²"),
            ("Densidad Negativos", f"{density_negative:.1f} núcleos/mm²"),
            ("Conteo TIL/Otros", f"{mitosis_per_mm2:.2f} mitosis/mm²"),
            ("", ""),
            ("Área Analizada", f"{area_mm2:.2f} mm²"),
            ("Escala", f"{self.calibration_scale:.4f} µm/pixel"),
            ("Resolución", f"{img_width} × {img_height} px")
        ]

        for i, (label, value) in enumerate(metrics):
            if label == "":
                ttk.Separator(metrics_frame, orient='horizontal').grid(row=i, column=0, columnspan=2, sticky='ew', pady=5)
            else:
                ttk.Label(metrics_frame, text=label, font=("Segoe UI", 9, "bold")).grid(row=i, column=0, sticky=tk.W, pady=2)
                ttk.Label(metrics_frame, text=value, font=("Segoe UI", 9)).grid(row=i, column=1, sticky=tk.W, pady=2, padx=10)

        # Pestaña de distribución
        if total_nuclei > 0:
            dist_frame = ttk.Frame(notebook, padding=10)
            notebook.add(dist_frame, text="Distribución")

            # Gráfico de distribución
            fig1 = plt.Figure(figsize=(6, 4), dpi=100)
            ax1 = fig1.add_subplot(111)
            categories = ['Ki-67 Positivo (+)', 'Ki-67 Negativo (-)', 'Otros']
            counts = [total_ki67, total_negative, total_mitosis]
            colors = [self.ki67_color.get(), self.negative_color.get(), self.mitosis_color.get()]
            bars = ax1.bar(categories, counts, color=colors)
            ax1.set_title('Distribución de Núcleos Identificados')
            ax1.set_ylabel('Cantidad')

            # Añadir valores en las barras
            for bar, count in zip(bars, counts):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{count}', ha='center', va='bottom')

            canvas1 = FigureCanvasTkAgg(fig1, master=dist_frame)
            canvas1.draw()
            canvas1.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            # Métricas de distribución
            dist_metrics_frame = ttk.LabelFrame(dist_frame, text="Métricas de Distribución", padding=10)
            dist_metrics_frame.pack(fill=tk.X, pady=10)

            dist_metrics = [
                ("Distancia Mínima entre Núcleos", f"{distribution_metrics['min_distance']:.1f} µm"),
                ("Distancia Máxima entre Núcleos", f"{distribution_metrics['max_distance']:.1f} µm"),
                ("Distancia Promedio entre Núcleos", f"{distribution_metrics['avg_distance']:.1f} µm"),
                ("Desviación Estándar de Distancias", f"{distribution_metrics['std_distance']:.1f} µm"),
                ("Coeficiente de Variación", f"{distribution_metrics['cv_distance']:.2f}"),
            ]

            for i, (label, value) in enumerate(dist_metrics):
                ttk.Label(dist_metrics_frame, text=label, font=("Segoe UI", 9)).grid(row=i, column=0, sticky=tk.W, pady=1)
                ttk.Label(dist_metrics_frame, text=value, font=("Segoe UI", 9, "bold")).grid(row=i, column=1, sticky=tk.W, pady=1, padx=10)

        # Pestaña de agrupamiento
        if total_nuclei > 10:  # Solo mostrar si hay suficientes puntos
            cluster_frame = ttk.Frame(notebook, padding=10)
            notebook.add(cluster_frame, text="Agrupamiento")

            # Gráfico de dispersión
            fig2 = plt.Figure(figsize=(6, 5), dpi=100)
            ax2 = fig2.add_subplot(111)

            # Preparar datos para el scatter plot
            all_points = []
            colors = []
            labels = []

            for points, color, label in [
                (self.ki67_points, self.ki67_color.get(), 'Ki-67 Positivo (+)'),
                (self.negative_points, self.negative_color.get(), 'Ki-67 Negativo (-)'),
                (self.mitosis_points, self.mitosis_color.get(), 'Otros')
            ]:
                for x, y, _ in points:
                    all_points.append([x * self.calibration_scale, y * self.calibration_scale])
                    colors.append(color)
                    labels.append(label)

            if all_points:
                points_array = np.array(all_points)
                ax2.scatter(points_array[:, 0], points_array[:, 1], c=colors, alpha=0.6, s=20)
                ax2.set_xlabel('Coordenada X (µm)')
                ax2.set_ylabel('Coordenada Y (µm)')
                ax2.set_title('Distribución Espacial de Núcleos')
                ax2.grid(True, alpha=0.3)

                # Añadir leyenda
                from matplotlib.patches import Patch
                legend_elements = [
                    Patch(facecolor=self.ki67_color.get(), label='Ki-67 Positivo (+)'),
                    Patch(facecolor=self.negative_color.get(), label='Ki-67 Negativo (-)'),
                    Patch(facecolor=self.mitosis_color.get(), label='Otros')
                ]
                ax2.legend(handles=legend_elements)

            canvas2 = FigureCanvasTkAgg(fig2, master=cluster_frame)
            canvas2.draw()
            canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            # Métricas de agrupamiento
            cluster_metrics_frame = ttk.LabelFrame(cluster_frame, text="Métricas de Agrupamiento", padding=10)
            cluster_metrics_frame.pack(fill=tk.X, pady=10)

            cluster_metrics = [
                ("Índice de Agrupamiento", f"{clustering_metrics['clustering_index']:.3f}"),
                ("Número de Grupos Detectados", f"{clustering_metrics['num_clusters']}"),
                ("Tamaño Promedio de Grupo", f"{clustering_metrics['avg_cluster_size']:.1f} núcleos"),
                ("Densidad de Grupos", f"{clustering_metrics['cluster_density']:.2f} grupos/mm²"),
            ]

            for i, (label, value) in enumerate(cluster_metrics):
                ttk.Label(cluster_metrics_frame, text=label, font=("Segoe UI", 9)).grid(row=i, column=0, sticky=tk.W, pady=1)
                ttk.Label(cluster_metrics_frame, text=value, font=("Segoe UI", 9, "bold")).grid(row=i, column=1, sticky=tk.W, pady=1, padx=10)

        # Botones de exportación
        export_frame = ttk.Frame(result_window)
        export_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(export_frame, text="Exportar a CSV",
                  command=lambda: self.export_metrics_to_csv(metrics, distribution_metrics, clustering_metrics)).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="Exportar Reporte PDF",
                  command=lambda: self.export_pdf_report(metrics, distribution_metrics, clustering_metrics)).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="Copiar al Portapapeles",
                  command=lambda: self.copy_metrics_to_clipboard(metrics)).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="Cerrar",
                  command=result_window.destroy).pack(side=tk.RIGHT, padx=5)

        self.status_bar.config(text="Métricas calculadas y mostradas.")

    def analyze_color(self):
        """Análisis avanzado de color de la imagen"""
        if not self.original_image:
            messagebox.showwarning("Sin Imagen", "Cargue una imagen primero.")
            return

        # Crear ventana de análisis de color
        color_window = tk.Toplevel(self.root)
        color_window.title("Análisis de Color - Distribución de Tinciones")
        color_window.geometry("1000x800")
        color_window.transient(self.root)
        color_window.grab_set()

        # Notebook para pestañas
        notebook = ttk.Notebook(color_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Pestaña 1: Diagrama de dispersión de colores
        scatter_frame = ttk.Frame(notebook, padding=10)
        notebook.add(scatter_frame, text="Diagrama de Colores")

        # Pestaña 2: Histogramas de color
        hist_frame = ttk.Frame(notebook, padding=10)
        notebook.add(hist_frame, text="Histogramas")

        # Pestaña 3: Paleta de colores dominantes
        palette_frame = ttk.Frame(notebook, padding=10)
        notebook.add(palette_frame, text="Paleta de Colores")

        # Pestaña 4: Análisis PCA de colores
        pca_frame = ttk.Frame(notebook, padding=10)
        notebook.add(pca_frame, text="Análisis PCA")

        # Convertir imagen a numpy array
        img_array = np.array(self.original_image)

        # Si la imagen tiene canal alpha, quitarlo
        if img_array.shape[2] == 4:
            img_array = img_array[:,:,:3]

        # Redimensionar imagen para análisis (para mejorar rendimiento)
        max_size = 500
        h, w = img_array.shape[:2]
        if max(h, w) > max_size:
            scale = max_size / max(h, w)
            new_h, new_w = int(h * scale), int(w * scale)
            img_resized = cv2.resize(img_array, (new_w, new_h))
        else:
            img_resized = img_array

        # Aplanar la imagen a una lista de píxeles
        pixels = img_resized.reshape(-1, 3)

        # Muestrear píxeles para análisis (máximo 10000 píxeles)
        n_samples = min(10000, len(pixels))
        indices = np.random.choice(len(pixels), n_samples, replace=False)
        sample_pixels = pixels[indices]

        # 1. Diagrama de dispersión de colores
        fig_scatter = plt.Figure(figsize=(8, 6), dpi=100)
        ax_scatter = fig_scatter.add_subplot(111, projection='3d')

        # Normalizar colores para visualización
        norm_pixels = sample_pixels / 255.0

        # Crear scatter plot 3D
        scatter = ax_scatter.scatter(
            sample_pixels[:, 0],  # Rojo
            sample_pixels[:, 1],  # Verde
            sample_pixels[:, 2],  # Azul
            c=norm_pixels,
            marker='o',
            alpha=0.6,
            s=10
        )

        ax_scatter.set_xlabel('Canal Rojo')
        ax_scatter.set_ylabel('Canal Verde')
        ax_scatter.set_zlabel('Canal Azul')
        ax_scatter.set_title('Espacio de Color RGB - Distribución de Píxeles')

        canvas_scatter = FigureCanvasTkAgg(fig_scatter, master=scatter_frame)
        canvas_scatter.draw()
        canvas_scatter.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 2. Histogramas de color
        fig_hist = plt.Figure(figsize=(10, 6), dpi=100)
        ax_hist1 = fig_hist.add_subplot(211)
        ax_hist2 = fig_hist.add_subplot(212)

        # Histograma RGB
        colors = ['red', 'green', 'blue']
        channels = ['Rojo', 'Verde', 'Azul']
        for i, color in enumerate(colors):
            ax_hist1.hist(sample_pixels[:, i], bins=50, alpha=0.7, color=color,
                         label=channels[i], density=True)
        ax_hist1.set_title('Distribución de Canales RGB')
        ax_hist1.set_xlabel('Intensidad')
        ax_hist1.set_ylabel('Densidad')
        ax_hist1.legend()
        ax_hist1.grid(True, alpha=0.3)

        # Convertir a HSV para análisis de tinción
        img_hsv = cv2.cvtColor(img_resized, cv2.COLOR_RGB2HSV)
        hsv_pixels = img_hsv.reshape(-1, 3)
        sample_hsv = hsv_pixels[indices]

        # Histograma HSV
        hsv_channels = ['Matiz (Hue)', 'Saturación (Sat)', 'Valor (Val)']
        hsv_colors = ['magenta', 'cyan', 'yellow']
        for i in range(3):
            ax_hist2.hist(sample_hsv[:, i], bins=50, alpha=0.7, color=hsv_colors[i],
                         label=hsv_channels[i], density=True)
        ax_hist2.set_title('Distribución de Canales HSV')
        ax_hist2.set_xlabel('Valor')
        ax_hist2.set_ylabel('Densidad')
        ax_hist2.legend()
        ax_hist2.grid(True, alpha=0.3)

        fig_hist.tight_layout()
        canvas_hist = FigureCanvasTkAgg(fig_hist, master=hist_frame)
        canvas_hist.draw()
        canvas_hist.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 3. Paleta de colores dominantes
        fig_palette = plt.Figure(figsize=(10, 4), dpi=100)
        ax_palette = fig_palette.add_subplot(111)

        # Encontrar colores dominantes usando k-means
        n_colors = 8
        kmeans = KMeans(n_clusters=n_colors, random_state=42)
        kmeans.fit(sample_pixels)
        dominant_colors = kmeans.cluster_centers_.astype(int)

        # Contar frecuencia de cada color
        labels = kmeans.labels_
        color_counts = Counter(labels)
        total_pixels = len(labels)

        # Crear paleta de colores
        palette = []
        color_info = []
        for i, color in enumerate(dominant_colors):
            count = color_counts[i]
            percentage = (count / total_pixels) * 100
            palette.append(color / 255.0)
            color_info.append(f"RGB{tuple(color)} ({percentage:.1f}%)")

        # Mostrar paleta
        ax_palette.imshow([palette], aspect='auto', extent=[0, n_colors, 0, 1])
        ax_palette.set_title(f'Paleta de {n_colors} Colores Dominantes')
        ax_palette.set_xlabel('Colores')
        ax_palette.set_ylabel('')
        ax_palette.set_yticks([])
        ax_palette.set_xticks(np.arange(n_colors) + 0.5)
        ax_palette.set_xticklabels([f'Color {i+1}' for i in range(n_colors)], rotation=45)

        # Añadir información de porcentajes
        for i, info in enumerate(color_info):
            ax_palette.text(i + 0.5, 0.5, f'{info.split("(")[1][:-1]}',
                          ha='center', va='center', fontsize=8,
                          bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

        canvas_palette = FigureCanvasTkAgg(fig_palette, master=palette_frame)
        canvas_palette.draw()
        canvas_palette.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 4. Análisis PCA de colores
        fig_pca = plt.Figure(figsize=(10, 8), dpi=100)
        ax_pca1 = fig_pca.add_subplot(221)
        ax_pca2 = fig_pca.add_subplot(222)
        ax_pca3 = fig_pca.add_subplot(223)
        ax_pca4 = fig_pca.add_subplot(224, projection='3d')

        # Aplicar PCA
        pca = PCA(n_components=3)
        pca_result = pca.fit_transform(sample_pixels)

        # Gráfico 2D - PC1 vs PC2
        scatter1 = ax_pca1.scatter(pca_result[:, 0], pca_result[:, 1],
                                 c=norm_pixels, alpha=0.6, s=10)
        ax_pca1.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.2%} var.)')
        ax_pca1.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.2%} var.)')
        ax_pca1.set_title('PCA: Componente 1 vs Componente 2')
        ax_pca1.grid(True, alpha=0.3)

        # Gráfico 2D - PC1 vs PC3
        scatter2 = ax_pca2.scatter(pca_result[:, 0], pca_result[:, 2],
                                 c=norm_pixels, alpha=0.6, s=10)
        ax_pca2.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.2%} var.)')
        ax_pca2.set_ylabel(f'PC3 ({pca.explained_variance_ratio_[2]:.2%} var.)')
        ax_pca2.set_title('PCA: Componente 1 vs Componente 3')
        ax_pca2.grid(True, alpha=0.3)

        # Gráfico 2D - PC2 vs PC3
        scatter3 = ax_pca3.scatter(pca_result[:, 1], pca_result[:, 2],
                                 c=norm_pixels, alpha=0.6, s=10)
        ax_pca3.set_xlabel(f'PC2 ({pca.explained_variance_ratio_[1]:.2%} var.)')
        ax_pca3.set_ylabel(f'PC3 ({pca.explained_variance_ratio_[2]:.2%} var.)')
        ax_pca3.set_title('PCA: Componente 2 vs Componente 3')
        ax_pca3.grid(True, alpha=0.3)

        # Gráfico 3D
        scatter4 = ax_pca4.scatter(pca_result[:, 0], pca_result[:, 1], pca_result[:, 2],
                                 c=norm_pixels, alpha=0.6, s=10)
        ax_pca4.set_xlabel('PC1')
        ax_pca4.set_ylabel('PC2')
        ax_pca4.set_zlabel('PC3')
        ax_pca4.set_title('PCA 3D - Espacio de Color Reducido')

        fig_pca.tight_layout()
        canvas_pca = FigureCanvasTkAgg(fig_pca, master=pca_frame)
        canvas_pca.draw()
        canvas_pca.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Información estadística
        stats_text = f"""
        ESTADÍSTICAS DE COLOR:
        - Total de píxeles analizados: {n_samples:,}
        - Dimensión original: {img_array.shape[1]} × {img_array.shape[0]} píxeles
        - Dimensión para análisis: {img_resized.shape[1]} × {img_resized.shape[0]} píxeles

        ANÁLISIS PCA:
        - Varianza explicada PC1: {pca.explained_variance_ratio_[0]:.2%}
        - Varianza explicada PC2: {pca.explained_variance_ratio_[1]:.2%}
        - Varianza explicada PC3: {pca.explained_variance_ratio_[2]:.2%}
        - Varianza total explicada: {sum(pca.explained_variance_ratio_):.2%}

        COLORES DOMINANTES:
        """

        for i, (color, info) in enumerate(zip(dominant_colors, color_info)):
            stats_text += f"- Color {i+1}: {info}\n"

        # Frame para estadísticas
        stats_frame = ttk.Frame(color_window)
        stats_frame.pack(fill=tk.X, padx=10, pady=5)

        stats_label = tk.Text(stats_frame, height=12, width=80, font=("Courier", 9))
        stats_label.insert(tk.END, stats_text)
        stats_label.config(state=tk.DISABLED)
        stats_label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Barra de scroll para el texto
        scrollbar = ttk.Scrollbar(stats_frame, command=stats_label.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        stats_label.config(yscrollcommand=scrollbar.set)

        # Botones de exportación
        export_frame = ttk.Frame(color_window)
        export_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(export_frame, text="Exportar Reporte de Color",
                  command=lambda: self.export_color_analysis(stats_text, dominant_colors)).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="Cerrar",
                  command=color_window.destroy).pack(side=tk.RIGHT, padx=5)

        self.status_bar.config(text="Análisis de color completado.")

    def export_color_analysis(self, stats_text, dominant_colors):
        """Exporta el análisis de color a un archivo de texto"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("REPORTE DE ANÁLISIS DE COLOR - HistoPath Analyst\n")
                f.write("=" * 60 + "\n\n")
                f.write(stats_text)
                f.write("\n\nVALORES RGB DE COLORES DOMINANTES:\n")
                for i, color in enumerate(dominant_colors):
                    f.write(f"Color {i+1}: R={color[0]}, G={color[1]}, B={color[2]}\n")

                f.write(f"\nGenerado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Proyecto: {self.current_project_name.get()}\n")

            self.status_bar.config(text=f"Reporte de color exportado: {file_path}")
            messagebox.showinfo("Exportación Exitosa", "El reporte de análisis de color se exportó correctamente.")
        except Exception as e:
            messagebox.showerror("Error de Exportación", f"No se pudo exportar el reporte:\n{str(e)}")

    def calculate_distribution_metrics(self):
        """Calcula métricas de distribución espacial"""
        all_points = []
        for points_list in [self.ki67_points, self.mitosis_points, self.negative_points]:
            for x, y, _ in points_list:
                all_points.append((x * self.calibration_scale, y * self.calibration_scale))

        if len(all_points) < 2:
            return {
                'min_distance': 0,
                'max_distance': 0,
                'avg_distance': 0,
                'std_distance': 0,
                'cv_distance': 0
            }

        # Calcular distancias entre todos los puntos
        distances = []
        for i in range(len(all_points)):
            for j in range(i + 1, len(all_points)):
                dist = sqrt((all_points[i][0] - all_points[j][0])**2 +
                           (all_points[i][1] - all_points[j][1])**2)
                distances.append(dist)

        if distances:
            return {
                'min_distance': min(distances),
                'max_distance': max(distances),
                'avg_distance': np.mean(distances),
                'std_distance': np.std(distances),
                'cv_distance': np.std(distances) / np.mean(distances) if np.mean(distances) > 0 else 0
            }
        else:
            return {
                'min_distance': 0,
                'max_distance': 0,
                'avg_distance': 0,
                'std_distance': 0,
                'cv_distance': 0
            }

    def calculate_clustering_metrics(self):
        """Calcula métricas de agrupamiento usando un algoritmo simple"""
        all_points = []
        for points_list in [self.ki67_points, self.mitosis_points, self.negative_points]:
            for x, y, _ in points_list:
                all_points.append([x * self.calibration_scale, y * self.calibration_scale])

        if len(all_points) < 3:
            return {
                'clustering_index': 0,
                'num_clusters': 0,
                'avg_cluster_size': 0,
                'cluster_density': 0
            }

        # Algoritmo simple de agrupamiento por distancia
        points_array = np.array(all_points)
        clusters = []
        visited = set()
        cluster_distance = 50  # µm - distancia máxima para considerar agrupamiento

        for i, point in enumerate(points_array):
            if i not in visited:
                cluster = [i]
                visited.add(i)
                queue = [i]

                while queue:
                    current = queue.pop(0)
                    for j, other_point in enumerate(points_array):
                        if j not in visited:
                            distance = np.linalg.norm(points_array[current] - other_point)
                            if distance < cluster_distance:
                                cluster.append(j)
                                visited.add(j)
                                queue.append(j)

                if len(cluster) > 1:  # Solo grupos con al menos 2 puntos
                    clusters.append(cluster)

        # Calcular métricas de agrupamiento
        if clusters:
            cluster_sizes = [len(cluster) for cluster in clusters]
            img_area_mm2 = (self.original_image.width * self.calibration_scale) * \
                          (self.original_image.height * self.calibration_scale) / 1e6

            return {
                'clustering_index': len(clusters) / len(all_points) if all_points else 0,
                'num_clusters': len(clusters),
                'avg_cluster_size': np.mean(cluster_sizes),
                'cluster_density': len(clusters) / img_area_mm2 if img_area_mm2 > 0 else 0
            }
        else:
            return {
                'clustering_index': 0,
                'num_clusters': 0,
                'avg_cluster_size': 0,
                'cluster_density': 0
            }

    def analyze_density(self):
        """Análisis avanzado de densidad"""
        if not self.original_image:
            messagebox.showwarning("Sin Imagen", "Cargue una imagen primero.")
            return

        self.calculate_metrics()

    def analyze_distribution(self):
        """Análisis de distribución espacial"""
        if not self.original_image:
            messagebox.showwarning("Sin Imagen", "Cargue una imagen primero.")
            return

        messagebox.showinfo("Análisis de Distribución",
                          "La distribución espacial se muestra en la pestaña 'Distribución' del análisis de métricas.")

    def analyze_clustering(self):
        """Análisis de agrupamiento celular"""
        if not self.original_image:
            messagebox.showwarning("Sin Imagen", "Cargue una imagen primero.")
            return

        messagebox.showinfo("Análisis de Agrupamiento",
                          "El análisis de agrupamiento se muestra en la pestaña 'Agrupamiento' del análisis de métricas.")

    def select_region(self):
        """Permite seleccionar una región rectangular para análisis"""
        if not self.original_image:
            messagebox.showwarning("Sin Imagen", "Cargue una imagen primero.")
            return

        self.status_bar.config(text="Seleccione una región rectangular. Haga clic y arrastre.")
        # Implementación de selección de región (simplificada)
        messagebox.showinfo("Selección de Región",
                          "Esta funcionalidad está en desarrollo. Por ahora, use las métricas globales.")

    def export_metrics_to_csv(self, basic_metrics, dist_metrics=None, cluster_metrics=None):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Todos los archivos", "*.*")]
        )
        if not file_path:
            return
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("Métrica,Valor\n")
                for label, value in basic_metrics:
                    if label != "":  # Saltar separadores
                        f.write(f"{label},{value}\n")

                if dist_metrics:
                    f.write("\nMétricas de Distribución,\n")
                    for key, value in dist_metrics.items():
                        label = key.replace('_', ' ').title()
                        f.write(f"{label},{value}\n")

                if cluster_metrics:
                    f.write("\nMétricas de Agrupamiento,\n")
                    for key, value in cluster_metrics.items():
                        label = key.replace('_', ' ').title()
                        f.write(f"{label},{value}\n")

            self.status_bar.config(text=f"Métricas exportadas a: {file_path}")
            messagebox.showinfo("Exportación Exitosa", "Las métricas se exportaron correctamente a formato CSV.")
        except Exception as e:
            messagebox.showerror("Error de Exportación", f"No se pudo exportar el archivo CSV:\n{str(e)}")

    def export_pdf_report(self, basic_metrics, dist_metrics=None, cluster_metrics=None):
        """Exporta un reporte en formato PDF (simulación)"""
        messagebox.showinfo("Exportar PDF",
                          "La exportación a PDF está en desarrollo. Por ahora, use la exportación a CSV.")

    def copy_metrics_to_clipboard(self, metrics):
        text = "Métrica\tValor\n"
        for label, value in metrics:
            if label != "":  # Saltar separadores
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
            self.open_project_file(path)
        elif project_type == 'annotation':
            self.load_annotations_file(path)
        else:
            self.open_image_file(path)

    def open_project_file(self, path):
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
            self.marker_size.set(project_data.get("marker_size", 8))
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
            self.zoom_fit()
            self.update_all_counts()
            self.redraw_markers()
            self.show_image_info()
            self.status_bar.config(text=f"Proyecto reciente cargado: {os.path.basename(path)}")
            self.update_quick_metrics()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el proyecto:\n{str(e)}")
            self.recent_projects = [p for p in self.recent_projects if p['path'] != path]
            self.update_recent_menu()

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
            self.update_quick_metrics()
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
            self.zoom_fit()
            self.status_bar.config(text=f"Imagen reciente cargada: {os.path.basename(path)}")
            self.add_to_recent(path)
            self.update_quick_metrics()
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
            "5. Calcular métricas (Archivo > Exportar Métricas o F6)\n"
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
            "Ctrl+0: Zoom 100%\n"
            "Ctrl+F: Ajustar a ventana\n"
            "F1: Mostrar este tutorial\n"
            "F2: Herramienta Ki-67 (+)\n"
            "F3: Herramienta Mitosis\n"
            "F4: Herramienta Negativo (-)\n"
            "F5: Herramienta Goma de Borrar\n"
            "F6: Calcular métricas\n"
            "Flechas: Desplazar imagen\n"
            "Rueda del mouse: Zoom\n"
            "Clic central + arrastrar: Pan\n"
        )
        messagebox.showinfo("Tutorial Rápido", tutorial, parent=self.root)

    def check_for_updates(self):
        messagebox.showinfo("Actualizaciones",
                          "HistoPath Analyst v1.1 es la versión más reciente.\n"
                          "Las actualizaciones se notificarán automáticamente cuando estén disponibles.",
                          parent=self.root)

    def show_about(self):
        about_text = (
            "HistoPath Analyst v1.1\n\n"
            "Herramienta soporte para el análisis cuantitativo en histopatología digital.\n"
            "Desarrollado para la optimización y estandarización de diagnósticos.\n\n"
            "Características principales:\n"
            "- Anotación precisa de núcleos celulares\n"
            "- Cálculo de índices de proliferación\n"
            "- Conteo de figuras infiltrantes\n"
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
