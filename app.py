
import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from PIL import Image

app = Flask(__name__)

# Configuración de base de datos SQLite y carpeta de carga de archivos
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'sistema_financiero.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# ==========================================
# 1. MODELOS DE BASE DE DATOS
# ==========================================

class Producto(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    codigo_barras = db.Column(db.String(100), unique=True, nullable=True)
    nombre = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50), nullable=True)
    ubicacion = db.Column(db.String(50), nullable=True)
    
    stock_actual = db.Column(db.Integer, default=0)
    stock_minimo = db.Column(db.Integer, default=5)
    
    costo_promedio = db.Column(db.Float, default=0.0)
    precio_venta = db.Column(db.Float, nullable=False)
    imagen_url = db.Column(db.String(255), nullable=True)

class Proveedor(db.Model):
    __tablename__ = 'proveedores'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    contacto = db.Column(db.String(100), nullable=True)
    condiciones_pago = db.Column(db.String(100), nullable=True)

class Compra(db.Model):
    __tablename__ = 'compras'
    id = db.Column(db.Integer, primary_key=True)
    proveedor_id = db.Column(db.Integer, db.ForeignKey('proveedores.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    costo_unitario = db.Column(db.Float, nullable=False)
    monto_total = db.Column(db.Float, nullable=False)
    monto_pendiente = db.Column(db.Float, default=0.0)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    pagado = db.Column(db.Boolean, default=False)
    fecha_vencimiento = db.Column(db.DateTime, nullable=True)

class Venta(db.Model):
    __tablename__ = 'ventas'
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(100), default="Cliente General")
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    costo_unitario_historico = db.Column(db.Float, nullable=False)
    monto_total = db.Column(db.Float, nullable=False)
    monto_pendiente = db.Column(db.Float, default=0.0)
    forma_pago = db.Column(db.String(50), nullable=False) # Efectivo, Transferencia, Crédito
    pagado = db.Column(db.Boolean, default=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

# Crear tablas en la base de datos
with app.app_context():
    db.create_all()

# ==========================================
# FUNCIONES AUXILIARES (OPTIMIZACIÓN DE IMAGEN)
# ==========================================

def optimizar_y_guardar_imagen(file_storage, filename):
    """Comprime la imagen recibida y la convierte a formato WebP ligero."""
    img = Image.open(file_storage)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{filename}.webp")
    img.save(output_path, "WEBP", optimize=True, quality=80)
    return f"/uploads/{filename}.webp"

# ==========================================
# 2. RUTAS DEL SISTEMA
# ==========================================

# --- GESTIÓN DE INVENTARIO Y CATÁLOGO VISUAL ---

@app.route('/productos', methods=['POST'])
def crear_producto():
    data = request.form
    imagen = request.files.get('imagen')
    
    sku = data.get('sku')
    if Producto.query.filter_by(sku=sku).first():
        return jsonify({"error": "El SKU ya existe"}), 400

    imagen_path = None
    if imagen:
        imagen_path = optimizar_y_guardar_imagen(imagen, f"prod_{sku}")

    nuevo_producto = Producto(
        sku=sku,
        codigo_barras=data.get('codigo_barras'),
        nombre=data.get('nombre'),
        categoria=data.get('categoria'),
        ubicacion=data.get('ubicacion'),
        stock_actual=int(data.get('stock_actual', 0)),
        stock_minimo=int(data.get('stock_minimo', 5)),
        costo_promedio=float(data.get('costo_promedio', 0.0)),
        precio_venta=float(data.get('precio_venta')),
        imagen_url=imagen_path
    )
    db.session.add(nuevo_producto)
    db.session.commit()
    return jsonify({"mensaje": "Producto creado con éxito", "id": nuevo_producto.id}), 201

@app.route('/productos/alertas', methods=['GET'])
def alertas_stock():
    """Alertas automáticas de reabastecimiento."""
    productos = Producto.query.filter(Producto.stock_actual <= Producto.stock_minimo).all()
    resultado = [{
        "sku": p.sku,
        "nombre": p.nombre,
        "stock_actual": p.stock_actual,
        "stock_minimo": p.stock_minimo
    } for p in productos]
    return jsonify({"alertas_reabastecimiento": resultado}), 200

# --- MÓDULO DE COMPRAS (ENTRADAS Y PROVEEDORES) ---

@app.route('/proveedores', methods=['POST'])
def crear_proveedor():
    data = request.json
    nuevo = Proveedor(
        nombre=data.get('nombre'),
        contacto=data.get('contacto'),
        condiciones_pago=data.get('condiciones_pago')
    )
    db.session.add(nuevo)
    db.session.commit()
    return jsonify({"mensaje": "Proveedor registrado", "id": nuevo.id}), 201

@app.route('/compras', methods=['POST'])
def registrar_compra():
    data = request.json
    producto_id = data.get('producto_id')
    cantidad = int(data.get('cantidad'))
    costo_unitario = float(data.get('costo_unitario'))
    es_credito = data.get('es_credito', False)
    
    producto = Producto.query.get_or_404(producto_id)

    # Recálculo de Costo Promedio Ponderado
    costo_total_existente = producto.stock_actual * producto.costo_promedio
    costo_total_nuevo = cantidad * costo_unitario
    nuevo_stock = producto.stock_actual + cantidad

    if nuevo_stock > 0:
        producto.costo_promedio = (costo_total_existente + costo_total_nuevo) / nuevo_stock
    
    producto.stock_actual = nuevo_stock
    monto_total = cantidad * costo_unitario

    nueva_compra = Compra(
        proveedor_id=data.get('proveedor_id'),
        producto_id=producto_id,
        cantidad=cantidad,
        costo_unitario=costo_unitario,
        monto_total=monto_total,
        monto_pendiente=monto_total if es_credito else 0.0,
        pagado=not es_credito
    )
    
    db.session.add(nueva_compra)
    db.session.commit()
    return jsonify({"mensaje": "Compra registrada y costo promedio recalculado"}), 201

# --- MÓDULO DE VENTAS (PUNTO DE VENTA) ---

@app.route('/ventas', methods=['POST'])
def registrar_venta():
    data = request.json
    producto_id = data.get('producto_id')
    cantidad = int(data.get('cantidad'))
    forma_pago = data.get('forma_pago', 'Efectivo')
    
    producto = Producto.query.get_or_404(producto_id)

    if producto.stock_actual < cantidad:
        return jsonify({"error": f"Stock insuficiente. Disponible: {producto.stock_actual}"}), 400

    # Descuento en tiempo real
    producto.stock_actual -= cantidad
    monto_total = cantidad * producto.precio_venta
    es_credito = (forma_pago.lower() == 'crédito' or forma_pago.lower() == 'credito')

    nueva_venta = Venta(
        cliente=data.get('cliente', 'Cliente General'),
        producto_id=producto_id,
        cantidad=cantidad,
        precio_unitario=producto.precio_venta,
        costo_unitario_historico=producto.costo_promedio,
        monto_total=monto_total,
        monto_pendiente=monto_total if es_credito else 0.0,
        forma_pago=forma_pago,
        pagado=not es_credito
    )

    db.session.add(nueva_venta)
    db.session.commit()

    return jsonify({
        "mensaje": "Venta procesada con éxito",
        "comprobante": {
            "ticket_id": nueva_venta.id,
            "fecha": nueva_venta.fecha.isoformat(),
            "cliente": nueva_venta.cliente,
            "producto": producto.nombre,
            "cantidad": cantidad,
            "total": monto_total,
            "forma_pago": forma_pago
        }
    }), 201

# --- CUENTAS POR PAGAR Y POR COBRAR ---

@app.route('/cuentas-por-pagar', methods=['GET', 'POST'])
def cuentas_por_pagar():
    if request.method == 'GET':
        compras_pendientes = Compra.query.filter_by(pagado=False).all()
        resultado = [{
            "compra_id": c.id,
            "proveedor_id": c.proveedor_id,
            "monto_total": c.monto_total,
            "monto_pendiente": c.monto_pendiente,
            "fecha": c.fecha.isoformat()
        } for c in compras_pendientes]
        return jsonify({"cuentas_por_pagar": resultado}), 200

    if request.method == 'POST':
        # Registrar abono/pago a proveedor
        data = request.json
        compra = Compra.query.get_or_404(data.get('compra_id'))
        monto_abono = float(data.get('monto_abono'))

        compra.monto_pendiente -= monto_abono
        if compra.monto_pendiente <= 0:
            compra.monto_pendiente = 0.0
            compra.pagado = True
            
        db.session.commit()
        return jsonify({"mensaje": "Abono registrado a proveedor", "saldo_pendiente": compra.monto_pendiente}), 200

@app.route('/cuentas-por-cobrar', methods=['GET', 'POST'])
def cuentas_por_cobrar():
    if request.method == 'GET':
        ventas_pendientes = Venta.query.filter_by(pagado=False).all()
        resultado = [{
            "venta_id": v.id,
            "cliente": v.cliente,
            "monto_total": v.monto_total,
            "monto_pendiente": v.monto_pendiente,
            "fecha": v.fecha.isoformat()
        } for v in ventas_pendientes]
        return jsonify({"cuentas_por_cobrar": resultado}), 200

    if request.method == 'POST':
        # Registrar abono/pago de cliente
        data = request.json
        venta = Venta.query.get_or_404(data.get('venta_id'))
        monto_abono = float(data.get('monto_abono'))

        venta.monto_pendiente -= monto_abono
        if venta.monto_pendiente <= 0:
            venta.monto_pendiente = 0.0
            venta.pagado = True

        db.session.commit()
        return jsonify({"mensaje": "Abono de cliente recibido", "saldo_pendiente": venta.monto_pendiente}), 200

# --- MOTOR FINANCIERO Y CÁLCULO DE GANANCIAS ---

@app.route('/reporte-financiero', methods=['GET'])
def reporte_financiero():
    ventas = Venta.query.all()
    
    ingresos_totales = sum(v.monto_total for v in ventas)
    costos_totales = sum(v.cantidad * v.costo_unitario_historico for v in ventas)
    ganancia_bruta = ingresos_totales - costos_totales

    # Cuentas pendientes
    por_cobrar = sum(v.monto_pendiente for v in Venta.query.filter_by(pagado=False).all())
    por_pagar = sum(c.monto_pendiente for c in Compra.query.filter_by(pagado=False).all())

    # Valoración actual del inventario
    productos = Producto.query.all()
    valor_inventario = sum(p.stock_actual * p.costo_promedio for p in productos)

    return jsonify({
        "ingresos_totales": round(ingresos_totales, 2),
        "costos_totales_mercancia": round(costos_totales, 2),
        "ganancia_bruta": round(ganancia_bruta, 2),
        "valor_actual_inventario": round(valor_inventario, 2),
        "cuentas_por_cobrar_pendientes": round(por_cobrar, 2),
        "cuentas_por_pagar_pendientes": round(por_pagar, 2)
    }), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
