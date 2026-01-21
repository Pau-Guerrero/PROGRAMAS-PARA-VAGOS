
import os
import glob
import time
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Variables globales
ultima_ruta = None
VERSION = "v2.2"
modo_actual = "dark"
historial_cambios = []  # Guardará listas de cambios por operación

# Historial de actualizaciones
historial = [
    "v1.0: Interfaz básica con renombrado y barra de progreso.",
    "v1.1: Animación en botón y diseño oscuro elegante.",
    "v1.2: Mostrar carpeta actual y versión en título.",
    "v1.3: Versión en esquina inferior derecha + botón historial.",
    "v1.4: Diseño moderno con CustomTkinter (igual a imagen).",
    "v1.5: Botón modo oscuro/claro + barra de progreso funcional.",
    "v1.6: Ventana historial con diseño moderno y botón salir.",
    "v2.0: Deshacer renombrado, descripción extra.",
    "v2.1: Eliminada numeración inversa.",
    "v2.2: Botones Cambiar carpeta y Renombrar imágenes en la misma línea + fuente Riot Block en título."
]

# Configuración inicial del tema
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Función para mostrar historial en ventana nueva
def mostrar_historial():
    ventana_historial = ctk.CTkToplevel()
    ventana_historial.title("Historial de actualizaciones")
    ventana_historial.geometry("450x400")

    titulo_historial = ctk.CTkLabel(ventana_historial, text="Historial de actualizaciones", font=("Arial", 18, "bold"))
    titulo_historial.pack(pady=10)

    frame_lista = ctk.CTkFrame(ventana_historial, corner_radius=10)
    frame_lista.pack(pady=10, padx=10, fill="both", expand=True)

    for cambio in historial:
        label_cambio = ctk.CTkLabel(frame_lista, text=cambio, font=("Arial", 12), anchor="w")
        label_cambio.pack(pady=5, padx=10, anchor="w")

    if historial_cambios:
        ctk.CTkLabel(ventana_historial, text="Cambios realizados:", font=("Arial", 14, "bold")).pack(pady=5)
        for original, nuevo in historial_cambios[-1]:
            ctk.CTkLabel(ventana_historial, text=f"{original} → {nuevo}", font=("Arial", 10)).pack(anchor="w", padx=20)

    boton_salir = ctk.CTkButton(ventana_historial, text="Salir", fg_color="#FF4C4C", hover_color="#CC0000", command=ventana_historial.destroy)
    boton_salir.pack(pady=15)

# Alternar modo oscuro/claro
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

# Deshacer último renombrado
def deshacer_ultimo():
    if not historial_cambios:
        messagebox.showinfo("Aviso", "No hay cambios para deshacer.")
        return

    ultima_operacion = historial_cambios.pop()
    for original, nuevo in ultima_operacion:
        if os.path.exists(nuevo):
            os.rename(nuevo, original)

    messagebox.showinfo("Deshacer", f"Se restauraron {len(ultima_operacion)} imágenes al estado original.")

# Renombrar imágenes
def renombrar_capturas(directorio, prefijo):
    os.chdir(directorio)
    archivos = sorted(glob.glob("*.png") + glob.glob("*.jpg"))

    if not archivos:
        messagebox.showinfo("Información", "No se encontraron imágenes.")
        return

    barra.set(0)
    total = len(archivos)
    contador = 1
    cambios_actuales = []

    for i, archivo in enumerate(archivos, start=1):
        if prefijo == "":
            nuevo_nombre = f"{contador}{os.path.splitext(archivo)[1]}"
        else:
            nuevo_nombre = f"{prefijo}{contador:03d}{os.path.splitext(archivo)[1]}"

        while os.path.exists(nuevo_nombre):
            contador += 1
            nuevo_nombre = f"{prefijo}{contador:03d}{os.path.splitext(archivo)[1]}"

        os.rename(archivo, nuevo_nombre)
        cambios_actuales.append((archivo, nuevo_nombre))
        contador += 1

        time.sleep(0.05)
        barra.set(i / total)
        ventana.update_idletasks()

    historial_cambios.append(cambios_actuales)
    messagebox.showinfo("Éxito", f"Renombradas {contador - 1} imágenes en:\n{directorio}")

# Selección de carpeta
def seleccionar_carpeta():
    global ultima_ruta
    carpeta = filedialog.askdirectory(title="Selecciona la carpeta de imágenes")
    if carpeta:
        ultima_ruta = carpeta
        etiqueta_ruta.configure(text=f"{ultima_ruta}")

# Ejecutar renombrado
def ejecutar_renombrado():
    global ultima_ruta
    if ultima_ruta:
        prefijo = entrada_prefijo.get().strip()
        renombrar_capturas(ultima_ruta, prefijo)
    else:
        messagebox.showwarning("Aviso", "Primero debes seleccionar una carpeta.")

# Ventana principal
ventana = ctk.CTk()
ventana.title("Renombrador Automático")
ventana.geometry("450x650")

# Botón modo oscuro/claro
boton_modo = ctk.CTkButton(ventana, text="☀", width=40, height=40, command=cambiar_modo, fg_color="#333333", hover_color="#444444")
boton_modo.place(x=380, y=20)

# Fuente personalizada para el título
titulo_fuente = ctk.CTkFont(family="Riot Block", size=95)

# Título con fuente Riot Block
ctk.CTkLabel(ventana, text="RENAME", font=titulo_fuente).pack(pady=10)
ctk.CTkLabel(ventana, text="Automático", font=("Arial", 25)).pack(pady=5)

# Frame principal
frame = ctk.CTkFrame(ventana, corner_radius=15)
frame.pack(pady=20, padx=20, fill="both")

# Prefijo
ctk.CTkLabel(frame, text="PREFIJO DEL ARCHIVO", font=("Arial", 14)).pack(pady=(10, 5))
entrada_prefijo = ctk.CTkEntry(frame, placeholder_text="image")
entrada_prefijo.pack(pady=5)
ctk.CTkLabel(frame, text="Si no rellenas el campo, se usará este patrón: 1.png, 2.png, 3.png", font=("Arial", 10)).pack(pady=(0, 10))

# Ubicación
ctk.CTkLabel(frame, text="UBICACIÓN", font=("Arial", 14)).pack(pady=(10, 5))
etiqueta_ruta = ctk.CTkLabel(frame, text="Ninguna carpeta seleccionada", font=("Arial", 10))
etiqueta_ruta.pack(pady=5)

# Frame horizontal para los dos botones
frame_botones = ctk.CTkFrame(frame)
frame_botones.pack(pady=10)

boton_cambiar = ctk.CTkButton(frame_botones, text="Cambiar carpeta", command=seleccionar_carpeta, width=150)
boton_cambiar.pack(side="left", padx=10)

boton_renombrar = ctk.CTkButton(frame_botones, text="▶ Renombrar imágenes", command=ejecutar_renombrado, fg_color="#00AEEF", hover_color="#008FCC", width=150)
boton_renombrar.pack(side="left", padx=10)

# Barra de progreso
barra = ctk.CTkProgressBar(ventana)
barra.pack(pady=10)
barra.set(0)

# Botones extra
ctk.CTkButton(ventana, text="Deshacer último renombrado", fg_color="#FF4C4C", hover_color="#CC0000", command=deshacer_ultimo).pack(pady=10)
ctk.CTkButton(ventana, text="Ver historial de actualizaciones", command=mostrar_historial, fg_color="#333333", hover_color="#444444").pack(pady=10)

# Versión y créditos
ctk.CTkLabel(ventana, text=f"Versión {VERSION}", font=("Arial", 10)).pack(side="bottom", pady=5)
ctk.CTkLabel(ventana, text="Desarrollado por PauGx", font=("Arial", 10)).pack(side="bottom", pady=5)

ventana.mainloop()
