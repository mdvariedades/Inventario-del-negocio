
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from PIL import Image
import io

# Configuración de la página
st.set_page_config(page_title="Sistema Financiero y Ventas", layout="wide")

# Conexión a la base de datos
conn = sqlite3.connect("sistema_financiero.db", check_same_thread=False)
cursor = conn.cursor()


cursor.execute('''
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE,
        nombre TEXT,
        stock_actual INTEGER,
        stock_minimo INTEGER,
        costo_promedio REAL,
        precio_venta REAL,
        imagen BLOB
    )
''')

# Añadir la columna 'imagen' si la tabla ya existía previamente sin ella
try:
    cursor.execute("ALTER TABLE productos ADD COLUMN imagen BLOB")
except sqlite3.OperationalError:
    pass # La columna ya existe, se ignora el error

cursor.execute('''
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producto_id INTEGER,
        cantidad INTEGER,
        precio_unitario REAL,
        costo_unitario REAL,
        monto_total REAL,
        forma_pago TEXT,
        fecha TEXT
    )
''')
conn.commit()



# Menú principal en la barra lateral
st.sidebar.title("Navegación")
opcion = st.sidebar.radio("Ir a:", ["Inventario", "Registrar Venta", "Reporte Financiero"])

# --- 1. GESTIÓN DE INVENTARIO ---
if opcion == "Inventario":
    st.header("Gestión de Inventario")
    
    with st.form("nuevo_producto"):
        st.subheader("Agregar Producto")
        sku = st.text_input("SKU")
        nombre = st.text_input("Nombre del Producto")
        col1, col2 = st.columns(2)
        stock = col1.number_input("Stock Inicial", min_value=0, value=10)
        stock_min = col2.number_input("Stock Mínimo", min_value=1, value=5)
        col3, col4 = st.columns(2)
        costo = col3.number_input("Costo Unitario ($)", min_value=0.0, value=1.0)
        precio = col4.number_input("Precio de Venta ($)", min_value=0.0, value=2.0)
        imagen_file = st.file_uploader("Cargar Imagen", type=["jpg", "png", "jpeg"])
        
        btn_guardar = st.form_submit_button("Guardar Producto")
        
        if btn_guardar:
            img_bytes = None
            if imagen_file:
                img = Image.open(imagen_file)
                buffer = io.BytesIO()
                img.save(buffer, format="WEBP", optimize=True, quality=80)
                img_bytes = buffer.getvalue()
                
            try:
                cursor.execute('''
                    INSERT INTO productos (sku, nombre, stock_actual, stock_minimo, costo_promedio, precio_venta, imagen)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (sku, nombre, stock, stock_min, costo, precio, img_bytes))
                conn.commit()
                st.success("Producto registrado exitosamente.")
            except Exception as e:
                st.error(f"Error al registrar: {e}")

    st.subheader("Productos en Catálogo")
    df_prods = pd.read_sql_query("SELECT id, sku, nombre, stock_actual, stock_minimo, costo_promedio, precio_venta FROM productos", conn)
    st.dataframe(df_prods, use_container_width=True)

# --- 2. REGISTRAR VENTA ---
elif opcion == "Registrar Venta":
    st.header("Punto de Venta")
    
    df_prods = pd.read_sql_query("SELECT id, nombre, stock_actual, precio_venta, costo_promedio FROM productos", conn)
    
    if df_prods.empty:
        st.warning("No hay productos registrados en el inventario.")
    else:
        prod_sel = st.selectbox("Seleccionar Producto", df_prods['nombre'].tolist())
        prod_data = df_prods[df_prods['nombre'] == prod_sel].iloc[0]
        
        st.info(f"Stock disponible: {prod_data['stock_actual']} | Precio: ${prod_data['precio_venta']}")
        
        cantidad = st.number_input("Cantidad a vender", min_value=1, max_value=int(prod_data['stock_actual']) if prod_data['stock_actual'] > 0 else 1)
        forma_pago = st.selectbox("Forma de Pago", ["Efectivo", "Transferencia", "Crédito"])
        
        if st.button("Procesar Venta"):
            if prod_data['stock_actual'] < cantidad:
                st.error("Stock insuficiente.")
            else:
                nuevo_stock = prod_data['stock_actual'] - cantidad
                cursor.execute("UPDATE productos SET stock_actual = ? WHERE id = ?", (nuevo_stock, prod_data['id']))
                
                total = cantidad * prod_data['precio_venta']
                fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                cursor.execute('''
                    INSERT INTO ventas (producto_id, cantidad, precio_unitario, costo_unitario, monto_total, forma_pago, fecha)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (prod_data['id'], cantidad, prod_data['precio_venta'], prod_data['costo_promedio'], total, forma_pago, fecha_actual))
                
                conn.commit()
                st.success(f"Venta procesada por ${total:.2f}")

# --- 3. REPORTE FINANCIERO ---
elif opcion == "Reporte Financiero":
    st.header("Resumen Financiero")
    
    df_ventas = pd.read_sql_query("SELECT * FROM ventas", conn)
    df_prods = pd.read_sql_query("SELECT * FROM productos", conn)
    
    if not df_ventas.empty:
        ingresos = df_ventas['monto_total'].sum()
        costos = (df_ventas['cantidad'] * df_ventas['costo_unitario']).sum()
        ganancia = ingresos - costos
        val_inventario = (df_prods['stock_actual'] * df_prods['costo_promedio']).sum()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Ingresos Totales", f"${ingresos:.2f}")
        col2.metric("Costo de Ventas", f"${costos:.2f}")
        col3.metric("Ganancia Bruta", f"${ganancia:.2f}")
        col4.metric("Valor Inventario", f"${val_inventario:.2f}")
        
        st.subheader("Historial de Ventas")
        st.dataframe(df_ventas, use_container_width=True)
    else:
        st.info("Aún no se han registrado ventas.")
