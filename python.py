
# -*- coding: utf-8 -*-
"""
Renombrador Automático — versión v2.5.5 (fix)
- Arreglado: errores de cadenas con salto de línea en mensajes (sin f-strings con 
).
- Arreglado: patrones regex para detectar archivos numerados (png|jpg|jpeg).
- Persistencia: se guarda SIEMPRE al cerrar Configuración y al salir; se aplica al iniciar si persist=True.
- Diseño/estructura visual: SIN cambios (misma UI que tu archivo base).
"""

import os
import time
import ctypes
import sys
import re
import shutil
import threading
import json
import tkinter as tk
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox

# =========================
# Variables globales
# =========================
ultima_ruta = None
VERSION = "v2.5.5"
modo_actual = "dark"
historial_cambios = []

# =========================
# Configuración (persistencia)
# =========================
settings = {
    "watch_rename": False,              # Renombrado en tiempo real en carpeta destino
    "persist": False,                   # Recordar preferencias entre sesiones
    "default_prefix_enabled": False,    # Usar prefijo predeterminado
    "default_prefix": "",             # Valor del prefijo predeterminado
    "last_folder": "",                # Última carpeta usada
    "last_prefix": "",                # Último prefijo escrito en la entrada
    "mode": "dark"                    # dark/light
}


def _settings_path() -> Path:
    """Ruta del archivo de configuración (portable)."""
    if os.name == 'nt' and os.environ.get('APPDATA'):
        base = Path(os.environ['APPDATA']) / 'PauGx' / 'AutoRename'
    else:
        base = Path.home() / '.autorename'
    base.mkdir(parents=True, exist_ok=True)
    return base / 'settings.json'


def cargar_settings():
    global settings
    try:
        sp = _settings_path()
        if sp.exists():
            with open(sp, 'r', encoding='utf-8') as f:
                data = json.load(f)
                settings.update(data)
    except Exception:
        # Si hay problema al cargar, continuamos con defaults
        pass


def guardar_settings():
    try:
        sp = _settings_path()
        with open(sp, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        # Evitamos crashear si no se puede escribir
        pass


# --- Observador de capturas (mover a carpeta elegida) ---
# Directorios candidatos donde Windows suele guardar capturas
# (se pueden añadir más rutas si fuese necesario, sin tocar la UI)

def _rutas_capturas_candidatas():
    rutas = []
    user = os.environ.get("USERPROFILE") or ""
    pictures = Path(user) / "Pictures"
    one_drive = Path(user) / "OneDrive"

    # Win+PrtScn por defecto
    rutas.append(pictures / "Screenshots")
    # Variante en español de Windows
    rutas.append(pictures / "Capturas de pantalla")
    # OneDrive (si está redirigido)
    rutas.append(one_drive / "Pictures" / "Screenshots")
    rutas.append(one_drive / "Imágenes" / "Capturas de pantalla")
    return [p for p in rutas if p.exists()]


RUTAS_CAPTURAS = _rutas_capturas_candidatas()
_archivos_vistos = set()
_observador_activo = False


# Detectar ruta de la fuente (empaquetado o desarrollo)

def obtener_ruta_fuente():
    if getattr(sys, 'frozen', False):  # Si está empaquetado con PyInstaller
        return Path(sys._MEIPASS) / "RiotBlock.otf"
    else:
        return Path(r"C:\Users\cfgm2smxa09\Pictures\VSC\programs\AutoRename\RiotBlock.otf")


# Registrar la fuente en Windows para esta sesión

def registrar_fuente(ruta_fuente: Path):
    try:
        if ruta_fuente.exists() and os.name == 'nt':
            FR_PRIVATE = 0x10
            ctypes.windll.gdi32.AddFontResourceExW(str(ruta_fuente), FR_PRIVATE, 0)
    except Exception:
        # En plataformas no-Windows o si falla el registro, no detenemos la app
        pass


# Cargar la fuente personalizada (opcional)
fuente_path = obtener_ruta_fuente()
registrar_fuente(fuente_path)


# Configuración inicial del tema
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# Historial de actualizaciones (texto mostrado en la ventana de historial)

def _make_historial_texto():
    return [
        "v1.0: Interfaz básica con renombrado y barra de progreso.",
        "v1.1: Animación en botón y diseño oscuro elegante.",
        "v1.2: Mostrar carpeta actual y versión en título.",
        "v1.3: Versión en esquina inferior derecha + botón historial.",
        "v1.4: Diseño moderno con CustomTkinter.",
        "v1.5: Botón modo oscuro/claro + barra de progreso funcional.",
        "v1.6: Ventana historial con diseño moderno y botón salir.",
        "v2.0: Deshacer renombrado, descripción extra.",
        "v2.1: Eliminada numeración inversa.",
        "v2.2: Botones Cambiar carpeta y Renombrar imágenes en la misma línea.",
        "v2.3: Título Riot Block tamaño 96 + historial corregido.",
        "v2.4: Observador de capturas: mueve automáticamente a la carpeta elegida.",
        "v2.4: Renombrado inteligente: continúa numeración y no toca numerados.",
        "v2.5: Menú de Configuración (watcher destino, persistencia y prefijo).",
        "v2.5.5: Mensajes sin f-strings con 
 + persistencia estable + regex OK.",
    ]

historial_texto = _make_historial_texto()


# =========================
# Funciones de UI
# =========================

def mostrar_historial():
    ventana_historial = ctk.CTkToplevel()
    ventana_historial.title("Historial de actualizaciones")
    ventana_historial.geometry("500x500")
    ctk.CTkLabel(ventana_historial, text="Historial de actualizaciones", font=("Arial", 20, "bold")).pack(pady=10)
    frame_lista = ctk.CTkFrame(ventana_historial, corner_radius=10)
    frame_lista.pack(pady=10, padx=10, fill="both", expand=True)
    for cambio in historial_texto:
        ctk.CTkLabel(frame_lista, text=cambio, font=("Arial", 12), anchor="w").pack(pady=2, padx=10, anchor="w")

    if historial_cambios:
        ctk.CTkLabel(ventana_historial, text="Cambios realizados:", font=("Arial", 14, "bold")).pack(pady=5)
        for lote in historial_cambios:
            ctk.CTkLabel(ventana_historial, text="--- Operación ---", font=("Arial", 12, "bold")).pack(anchor="w", padx=20)
            for original, nuevo in lote:
                ctk.CTkLabel(ventana_historial, text=f"{original} → {nuevo}", font=("Arial", 10)).pack(anchor="w", padx=40)

    ctk.CTkButton(
        ventana_historial, text="Salir", fg_color="#FF4C4C", hover_color="#CC0000",
        command=ventana_historial.destroy
    ).pack(pady=15)


def cambiar_modo():
    global modo_actual
    if modo_actual == "dark":
        ctk.set_appearance_mode("light")
        modo_actual = "light"
        boton_modo.configure(text="🌙")
    else:
        ctk.set_appearance_mode("dark")
        modo_actual = "dark"
        boton_modo.configure(text="☀")
    # Guardamos el modo siempre; se aplicará en el arranque solo si persist=True
    settings["mode"] = modo_actual
    guardar_settings()


def deshacer_ultimo():
    if not historial_cambios:
        messagebox.showinfo("Aviso", "No hay cambios para deshacer.")
        return
    ultima_operacion = historial_cambios.pop()
    restaurados = 0
    for original, nuevo in ultima_operacion:
        try:
            if Path(nuevo).exists():
                Path(nuevo).rename(original)
                restaurados += 1
        except Exception:
            # Si no se puede restaurar un archivo, continuamos con los demás
            pass
    messagebox.showinfo("Deshacer", f"Se restauraron {restaurados} imágenes al estado original.")


# =========================
# Lógica de renombrado (mejorada)
# =========================

_EXTS = {".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"}


def _listar_imagenes(directorio: Path):
    archivos = []
    for ext in _EXTS:
        archivos.extend(sorted(directorio.glob(f"*{ext}")))
    return archivos


def _regex_numerado(prefijo: str):
    # Patrón correcto sin saltos de línea
    if prefijo:
        return re.compile(rf"^{re.escape(prefijo)}(\d+)\.(png|jpg|jpeg)$", re.IGNORECASE)
    else:
        return re.compile(r"^(\d+)\.(png|jpg|jpeg)$", re.IGNORECASE)


def _max_num_existente(directorio: Path, prefijo: str):
    ya_numerados = []
    max_n = 0
    patron = _regex_numerado(prefijo)
    for f in _listar_imagenes(directorio):
        m = patron.match(f.name)
        if m:
            n = int(m.group(1))
            ya_numerados.append(f)
            if n > max_n:
                max_n = n
    return max_n, set(ya_numerados)


def renombrar_capturas(directorio: Path, prefijo: str):
    archivos = _listar_imagenes(directorio)
    if not archivos:
        messagebox.showinfo("Información", "No se encontraron imágenes.")
        return

    # Descubrir numeración existente y qué archivos NO tocar
    max_existente, conjunto_skip = _max_num_existente(directorio, prefijo)

    # Los que se van a renombrar son los que no están ya numerados
    archivos_a_renombrar = [a for a in archivos if a not in conjunto_skip]

    if not archivos_a_renombrar:
        messagebox.showinfo("Información", "Todas las imágenes ya están numeradas. No hay nada que renombrar.")
        barra.set(1)
        ventana.update_idletasks()
        return

    barra.set(0)
    total = len(archivos_a_renombrar)
    contador = max_existente + 1
    cambios_actuales = []

    for i, archivo in enumerate(archivos_a_renombrar, start=1):
        suf = archivo.suffix.lower()
        if prefijo:
            nuevo_nombre = f"{prefijo}{contador:03d}{suf}"
        else:
            nuevo_nombre = f"{contador}{suf}"
        nuevo_path = directorio / nuevo_nombre

        # Evitar colisiones por si acaso
        while nuevo_path.exists():
            contador += 1
            if prefijo:
                nuevo_nombre = f"{prefijo}{contador:03d}{suf}"
            else:
                nuevo_nombre = f"{contador}{suf}"
            nuevo_path = directorio / nuevo_nombre

        try:
            archivo.rename(nuevo_path)
            cambios_actuales.append((str(archivo), str(nuevo_path)))
            contador += 1
        except Exception:
            pass

        time.sleep(0.02)
        barra.set(i / total)
        ventana.update_idletasks()

    if cambios_actuales:
        # Construimos el mensaje sin f-strings con 
 para evitar errores de copiado/pegado
        line1 = "Renombradas {} imágenes en:".format(len(cambios_actuales))
        msg = "
".join([line1, str(directorio)])
        historial_cambios.append(cambios_actuales)
        messagebox.showinfo("Éxito", msg)
    else:
        messagebox.showinfo("Información", "No se realizaron cambios.")


def seleccionar_carpeta():
    global ultima_ruta
    carpeta = filedialog.askdirectory(title="Selecciona la carpeta de imágenes")
    if carpeta:
        ultima_ruta = Path(carpeta)
        etiqueta_ruta.configure(text=str(ultima_ruta))
        # Guardar siempre; solo se aplicará al arrancar si persist=True
        settings["last_folder"] = str(ultima_ruta)
        guardar_settings()


def ejecutar_renombrado():
    if ultima_ruta:
        prefijo = current_effective_prefix()
        if not settings.get("default_prefix_enabled"):
            prefijo = entrada_prefijo.get().strip()
        renombrar_capturas(ultima_ruta, prefijo)
    else:
        messagebox.showwarning("Aviso", "Primero debes seleccionar una carpeta.")


# =========================
# Observador de capturas (mover automáticamente a ultima_ruta)
# =========================

def _nombre_unico(dest_dir: Path, nombre: str) -> Path:
    base, ext = os.path.splitext(nombre)
    candidato = dest_dir / nombre
    idx = 1
    while candidato.exists():
        candidato = dest_dir / f"{base} ({idx}){ext}"
        idx += 1
    return candidato


def _rellenar_archivos_vistos_inicial():
    for carpeta in RUTAS_CAPTURAS:
        for ext in _EXTS:
            for f in carpeta.glob(f"*{ext}"):
                try:
                    _archivos_vistos.add(str(f.resolve()))
                except Exception:
                    pass


def _intentar_mover(origen: Path, destino_dir: Path):
    intentos = 10
    for _ in range(intentos):
        try:
            if not destino_dir.exists():
                destino_dir.mkdir(parents=True, exist_ok=True)
            destino = _nombre_unico(destino_dir, origen.name)
            shutil.move(str(origen), str(destino))
            return True
        except Exception:
            time.sleep(0.2)
    return False


def _observador_loop():
    global _observador_activo
    _observador_activo = True
    _rellenar_archivos_vistos_inicial()
    while _observador_activo:
        try:
            if ultima_ruta:
                for carpeta in RUTAS_CAPTURAS:
                    if not carpeta.exists():
                        continue
                    for ext in _EXTS:
                        for f in carpeta.glob(f"*{ext}"):
                            try:
                                ruta_abs = str(f.resolve())
                            except Exception:
                                continue
                            if ruta_abs in _archivos_vistos:
                                continue
                            _archivos_vistos.add(ruta_abs)
                            if ultima_ruta and f.parent.resolve() != ultima_ruta.resolve():
                                _intentar_mover(f, ultima_ruta)
        except Exception:
            pass
        time.sleep(1.0)


def iniciar_observador_capturas_si_no_iniciado():
    if not getattr(iniciar_observador_capturas_si_no_iniciado, "_started", False):
        t = threading.Thread(target=_observador_loop, daemon=True)
        t.start()
        iniciar_observador_capturas_si_no_iniciado._started = True


# =========================
# Watcher de RENOMBRADO en carpeta destino (opcional)
# =========================
_dest_seen = set()


def current_effective_prefix() -> str:
    """Prefijo efectivo para operaciones (watchers y manual).
    Si default_prefix_enabled=True y hay valor -> usa ese; si no, usa el entry.
    """
    if settings.get("default_prefix_enabled"):
        return settings.get("default_prefix", "").strip()
    return entrada_prefijo.get().strip() if 'entrada_prefijo' in globals() else ""


def _es_numerado(f: Path, prefijo: str) -> bool:
    return bool(_regex_numerado(prefijo).match(f.name))


def _renombrar_uno_si_corresponde(directorio: Path, archivo: Path, prefijo: str):
    if _es_numerado(archivo, prefijo):
        return False
    # Saltar archivos temporales típicos
    if archivo.name.startswith('~$'):
        return False
    try:
        # Calcular siguiente número libre cada vez para ser robustos
        max_exist, _ = _max_num_existente(directorio, prefijo)
        contador = max_exist + 1
        suf = archivo.suffix.lower()
        if prefijo:
            nuevo_nombre = f"{prefijo}{contador:03d}{suf}"
        else:
            nuevo_nombre = f"{contador}{suf}"
        nuevo_path = directorio / nuevo_nombre
        while nuevo_path.exists():
            contador += 1
            if prefijo:
                nuevo_nombre = f"{prefijo}{contador:03d}{suf}"
            else:
                nuevo_nombre = f"{contador}{suf}"
            nuevo_path = directorio / nuevo_nombre
        # Reintento por si el archivo aún está en uso
        for _ in range(10):
            try:
                archivo.rename(nuevo_path)
                return True
            except Exception:
                time.sleep(0.2)
        return False
    except Exception:
        return False


def _watch_dest_loop():
    # Renombrado en tiempo real en la carpeta de destino
    # Respeta settings["watch_rename"]
    while True:
        try:
            if settings.get("watch_rename") and ultima_ruta and Path(ultima_ruta).exists():
                pref = current_effective_prefix()
                for ext in _EXTS:
                    for f in Path(ultima_ruta).glob(f"*{ext}"):
                        try:
                            p = f.resolve()
                        except Exception:
                            continue
                        if str(p) in _dest_seen:
                            continue
                        _dest_seen.add(str(p))
                        _renombrar_uno_si_corresponde(Path(ultima_ruta), f, pref)
        except Exception:
            pass
        time.sleep(1.0)


def iniciar_watcher_destino_si_no_iniciado():
    if not getattr(iniciar_watcher_destino_si_no_iniciado, "_started", False):
        t = threading.Thread(target=_watch_dest_loop, daemon=True)
        t.start()
        iniciar_watcher_destino_si_no_iniciado._started = True


# =========================
# Ventana principal (misma UI)
# =========================
ventana = ctk.CTk()
ventana.title("Renombrador Automático")
ventana.geometry("500x700")

# Botón modo oscuro/claro
boton_modo = ctk.CTkButton(
    ventana, text="☀", width=40, height=40, command=cambiar_modo,
    fg_color="#333333", hover_color="#444444"
)
boton_modo.place(x=430, y=20)

# Fuente personalizada para el título
titulo_fuente = ctk.CTkFont(family="Riot Block", size=96)

# Título y subtítulo
ctk.CTkLabel(ventana, text="RENAME", font=titulo_fuente).pack(pady=10)
ctk.CTkLabel(ventana, text="Automático", font=("Arial", 16)).pack(pady=5)

# Frame principal
frame = ctk.CTkFrame(ventana, corner_radius=15)
frame.pack(pady=20, padx=20, fill="both")

# Prefijo
ctk.CTkLabel(frame, text="PREFIJO DEL ARCHIVO", font=("Arial", 14)).pack(pady=(10, 5))
entrada_prefijo = ctk.CTkEntry(frame, placeholder_text="image")
entrada_prefijo.pack(pady=5)
ctk.CTkLabel(
    frame,
    text="Si no rellenas el campo, se usará este patrón: 1.png, 2.png, 3.png",
    font=("Arial", 10)
).pack(pady=(0, 10))

# Ubicación
ctk.CTkLabel(frame, text="UBICACIÓN", font=("Arial", 14)).pack(pady=(10, 5))
etiqueta_ruta = ctk.CTkLabel(frame, text="Ninguna carpeta seleccionada", font=("Arial", 10))
etiqueta_ruta.pack(pady=5)

# Botones principales
frame_botones = ctk.CTkFrame(frame)
frame_botones.pack(pady=10)
ctk.CTkButton(frame_botones, text="Cambiar carpeta", command=seleccionar_carpeta, width=150).pack(side="left", padx=10)
ctk.CTkButton(
    frame_botones, text="▶ Renombrar imágenes", command=ejecutar_renombrado,
    fg_color="#00AEEF", hover_color="#008FCC", width=150
).pack(side="left", padx=10)

# Barra de progreso
barra = ctk.CTkProgressBar(ventana)
barra.pack(pady=10)
barra.set(0)

# Botones extra
ctk.CTkButton(
    ventana, text="Deshacer último renombrado", fg_color="#FF4C4C", hover_color="#CC0000",
    command=deshacer_ultimo
).pack(pady=10)
ctk.CTkButton(
    ventana, text="Ver historial de actualizaciones", command=mostrar_historial,
    fg_color="#333333", hover_color="#444444"
).pack(pady=10)

# Versión y créditos
ctk.CTkLabel(ventana, text=f"Versión {VERSION}", font=("Arial", 10)).pack(side="bottom", pady=5)
ctk.CTkLabel(ventana, text="Desarrollado por PauGx", font=("Arial", 10)).pack(side="bottom", pady=5)


# =========================
# Menú de Configuración (sin alterar layout principal)
# =========================

def abrir_config():
    cfg = ctk.CTkToplevel()
    cfg.title("Configuración")
    cfg.geometry("420x300")
    cfg.grab_set()

    ctk.CTkLabel(cfg, text="Configuración", font=("Arial", 18, "bold")).pack(pady=10)

    cont = ctk.CTkFrame(cfg, corner_radius=12)
    cont.pack(padx=15, pady=10, fill="both", expand=True)

    # Checklist: watcher de renombrado en tiempo real
    var_watch = tk.BooleanVar(value=settings.get("watch_rename", False))
    chk_watch = ctk.CTkCheckBox(cont, text="Renombrado en tiempo real (carpeta destino)", variable=var_watch)
    chk_watch.pack(anchor="w", padx=12, pady=(12, 6))

    # Checklist: persistencia de preferencias
    var_persist = tk.BooleanVar(value=settings.get("persist", False))
    chk_persist = ctk.CTkCheckBox(cont, text="Recordar preferencias (persistencia)", variable=var_persist)
    chk_persist.pack(anchor="w", padx=12, pady=6)

    # Checklist + entrada: prefijo predeterminado
    var_defprefix = tk.BooleanVar(value=settings.get("default_prefix_enabled", False))
    chk_defprefix = ctk.CTkCheckBox(cont, text="Usar prefijo predeterminado", variable=var_defprefix)
    chk_defprefix.pack(anchor="w", padx=12, pady=(6, 0))

    entrada_prefijo_cfg = ctk.CTkEntry(cont, placeholder_text="prefijo", width=200)
    entrada_prefijo_cfg.insert(0, settings.get("default_prefix", ""))
    entrada_prefijo_cfg.configure(state=("normal" if var_defprefix.get() else "disabled"))
    entrada_prefijo_cfg.pack(anchor="w", padx=32, pady=(4, 12))

    def on_toggle_defprefix():
        entrada_prefijo_cfg.configure(state=("normal" if var_defprefix.get() else "disabled"))

    chk_defprefix.configure(command=on_toggle_defprefix)

    # Botonera
    fila = ctk.CTkFrame(cfg)
    fila.pack(fill="x", padx=15, pady=10)

    def guardar_y_cerrar():
        # Actualizamos settings con lo que haya en el diálogo
        settings["watch_rename"] = bool(var_watch.get())
        settings["persist"] = bool(var_persist.get())
        settings["default_prefix_enabled"] = bool(var_defprefix.get())
        settings["default_prefix"] = entrada_prefijo_cfg.get().strip()
        # Guardamos SIEMPRE para recordar el estado del diálogo
        settings["last_prefix"] = entrada_prefijo.get().strip()
        if ultima_ruta:
            settings["last_folder"] = str(ultima_ruta)
        settings["mode"] = modo_actual
        guardar_settings()
        cfg.destroy()

    ctk.CTkButton(
        fila, text="Guardar", fg_color="#00AEEF", hover_color="#008FCC", command=guardar_y_cerrar
    ).pack(side="right", padx=5)
    ctk.CTkButton(
        fila, text="Cerrar", command=cfg.destroy, fg_color="#333333", hover_color="#444444"
    ).pack(side="right", padx=5)


# Menú superior (no altera el layout de frames/botones)
menubar = tk.Menu(ventana)
menu_cfg = tk.Menu(menubar, tearoff=0)
menu_cfg.add_command(label="Abrir configuración (Ctrl+,)", command=abrir_config)
menubar.add_cascade(label="Configuración", menu=menu_cfg)
ventana.configure(menu=menubar)
ventana.bind_all('<Control-comma>', lambda e: abrir_config())


# =========================
# Carga inicial de settings y estado
# =========================

cargar_settings()
if settings.get("persist"):
    # Rellenar entry de prefijo
    if settings.get("last_prefix"):
        try:
            entrada_prefijo.delete(0, tk.END)
            entrada_prefijo.insert(0, settings.get("last_prefix"))
        except Exception:
            pass
    # Última carpeta
    lf = settings.get("last_folder")
    if lf and Path(lf).exists():
        ultima_ruta = Path(lf)
        etiqueta_ruta.configure(text=str(ultima_ruta))
    # Modo claro/oscuro
    if settings.get("mode") in ("dark", "light"):
        if settings["mode"] != modo_actual:
            if settings["mode"] == "light":
                ctk.set_appearance_mode("light")
                modo_actual = "light"
                boton_modo.configure(text="🌙")
            else:
                ctk.set_appearance_mode("dark")
                modo_actual = "dark"
                boton_modo.configure(text="☀")


# Iniciar hilos observadores (no modifican la UI)
iniciar_observador_capturas_si_no_iniciado()
iniciar_watcher_destino_si_no_iniciado()


# Al cerrar: guardamos SIEMPRE settings (se aplicarán en el arranque solo si persist=True)

def _on_close():
    settings["last_prefix"] = entrada_prefijo.get().strip()
    if ultima_ruta:
        settings["last_folder"] = str(ultima_ruta)
    settings["mode"] = modo_actual
    guardar_settings()
    ventana.destroy()

ventana.protocol('WM_DELETE_WINDOW', _on_close)

ventana.mainloop()
