import streamlit as st
import pandas as pd

st.set_page_config(page_title="Gestión Financiera", layout="wide")
st.title("📊 Mi Panel Financiero e Inventario")

# Inicializar inventario y ventas en session_state para mantener los datos en la sesión
if "inventario" not in st.session_state:
    st.session_state.inventario = pd.DataFrame(
        columns=["Producto", "Categoría", "Stock", "Costo ($)", "Precio Venta ($)", "Ganancia Un. ($)"]
    )

if "ventas" not in st.session_state:
    st.session_state.ventas = pd.DataFrame(
        columns=["Producto", "Cantidad", "Total ($)", "Ganancia ($)"]
    )

# --- RESUMEN Y MÉTRICAS FINANCIERAS (KPIs) ---
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

# --- PESTAÑAS DE TRABAJO ---
tab1, tab2 = st.tabs(["📦 Registro de Productos e Inventario", "🛒 Registrar Venta"])

with tab1:
    st.subheader("➕ Agregar Producto al Inventario")
   
    with st.form("form_producto", clear_on_submit=True):
        col_a, col_b = st.columns(2)
       
        with col_a:
            nombre = st.text_input("Nombre del producto")
            categoria = st.selectbox("Categoría", ["Helados", "Accesorios / Bisutería", "Otros"])
            stock = st.number_input("Cantidad inicial en stock", min_value=0, step=1)
           
        with col_b:
            costo = st.number_input("Costo de producción/compra ($)", min_value=0.0, step=0.05, format="%.2f")
            precio = st.number_input("Precio de venta ($)", min_value=0.0, step=0.05, format="%.2f")
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
        st.success(f"¡Producto '{nombre}' guardado con éxito con un margen de ${ganancia_un:.2f} por unidad!")
        st.rerun()

    st.subheader("📋 Inventario Actual")
    st.dataframe(st.session_state.inventario, use_container_width=True)

with tab2:
    st.subheader("🛒 Registrar Venta")
   
    if st.session_state.inventario.empty:
        st.info("Primero agrega productos en la pestaña de inventario.")
    else:
        prod_lista = st.session_state.inventario["Producto"].tolist()
        prod_sel = st.selectbox("Selecciona el producto a vender", prod_lista)
       
        # Buscar índice del producto seleccionado
        idx = st.session_state.inventario[st.session_state.inventario["Producto"] == prod_sel].index[0]
        stock_actual = st.session_state.inventario.loc[idx, "Stock"]
        precio_un = st.session_state.inventario.loc[idx, "Precio Venta ($)"]
        costo_un = st.session_state.inventario.loc[idx, "Costo ($)"]
       
        cant_venta = st.number_input(
            "Cantidad a vender",
            min_value=1,
            max_value=int(stock_actual) if stock_actual > 0 else 1,
            step=1
        )
       
        if stock_actual <= 0:
            st.error("⚠️ Este producto no tiene unidades disponible en stock.")
        else:
            if st.button("Confirmar y Descontar Venta"):
                # Actualizar el stock disponible
                st.session_state.inventario.loc[idx, "Stock"] -= cant_venta
               
                # Calcular montos
                total = cant_venta * precio_un
                ganancia = cant_venta * (precio_un - costo_un)
               
                # Guardar venta
                nueva_venta = pd.DataFrame([{
                    "Producto": prod_sel,
                    "Cantidad": cant_venta,
                    "Total ($)": total,
                    "Ganancia ($)": ganancia
                }])
                st.session_state.ventas = pd.concat([st.session_state.ventas, nueva_venta], ignore_index=True)
                st.success(f"Venta registrada: {cant_venta}x {prod_sel} | Total: ${total:.2f} | Ganancia: ${ganancia:.2f}")
                st.rerun()

    st.subheader("📜 Historial de Ventas")
    st.dataframe(st.session_state.ventas, use_container_width=True)

