
import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Panel de Control y Ventas", layout="wide")

# Archivos de almacenamiento
ARCHIVO_INVENTARIO = "inventario.csv"
ARCHIVO_VENTAS = "ventas.csv"

COLS_INV = ["Producto", "Categoría", "Stock", "Costo ($)", "Precio Venta ($)", "Ganancia Un. ($)"]
COLS_VEN = ["Producto", "Cantidad", "Total ($)", "Ganancia ($)"]

# Carga segura con auto-reparación de columnas y tipos numéricos
def cargar_datos(archivo, columnas_esperadas):
    if os.path.exists(archivo):
        try:
            df = pd.read_csv(archivo)
            for col in columnas_esperadas:
                if col not in df.columns:
                    df[col] = 0.0 if "($)" in col or col == "Stock" else "General"
           
            # Convertir columnas numéricas para evitar errores
            for c in ["Stock", "Costo ($)", "Precio Venta ($)", "Ganancia Un. ($)"]:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
            return df[columnas_esperadas]
        except Exception:
            return pd.DataFrame(columns=columnas_esperadas)
    return pd.DataFrame(columns=columnas_esperadas)

def guardar_datos(df, archivo):
    df.to_csv(archivo, index=False)

if "inventario" not in st.session_state:
    st.session_state.inventario = cargar_datos(ARCHIVO_INVENTARIO, COLS_INV)

if "ventas" not in st.session_state:
    st.session_state.ventas = cargar_datos(ARCHIVO_VENTAS, COLS_VEN)

# --- MENÚ LATERAL: ROLES ---
st.sidebar.title("🔐 Acceso de Usuario")
rol = st.sidebar.radio("Selecciona tu rol:", ["Vendedor", "Administrador"])

# --- VISTA 1: VENDEDOR ---
if rol == "Vendedor":
    st.title("🛒 Punto de Venta (Vendedor)")
   
    if st.session_state.inventario.empty:
        st.info("No hay productos disponibles en el inventario.")
    else:
        cats = ["Todas"] + list(st.session_state.inventario["Categoría"].unique())
        cat_sel = st.selectbox("Filtrar por Categoría", cats)
       
        inv_filtrado = st.session_state.inventario
        if cat_sel != "Todas":
            inv_filtrado = inv_filtrado[inv_filtrado["Categoría"] == cat_sel]
           
        if inv_filtrado.empty:
            st.warning("No hay productos en esta categoría.")
        else:
            prod_lista = inv_filtrado["Producto"].tolist()
            prod_sel = st.selectbox("Selecciona el producto a vender", prod_lista)
           
            idx = st.session_state.inventario[st.session_state.inventario["Producto"] == prod_sel].index[0]
            stock_act = int(st.session_state.inventario.loc[idx, "Stock"])
            precio_un = float(st.session_state.inventario.loc[idx, "Precio Venta ($)"])
            costo_un = float(st.session_state.inventario.loc[idx, "Costo ($)"])
           
            col_info1, col_info2 = st.columns(2)
            col_info1.metric("Precio Unitario", f"${precio_un:.2f}")
            col_info2.metric("Disponible en Stock", f"{stock_act} un.")
           
            if precio_un == 0.0:
                st.warning("⚠️ Este producto tiene precio $0.00. Pide al Administrador que actualice el precio en el catálogo.")

            cant_venta = st.number_input("Cantidad a vender", min_value=1, max_value=max(1, stock_act), step=1)
           
            # Cálculo total en tiempo real
            total_cobro = cant_venta * precio_un
            st.subheader(f"💰 Total a cobrar: **${total_cobro:.2f}**")
           
            if stock_act <= 0:
                st.error("⚠️ Producto agotado en inventario.")
            else:
                if st.button("🛍️ Confirmar Venta", use_container_width=True):
                    st.session_state.inventario.loc[idx, "Stock"] -= cant_venta
                   
                    ganancia = cant_venta * (precio_un - costo_un)
                   
                    nueva_vta = pd.DataFrame([{
                        "Producto": prod_sel,
                        "Cantidad": cant_venta,
                        "Total ($)": total_cobro,
                        "Ganancia ($)": ganancia
                    }])
                   
                    st.session_state.ventas = pd.concat([st.session_state.ventas, nueva_vta], ignore_index=True)
                   
                    guardar_datos(st.session_state.inventario, ARCHIVO_INVENTARIO)
                    guardar_datos(st.session_state.ventas, ARCHIVO_VENTAS)
                   
                    st.success(f"¡Venta registrada con éxito! Total: ${total_cobro:.2f}")
                    st.rerun()

# --- VISTA 2: ADMINISTRADOR ---
else:
    st.title("📊 Panel de Administración")
    clave = st.sidebar.text_input("Contraseña de Admin", type="password")
   
    if clave == "1234":
        inv = st.session_state.inventario
        ventas = st.session_state.ventas

        val_inv = (inv["Stock"] * inv["Precio Venta ($)"]).sum() if not inv.empty else 0.0
        ganancia_estimada = (inv["Stock"] * inv["Ganancia Un. ($)"]).sum() if not inv.empty else 0.0
        ganancia_real = ventas["Ganancia ($)"].sum() if not ventas.empty else 0.0
        total_prods = len(inv)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Valor Total Inventario", f"${val_inv:.2f}")
        c2.metric("Ganancia Est. en Stock", f"${ganancia_estimada:.2f}")
        c3.metric("Ganancia Real Acumulada", f"${ganancia_real:.2f}")
        c4.metric("Productos Registrados", total_prods)

        st.divider()

        tab1, tab2, tab3 = st.tabs(["📦 Crear Producto", "✏️ Editar / Borrar Productos", "📜 Historial Ventas"])

        with tab1:
            st.subheader("➕ Agregar Nuevo Producto")
            with st.form("form_producto", clear_on_submit=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    nombre = st.text_input("Nombre del Producto")
                    categoria = st.selectbox("Categoría", ["Helados", "Accesorios / Bisutería", "Otros"])
                    stock = st.number_input("Stock Inicial", min_value=0, step=1)
                with col_b:
                    costo = st.number_input("Costo de Producción / Compra ($)", min_value=0.0, step=0.05, format="%.2f")
                    precio = st.number_input("Precio de Venta ($)", min_value=0.0, step=0.05, format="%.2f")
                    guardar = st.form_submit_button("Guardar Producto")

            if guardar and nombre:
                ganancia_un = precio - costo
                nuevo_prod = pd.DataFrame([{
                    "Producto": nombre,
                    "Categoría": categoria,
                    "Stock": stock,
                    "Costo ($)": costo,
                    "Precio Venta ($)": precio,
                    "Ganancia Un. ($)": ganancia_un
                }])
                st.session_state.inventario = pd.concat([st.session_state.inventario, nuevo_prod], ignore_index=True)
                guardar_datos(st.session_state.inventario, ARCHIVO_INVENTARIO)
                st.success(f"¡Producto '{nombre}' guardado!")
                st.rerun()

        with tab2:
            st.subheader("✏️ Modificar o Eliminar Productos Existentes")
            if inv.empty:
                st.info("No hay productos cargados.")
            else:
                prod_edit = st.selectbox("Selecciona producto a corregir", inv["Producto"].tolist())
                idx_e = inv[inv["Producto"] == prod_edit].index[0]
               
                col_e1, col_e2, col_e3, col_e4 = st.columns(4)
                nuevo_stock = col_e1.number_input("Stock", value=int(inv.loc[idx_e, "Stock"]), min_value=0)
                nuevo_costo = col_e2.number_input("Costo ($)", value=float(inv.loc[idx_e, "Costo ($)"]), min_value=0.0, format="%.2f")
                nuevo_precio = col_e3.number_input("Precio Venta ($)", value=float(inv.loc[idx_e, "Precio Venta ($)"]), min_value=0.0, format="%.2f")
               
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("💾 Actualizar Producto"):
                    st.session_state.inventario.loc[idx_e, "Stock"] = nuevo_stock
                    st.session_state.inventario.loc[idx_e, "Costo ($)"] = nuevo_costo
                    st.session_state.inventario.loc[idx_e, "Precio Venta ($)"] = nuevo_precio
                    st.session_state.inventario.loc[idx_e, "Ganancia Un. ($)"] = nuevo_precio - nuevo_costo
                    guardar_datos(st.session_state.inventario, ARCHIVO_INVENTARIO)
                    st.success("¡Producto actualizado correctamente!")
                    st.rerun()
                   
                if col_btn2.button("🗑️ Eliminar Producto"):
                    st.session_state.inventario = st.session_state.inventario.drop(idx_e).reset_index(drop=True)
                    guardar_datos(st.session_state.inventario, ARCHIVO_INVENTARIO)
                    st.warning("Producto eliminado.")
                    st.rerun()

            st.subheader("📋 Inventario Completo")
            st.dataframe(st.session_state.inventario, use_container_width=True)

        with tab3:
            st.subheader("📜 Registro Completo de Ventas")
            st.dataframe(ventas, use_container_width=True)

    else:
        st.warning("Ingresa la contraseña de administrador en el menú lateral para ver este panel.")

