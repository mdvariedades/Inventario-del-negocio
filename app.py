
import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Gestión Financiera", layout="wide")

# Archivos de almacenamiento
ARCHIVO_INVENTARIO = "inventario.csv"
ARCHIVO_VENTAS = "ventas.csv"

# Cargar datos
def cargar_datos(archivo, columnas):
    if os.path.exists(archivo):
        return pd.read_csv(archivo)
    return pd.DataFrame(columns=columnas)

def guardar_datos(df, archivo):
    df.to_csv(archivo, index=False)

if "inventario" not in st.session_state:
    cols_inv = ["Producto", "Categoría", "Stock", "Costo ($)", "Precio Venta ($)", "Ganancia Un. ($)"]
    st.session_state.inventario = cargar_datos(ARCHIVO_INVENTARIO, cols_inv)

if "ventas" not in st.session_state:
    cols_ven = ["Producto", "Cantidad", "Total ($)", "Ganancia ($)"]
    st.session_state.ventas = cargar_datos(ARCHIVO_VENTAS, cols_ven)

# --- BARRA LATERAL: SELECCIÓN DE ROL ---
st.sidebar.title("🔐 Acceso de Usuario")
rol = st.sidebar.radio("Selecciona tu Rol:", ["Vendedor", "Administrador"])

# --- VISTA DE VENDEDOR ---
if rol == "Vendedor":
    st.title("🛒 Punto de Venta (Vendedor)")
   
    if st.session_state.inventario.empty:
        st.info("No hay productos disponibles en el inventario.")
    else:
        prod_lista = st.session_state.inventario["Producto"].tolist()
        prod_sel = st.selectbox("Selecciona el producto a vender", prod_lista)
       
        idx = st.session_state.inventario[st.session_state.inventario["Producto"] == prod_sel].index[0]
        stock_actual = st.session_state.inventario.loc[idx, "Stock"]
        precio_un = st.session_state.inventario.loc[idx, "Precio Venta ($)"]
        costo_un = st.session_state.inventario.loc[idx, "Costo ($)"]
       
        st.write(f"**Precio unitario:** ${precio_un:.2f}")
        st.write(f"**Disponibles en stock:** {stock_actual}")
       
        cant_venta = st.number_input("Cantidad a vender", min_value=1, max_value=int(stock_actual) if stock_actual > 0 else 1, step=1)
       
        if stock_actual <= 0:
            st.error("⚠️ Producto agotado.")
        else:
            if st.button("Confirmar Venta"):
                st.session_state.inventario.loc[idx, "Stock"] -= cant_venta
                total = cant_venta * precio_un
                ganancia = cant_venta * (precio_un - costo_un)
               
                nueva_venta = pd.DataFrame([{
                    "Producto": prod_sel,
                    "Cantidad": cant_venta,
                    "Total ($)": total,
                    "Ganancia ($)": ganancia
                }])
                st.session_state.ventas = pd.concat([st.session_state.ventas, nueva_venta], ignore_index=True)
               
                guardar_datos(st.session_state.inventario, ARCHIVO_INVENTARIO)
                guardar_datos(st.session_state.ventas, ARCHIVO_VENTAS)
               
                st.success(f"✅ Venta registrada con éxito. Total a cobrar: ${total:.2f}")
                st.rerun()

# --- VISTA DE ADMINISTRADOR ---
else:
    st.title("📊 Panel Administrativo")
    clave = st.sidebar.text_input("Contraseña de Admin", type="password")
   
    # Cambia '1234' por la contraseña que tú quieras
    if clave == "1234":
        inv = st.session_state.inventario
        ventas = st.session_state.ventas

        val_inventario = (inv["Stock"] * inv["Precio Venta ($)"]).sum() if not inv.empty else 0.0
        total_ventas = ventas["Total ($)"].sum() if not ventas.empty else 0.0
        ganancia_total = ventas["Ganancia ($)"].sum() if not ventas.empty else 0.0

        col1, col2, col3 = st.columns(3)
        col1.metric("Valor del Inventario", f"${val_inventario:.2f}")
        col2.metric("Ventas Totales", f"${total_ventas:.2f}")
        col3.metric("Ganancia Real Acumulada", f"${ganancia_total:.2f}")

        st.divider()

        st.subheader("➕ Agregar / Modificar Producto")
        with st.form("form_producto", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                nombre = st.text_input("Nombre del producto")
                categoria = st.selectbox("Categoría", ["Helados", "Accesorios / Bisutería", "Otros"])
                stock = st.number_input("Cantidad inicial en stock", min_value=0, step=1)
            with col_b:
                costo = st.number_input("Costo ($)", min_value=0.0, step=0.05, format="%.2f")
                precio = st.number_input("Precio Venta ($)", min_value=0.0, step=0.05, format="%.2f")
                guardar = st.form_submit_button("Guardar Producto")

        if guardar and nombre:
            ganancia_un = precio - costo
            nuevo_prod = pd.DataFrame([{
                "Producto": nombre, "Categoría": categoria, "Stock": stock,
                "Costo ($)": costo, "Precio Venta ($)": precio, "Ganancia Un. ($)": ganancia_un
            }])
            st.session_state.inventario = pd.concat([st.session_state.inventario, nuevo_prod], ignore_index=True)
            guardar_datos(st.session_state.inventario, ARCHIVO_INVENTARIO)
            st.success(f"Producto '{nombre}' guardado.")
            st.rerun()

        st.subheader("📋 Inventario Completo")
        st.dataframe(st.session_state.inventario, use_container_width=True)

        st.subheader("📜 Historial de Ventas")
        st.dataframe(st.session_state.ventas, use_container_width=True)
    else:
        st.warning("Ingresa la contraseña de administrador en el menú lateral para ver la información financiera.")

