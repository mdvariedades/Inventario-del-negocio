import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="MD Variedades - Inventario", page_icon="📦", layout="centered")

st.title("📦 MD Variedades")
st.subheader("Control de Inventario y Finanzas")

menu = st.sidebar.selectbox("Menú Principal", ["Inventario", "Registrar Venta", "Resumen Financiero"])

if 'inventario' not in st.session_state:
    st.session_state['inventario'] = pd.DataFrame(columns=["Producto", "Cantidad", "Precio Venta ($)", "Imagen"])

if 'ventas' not in st.session_state:
    st.session_state['ventas'] = pd.DataFrame(columns=["Fecha", "Producto", "Cantidad", "Total ($)"])

if menu == "Inventario":
    st.header("Gestión de Inventario")
    
    with st.form("form_producto", clear_on_submit=True):
        nombre = st.text_input("Nombre del Producto")
        cantidad = st.number_input("Cantidad en Stock", min_value=0, step=1)
        precio = st.number_input("Precio de Venta ($)", min_value=0.0, format="%.2f")
        imagen_subida = st.file_uploader("Subir foto del producto", type=["png", "jpg", "jpeg"])
        
        submit = st.form_submit_button("Guardar Producto")
        
        if submit and nombre:
            # Guardamos la imagen si el usuario la subió, o un texto indicando que no hay
            img_nombre = imagen_subida.name if imagen_subida is not None else "Sin imagen"
            
            nuevo_prod = pd.DataFrame([[nombre, cantidad, precio, img_nombre]], columns=["Producto", "Cantidad", "Precio Venta ($)", "Imagen"])
            st.session_state['inventario'] = pd.concat([st.session_state['inventario'], nuevo_prod], ignore_index=True)
            st.success(f"¡Producto '{nombre}' guardado con éxito!")

    st.subheader("Productos Actuales")
    if not st.session_state['inventario'].empty:
        st.dataframe(st.session_state['inventario'], use_container_width=True)
    else:
        st.info("Aún no hay productos registrados.")

elif menu == "Registrar Venta":
    st.header("Registrar una Venta")
    
    if st.session_state['inventario'].empty:
        st.warning("Primero debes agregar productos en la sección de Inventario.")
    else:
        productos_lista = st.session_state['inventario']['Producto'].tolist()
        prod_seleccionado = st.selectbox("Selecciona el Producto", productos_lista)
        cant_vendida = st.number_input("Cantidad Vendida", min_value=1, step=1)
        
        if st.button("Procesar Venta"):
            idx = st.session_state['inventario'][st.session_state['inventario']['Producto'] == prod_seleccionado].index[0]
            stock_actual = st.session_state['inventario'].loc[idx, "Cantidad"]
            precio_v = st.session_state['inventario'].loc[idx, "Precio Venta ($)"]
            
            if cant_vendida > stock_actual:
                st.error("No hay suficiente stock disponible para esta venta.")
            else:
                st.session_state['inventario'].loc[idx, "Cantidad"] = stock_actual - cant_vendida
                total_venta = cant_vendida * precio_v
                
                nueva_venta = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M"), prod_seleccionado, cant_vendida, total_venta]], 
                                            columns=["Fecha", "Producto", "Cantidad", "Total ($)"])
                st.session_state['ventas'] = pd.concat([st.session_state['ventas'], nueva_venta], ignore_index=True)
                st.success(f"¡Venta registrada con éxito! Total: ${total_venta:.2f}")

elif menu == "Resumen Financiero":
    st.header("Resumen Financiero y Ventas")
    
    if not st.session_state['ventas'].empty:
        st.dataframe(st.session_state['ventas'], use_container_width=True)
        total_ingresos = st.session_state['ventas']['Total ($)'].sum()
        st.metric(label="Ingresos Totales por Ventas", value=f"${total_ingresos:.2f}")
    else:
        st.info("Aún no se han registrado ventas.")
