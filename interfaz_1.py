"""
interfaz.py — Operación Rescate: Cumbres Salvajes
CAPA 2: Interfaz Gráfica con Drag & Drop
Autor: Andrew (con Mateo)
"""

import pygame
import sys
import math
from typing import Optional

# ─────────────────────────────────────────────
#  IMPORTAR EL MOTOR LÓGICO (de Solange)
# ─────────────────────────────────────────────
try:
    from Algoritmo_1 import resolver_distribucion
    ALGORITMO_DISPONIBLE = True
except ImportError:
    ALGORITMO_DISPONIBLE = False
    print("⚠️  Algoritmo_1.py no encontrado. Modo visual solamente.")


# ─────────────────────────────────────────────
#  CONSTANTES Y COLORES
# ─────────────────────────────────────────────
ANCHO, ALTO = 1100, 700

# Paleta del juego (estilo cálido/aventura)
COLOR_FONDO        = (30,  40,  55)
COLOR_PANEL        = (45,  58,  75)
COLOR_PANEL_BORDE  = (80, 100, 130)
COLOR_TARJETA      = (55,  72,  95)
COLOR_TARJETA_HOV  = (70,  92, 120)
COLOR_TARJETA_DRAG = (90, 120, 155)
COLOR_ZONA         = (38,  50,  65)
COLOR_ZONA_ACTIVA  = (50,  80,  60)
COLOR_ZONA_BORDE   = (70,  90, 110)
COLOR_TEXTO        = (220, 225, 235)
COLOR_SUBTEXTO     = (140, 155, 175)
COLOR_ACENTO       = (255, 185,  60)   # Dorado cálido
COLOR_VERDE        = ( 80, 200, 100)
COLOR_AMARILLO     = (240, 200,  50)
COLOR_ROJO         = (220,  70,  60)
COLOR_BOTON        = ( 60, 130, 100)
COLOR_BOTON_HOV    = ( 75, 160, 120)
COLOR_BOTON_TEXTO  = (220, 240, 225)

ROLES_COLORES = {
    "Rastreador":  (100, 180, 120),
    "Paramédico":  ( 80, 150, 220),
    "Escalador":   (220, 140,  60),
    "Cargador":    (180,  90, 200),
}


# ─────────────────────────────────────────────
#  CONFIGURACIÓN DEL NIVEL
#  ⚠️  JORDY: solo modifica estos valores por nivel
# ─────────────────────────────────────────────
CANTIDAD_EQUIPOS    = 2   # k = cuántos equipos se forman
PERSONAS_POR_EQUIPO = 3   # cuántas personas van en cada equipo

# ─────────────────────────────────────────────
#  DATOS DE PRUEBA (rescatistas del juego)
# ─────────────────────────────────────────────
RESCATISTAS_NIVEL_1 = [
    {"nombre": "Ana",    "habilidad": 72, "rol": "Rastreadora"},
    {"nombre": "Luis",   "habilidad": 68, "rol": "Paramédico"},
    {"nombre": "Marta",  "habilidad": 75, "rol": "Escaladora"},
    {"nombre": "Carlos", "habilidad": 40, "rol": "Cargador"},
    {"nombre": "Sofía",  "habilidad": 55, "rol": "Rastreadora"},
    {"nombre": "Tomás",  "habilidad": 80, "rol": "Escalador"},
]

TAMANO_EQUIPO = PERSONAS_POR_EQUIPO   # se adapta automáticamente


# ─────────────────────────────────────────────
#  CLASE: TARJETA DE RESCATISTA
# ─────────────────────────────────────────────
class TarjetaRescatista:
    ANCHO  = 120
    ALTO   = 145
    RADIO  = 10

    def __init__(self, rescatista: dict, x: int, y: int):
        self.rescatista  = rescatista
        self.origen_x    = x
        self.origen_y    = y
        self.rect        = pygame.Rect(x, y, self.ANCHO, self.ALTO)
        self.arrastrando = False
        self.en_zona     = None          # zona donde está colocada
        self.offset_x    = 0
        self.offset_y    = 0
        self.hover       = False
        self.animando    = False
        self.anim_progreso = 1.0         # 0.0 → 1.0 (para animación de retorno)

    # ── Propiedades ──────────────────────────
    @property
    def nombre(self) -> str:
        return self.rescatista["nombre"]

    @property
    def habilidad(self) -> int:
        return self.rescatista["habilidad"]

    @property
    def rol(self) -> str:
        return self.rescatista.get("rol", "?")

    # ── Lógica de arrastre ───────────────────
    def iniciar_arrastre(self, mouse_x: int, mouse_y: int) -> None:
        if self.en_zona:
            self.en_zona.quitar_tarjeta(self)
            self.en_zona = None
        self.arrastrando = True
        self.offset_x    = self.rect.x - mouse_x
        self.offset_y    = self.rect.y - mouse_y

    def mover(self, mouse_x: int, mouse_y: int) -> None:
        if self.arrastrando:
            self.rect.x = mouse_x + self.offset_x
            self.rect.y = mouse_y + self.offset_y

    def soltar(self, zonas: list) -> bool:
        """Intenta colocar la tarjeta en una zona. Devuelve True si lo logró."""
        self.arrastrando = False
        for zona in zonas:
            if zona.rect.colliderect(self.rect) and zona.puede_recibir():
                zona.recibir_tarjeta(self)
                self.en_zona = zona
                self.rect.center = zona.siguiente_posicion()
                return True
        # Si no cayó en ninguna zona → animar retorno al origen
        self._iniciar_retorno()
        return False

    def _iniciar_retorno(self) -> None:
        self.animando      = True
        self.anim_progreso = 0.0
        self.anim_inicio_x = self.rect.x
        self.anim_inicio_y = self.rect.y

    def actualizar(self) -> None:
        """Actualiza la animación de retorno al origen."""
        if self.animando:
            self.anim_progreso = min(self.anim_progreso + 0.08, 1.0)
            t = _ease_out(self.anim_progreso)
            self.rect.x = int(self.anim_inicio_x + (self.origen_x - self.anim_inicio_x) * t)
            self.rect.y = int(self.anim_inicio_y + (self.origen_y - self.anim_inicio_y) * t)
            if self.anim_progreso >= 1.0:
                self.animando = False

    # ── Dibujado ─────────────────────────────
    def dibujar(self, surface: pygame.Surface) -> None:
        color_rol = ROLES_COLORES.get(self.rol.replace("a", "").replace("o", ""), (120, 140, 160))

        if self.arrastrando:
            color_fondo = COLOR_TARJETA_DRAG
            sombra = pygame.Surface((self.ANCHO + 10, self.ALTO + 10), pygame.SRCALPHA)
            pygame.draw.rect(sombra, (0, 0, 0, 80), sombra.get_rect(), border_radius=self.RADIO)
            surface.blit(sombra, (self.rect.x - 5, self.rect.y + 8))
        elif self.hover:
            color_fondo = COLOR_TARJETA_HOV
        else:
            color_fondo = COLOR_TARJETA

        # Fondo de la tarjeta
        pygame.draw.rect(surface, color_fondo, self.rect, border_radius=self.RADIO)
        pygame.draw.rect(surface, COLOR_PANEL_BORDE, self.rect, width=2, border_radius=self.RADIO)

        # Barra de color del rol (arriba)
        barra = pygame.Rect(self.rect.x + 2, self.rect.y + 2, self.ANCHO - 4, 6)
        pygame.draw.rect(surface, color_rol, barra, border_radius=4)

        # Ícono circular del nivel (centro superior)
        cx = self.rect.centerx
        cy = self.rect.y + 48
        pygame.draw.circle(surface, color_rol, (cx, cy), 26)
        pygame.draw.circle(surface, COLOR_PANEL_BORDE, (cx, cy), 26, 2)
        _dibujar_texto(surface, str(self.habilidad), cx, cy, 20, COLOR_TEXTO, negrita=True)

        # Nombre
        _dibujar_texto(surface, self.nombre, cx, self.rect.y + 88, 14, COLOR_TEXTO, negrita=True)

        # Rol
        _dibujar_texto(surface, self.rol, cx, self.rect.y + 108, 11, color_rol)

        # Barra de habilidad (abajo)
        barra_y    = self.rect.y + 126
        barra_rect = pygame.Rect(self.rect.x + 10, barra_y, self.ANCHO - 20, 8)
        pygame.draw.rect(surface, COLOR_FONDO, barra_rect, border_radius=4)
        fill_w = int((self.ANCHO - 20) * self.habilidad / 100)
        fill_color = _color_por_nivel(self.habilidad)
        pygame.draw.rect(surface, fill_color,
                         pygame.Rect(self.rect.x + 10, barra_y, fill_w, 8),
                         border_radius=4)


# ─────────────────────────────────────────────
#  CLASE: ZONA DE EQUIPO (slot destino)
# ─────────────────────────────────────────────
class ZonaEquipo:
    SLOTS = PERSONAS_POR_EQUIPO   # se adapta al nivel definido por Jordy

    def __init__(self, x: int, y: int, ancho: int, alto: int, etiqueta: str = "Expedición"):
        self.rect     = pygame.Rect(x, y, ancho, alto)
        self.etiqueta = etiqueta
        self.tarjetas: list[TarjetaRescatista] = []
        self.activa   = False              # True cuando hay una tarjeta encima

    def puede_recibir(self) -> bool:
        return len(self.tarjetas) < self.SLOTS

    def recibir_tarjeta(self, tarjeta: TarjetaRescatista) -> None:
        self.tarjetas.append(tarjeta)

    def quitar_tarjeta(self, tarjeta: TarjetaRescatista) -> None:
        if tarjeta in self.tarjetas:
            self.tarjetas.remove(tarjeta)

    def siguiente_posicion(self) -> tuple[int, int]:
        """Calcula el centro donde se colocará la próxima tarjeta."""
        idx  = len(self.tarjetas) - 1
        cols = 2
        col  = idx % cols
        fila = idx // cols
        x = self.rect.x + 15 + col * (TarjetaRescatista.ANCHO + 10) + TarjetaRescatista.ANCHO // 2
        y = self.rect.y + 55 + fila * (TarjetaRescatista.ALTO  + 8)  + TarjetaRescatista.ALTO  // 2
        return (x, y)

    def habilidades(self) -> list[int]:
        return [t.habilidad for t in self.tarjetas]

    def desviacion(self) -> int:
        h = self.habilidades()
        if len(h) <= 1:
            return 0
        return max(h) - min(h)

    def dibujar(self, surface: pygame.Surface) -> None:
        # Fondo de la zona
        color_fondo = COLOR_ZONA_ACTIVA if self.activa else COLOR_ZONA
        pygame.draw.rect(surface, color_fondo, self.rect, border_radius=12)
        pygame.draw.rect(surface, COLOR_ZONA_BORDE, self.rect, width=2, border_radius=12)

        # Etiqueta superior
        _dibujar_texto(surface, self.etiqueta,
                       self.rect.centerx, self.rect.y + 20, 15, COLOR_ACENTO, negrita=True)

        # Slots vacíos (guías visuales)
        cols = 2
        for i in range(self.SLOTS):
            if i < len(self.tarjetas):
                continue
            col  = i % cols
            fila = i // cols
            sx = self.rect.x + 15 + col * (TarjetaRescatista.ANCHO + 10)
            sy = self.rect.y + 50 + fila * (TarjetaRescatista.ALTO  + 8)
            slot_rect = pygame.Rect(sx, sy, TarjetaRescatista.ANCHO, TarjetaRescatista.ALTO)
            pygame.draw.rect(surface, (50, 65, 82), slot_rect, border_radius=10)
            pygame.draw.rect(surface, (65, 85, 105), slot_rect, width=1, border_radius=10)
            _dibujar_texto(surface, "+", slot_rect.centerx, slot_rect.centery,
                           28, (70, 90, 110))

        # Contador de miembros
        texto_cnt = f"{len(self.tarjetas)}/{self.SLOTS} rescatistas"
        _dibujar_texto(surface, texto_cnt,
                       self.rect.centerx, self.rect.bottom - 18, 12, COLOR_SUBTEXTO)


# ─────────────────────────────────────────────
#  CLASE: HARMONY METER (barra de armonía)
# ─────────────────────────────────────────────
class HarmonyMeter:
    def __init__(self, x: int, y: int, ancho: int, alto: int):
        self.rect           = pygame.Rect(x, y, ancho, alto)
        self.valor_actual   = 0.0    # 0.0 = máxima armonía, 1.0 = caos total
        self.valor_objetivo = 0.0
        self.desviacion     = 0
        self.optimo         = 0

    def actualizar_desde_zona(self, zona: ZonaEquipo, optimo: int) -> None:
        self.desviacion     = zona.desviacion()
        self.optimo         = optimo
        rango_max           = 100
        self.valor_objetivo = min(self.desviacion / rango_max, 1.0)

    def actualizar(self) -> None:
        """Animación suave hacia el valor objetivo."""
        diff = self.valor_objetivo - self.valor_actual
        self.valor_actual += diff * 0.06

    def dibujar(self, surface: pygame.Surface) -> None:
        # Fondo del panel
        pygame.draw.rect(surface, COLOR_PANEL, self.rect, border_radius=14)
        pygame.draw.rect(surface, COLOR_PANEL_BORDE, self.rect, width=2, border_radius=14)

        cx = self.rect.centerx
        cy = self.rect.y + 30
        _dibujar_texto(surface, "HARMONY METER", cx, cy, 13, COLOR_ACENTO, negrita=True)

        # Arco del medidor (estilo velocímetro)
        radio        = 60
        centro       = (cx, self.rect.y + 115)
        angulo_min   = 210          # grados (pygame: 0 = derecha, sentido horario)
        angulo_max   = -30
        angulo_rango = angulo_min - angulo_max

        # Fondo del arco
        _dibujar_arco(surface, centro, radio, angulo_min, angulo_max, (40, 55, 70), 12)

        # Arco de color (verde→amarillo→rojo)
        color_aguja  = _color_harmony(self.valor_actual)
        angulo_aguja = angulo_min - self.valor_actual * angulo_rango
        _dibujar_arco(surface, centro, radio, angulo_min, angulo_aguja, color_aguja, 12)

        # Aguja
        rad           = math.radians(-angulo_aguja)
        largo_aguja   = radio - 8
        px            = centro[0] + int(math.cos(rad) * largo_aguja)
        py            = centro[1] - int(math.sin(rad) * largo_aguja)
        pygame.draw.line(surface, COLOR_TEXTO, centro, (px, py), 3)
        pygame.draw.circle(surface, COLOR_TEXTO, centro, 6)

        # Texto de desviación
        _dibujar_texto(surface, f"Desviación: {self.desviacion}",
                       cx, self.rect.y + 185, 12, COLOR_SUBTEXTO)

        # Etiqueta de estado
        if self.valor_actual < 0.25:
            etiqueta, color = "ARMONIOSO ✓", COLOR_VERDE
        elif self.valor_actual < 0.55:
            etiqueta, color = "MODERADO", COLOR_AMARILLO
        else:
            etiqueta, color = "PELIGROSO ✗", COLOR_ROJO
        _dibujar_texto(surface, etiqueta, cx, self.rect.y + 205, 14, color, negrita=True)

        # Comparación con óptimo (si existe)
        if self.optimo > 0:
            _dibujar_texto(surface, f"Óptimo IA: {self.optimo}",
                           cx, self.rect.y + 225, 11, (100, 180, 120))


# ─────────────────────────────────────────────
#  CLASE: BOTÓN
# ─────────────────────────────────────────────
class Boton:
    def __init__(self, x: int, y: int, ancho: int, alto: int, texto: str):
        self.rect   = pygame.Rect(x, y, ancho, alto)
        self.texto  = texto
        self.hover  = False
        self.activo = True

    def manejar_evento(self, evento: pygame.event.Event) -> bool:
        if evento.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(evento.pos)
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if self.rect.collidepoint(evento.pos) and self.activo:
                return True
        return False

    def dibujar(self, surface: pygame.Surface) -> None:
        color = COLOR_BOTON_HOV if self.hover else COLOR_BOTON
        if not self.activo:
            color = (50, 60, 70)
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        pygame.draw.rect(surface, COLOR_PANEL_BORDE, self.rect, width=2, border_radius=10)
        _dibujar_texto(surface, self.texto,
                       self.rect.centerx, self.rect.centery,
                       14, COLOR_BOTON_TEXTO, negrita=True)


# ─────────────────────────────────────────────
#  SISTEMA DE PUNTUACIÓN (Andrew + Solange)
# ─────────────────────────────────────────────
def calcular_estrellas(desviacion_usuario: int, desviacion_optima: int) -> int:
    """
    Compara la solución manual del jugador vs el óptimo del algoritmo.
    Retorna 1, 2 o 3 estrellas.
    """
    if desviacion_optima == 0:
        return 3 if desviacion_usuario == 0 else 1

    ratio = desviacion_usuario / desviacion_optima
    if ratio <= 1.0:
        return 3    # ⭐⭐⭐ Igual o mejor que el óptimo
    elif ratio <= 1.5:
        return 2    # ⭐⭐   Hasta 50% peor
    else:
        return 1    # ⭐     Más del 50% peor


def dibujar_resultado(surface: pygame.Surface, estrellas: int,
                      desv_usuario: int, desv_optima: int) -> None:
    """Panel de resultado al finalizar la misión."""
    overlay = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surface.blit(overlay, (0, 0))

    panel = pygame.Rect(ANCHO // 2 - 200, ALTO // 2 - 180, 400, 360)
    pygame.draw.rect(surface, COLOR_PANEL, panel, border_radius=18)
    pygame.draw.rect(surface, COLOR_ACENTO, panel, width=3, border_radius=18)

    cx = panel.centerx
    _dibujar_texto(surface, "¡MISIÓN COMPLETADA!", cx, panel.y + 40, 22, COLOR_ACENTO, negrita=True)

    # Estrellas
    for i in range(3):
        color = COLOR_ACENTO if i < estrellas else (60, 70, 85)
        sx    = cx - 60 + i * 60
        pygame.draw.polygon(surface, color, _puntos_estrella(sx, panel.y + 110, 28))

    _dibujar_texto(surface, f"Tu desviación: {desv_usuario}", cx, panel.y + 170, 15, COLOR_TEXTO)
    _dibujar_texto(surface, f"Óptimo de la IA: {desv_optima}", cx, panel.y + 195, 15, COLOR_VERDE)

    gap  = abs(desv_usuario - desv_optima)
    msg  = "¡Igual que la IA!" if gap == 0 else f"Diferencia: {gap} puntos"
    _dibujar_texto(surface, msg, cx, panel.y + 225, 13, COLOR_SUBTEXTO)

    _dibujar_texto(surface, "Presiona R para reiniciar", cx, panel.y + 310, 13, COLOR_SUBTEXTO)


# ─────────────────────────────────────────────
#  JUEGO PRINCIPAL
# ─────────────────────────────────────────────
class JuegoOperacionRescate:

    def __init__(self):
        pygame.init()
        self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
        pygame.display.set_caption("Operación Rescate: Cumbres Salvajes")
        self.reloj    = pygame.time.Clock()
        self._inicializar()

    def _inicializar(self):
        """Crea todos los objetos del juego."""
        # Panel izquierdo: banco de rescatistas disponibles
        self.tarjetas: list[TarjetaRescatista] = []
        for i, datos in enumerate(RESCATISTAS_NIVEL_1):
            col = i % 2
            fil = i // 2
            x   = 20 + col * (TarjetaRescatista.ANCHO + 12)
            y   = 80  + fil * (TarjetaRescatista.ALTO  + 10)
            self.tarjetas.append(TarjetaRescatista(datos, x, y))

        # Zona central: expedición
        self.zona = ZonaEquipo(
            x=310, y=60,
            ancho=TarjetaRescatista.ANCHO * 2 + 50,
            alto=TarjetaRescatista.ALTO  * 2 + 110,
            etiqueta="ZONA DE EXPEDICIÓN"
        )

        # Panel derecho: Harmony Meter
        self.meter = HarmonyMeter(x=680, y=60, ancho=200, alto=260)

        # Botones
        self.btn_analizar = Boton(680, 340, 200, 45, "🔍 Analizar (IA)")
        self.btn_limpiar  = Boton(680, 400, 200, 45, "🔄 Limpiar")
        self.btn_enviar   = Boton(680, 460, 200, 45, "🚁 Enviar Equipo")

        # Estado
        self.arrastrada:  Optional[TarjetaRescatista] = None
        self.resultado_ia: Optional[dict] = None
        self.desv_optima:  int  = 0
        self.mostrar_resultado = False

    def manejar_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_r:
                    self._inicializar()
                if evento.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

            # ── Mouse Down: iniciar arrastre ──────────
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                mx, my = evento.pos
                # Verificar tarjetas de la zona primero (para sacarlas)
                for t in reversed(self.zona.tarjetas):
                    if t.rect.collidepoint(mx, my):
                        t.iniciar_arrastre(mx, my)
                        self.arrastrada = t
                        break
                else:
                    # Luego verificar banco de rescatistas
                    for t in reversed(self.tarjetas):
                        if t.rect.collidepoint(mx, my) and t.en_zona is None:
                            t.iniciar_arrastre(mx, my)
                            self.arrastrada = t
                            break

            # ── Mouse Move: mover tarjeta arrastrada ──
            if evento.type == pygame.MOUSEMOTION:
                if self.arrastrada:
                    self.arrastrada.mover(*evento.pos)
                # Hover en tarjetas del banco
                for t in self.tarjetas:
                    t.hover = t.rect.collidepoint(evento.pos) and not t.arrastrando
                # Zona activa si hay tarjeta encima
                self.zona.activa = (
                    self.arrastrada is not None and
                    self.zona.rect.collidepoint(evento.pos)
                )

            # ── Mouse Up: soltar tarjeta ──────────────
            if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                if self.arrastrada:
                    self.arrastrada.soltar([self.zona])
                    self.arrastrada = None
                    self.zona.activa = False

            # ── Botones ───────────────────────────────
            if self.btn_analizar.manejar_evento(evento):
                self._ejecutar_ia()

            if self.btn_limpiar.manejar_evento(evento):
                self._limpiar_zona()

            if self.btn_enviar.manejar_evento(evento):
                if len(self.zona.tarjetas) == TAMANO_EQUIPO:
                    self.mostrar_resultado = True

    def _ejecutar_ia(self):
        """
        Llama al algoritmo de Solange.
        Respeta el enunciado: distribuir N personas en k equipos
        minimizando la desviación total de habilidades en cada equipo.
        La desviación total óptima se usa como referencia para el puntaje.
        """
        if not ALGORITMO_DISPONIBLE:
            print("⚠️  algoritmo.py no disponible")
            return

        # Todas las personas disponibles
        personas = [{"nombre": t.nombre, "habilidad": t.habilidad}
                    for t in self.tarjetas]

        # k = definido por Jordy en CONFIGURACIÓN DEL NIVEL
        cantidad_equipos = CANTIDAD_EQUIPOS

        try:
            resultado = resolver_distribucion(
                personas,
                cantidad_equipos=cantidad_equipos,
                guardar_historial=False
            )

            # Desviación total óptima encontrada por el algoritmo
            self.desv_optima  = resultado["mejor_desviacion"]
            self.resultado_ia = resultado

            # Mostrar en consola los equipos óptimos formados
            print(f"✅ Distribución óptima encontrada:")
            for i, equipo in enumerate(resultado["mejores_equipos"]):
                nombres = [p["nombre"] for p in equipo]
                habs    = [p["habilidad"] for p in equipo]
                desv    = max(habs) - min(habs) if len(habs) > 1 else 0
                print(f"   Equipo {i+1}: {nombres} — desviación: {desv}")
            print(f"   Desviación total óptima: {self.desv_optima}")
            print(f"   Estadísticas: {resultado['estadisticas']}")

        except Exception as e:
            print(f"❌ Error en algoritmo: {e}")

    def _limpiar_zona(self):
        """Devuelve todas las tarjetas al banco."""
        for t in list(self.zona.tarjetas):
            self.zona.quitar_tarjeta(t)
            t.en_zona = None
            t._iniciar_retorno()

    def actualizar(self):
        for t in self.tarjetas:
            t.actualizar()
        self.meter.actualizar_desde_zona(self.zona, self.desv_optima)
        self.meter.actualizar()

    def dibujar(self):
        self.pantalla.fill(COLOR_FONDO)

        # ── Título ────────────────────────────────
        _dibujar_texto(self.pantalla, "⛰  OPERACIÓN RESCATE: CUMBRES SALVAJES",
                       ANCHO // 2, 28, 18, COLOR_ACENTO, negrita=True)

        # ── Etiquetas de paneles ──────────────────
        _dibujar_texto(self.pantalla, "RESCATISTAS DISPONIBLES",
                       145, 60, 13, COLOR_SUBTEXTO, negrita=True)

        # ── Zona de expedición ───────────────────
        self.zona.dibujar(self.pantalla)

        # ── Tarjetas en zona ─────────────────────
        for t in self.zona.tarjetas:
            if not t.arrastrando:
                t.dibujar(self.pantalla)

        # ── Tarjetas del banco ───────────────────
        for t in self.tarjetas:
            if t.en_zona is None and not t.arrastrando:
                t.dibujar(self.pantalla)

        # ── Tarjeta arrastrada (siempre al frente) ─
        if self.arrastrada:
            self.arrastrada.dibujar(self.pantalla)

        # ── Panel derecho ─────────────────────────
        self.meter.dibujar(self.pantalla)
        self.btn_analizar.dibujar(self.pantalla)
        self.btn_limpiar.dibujar(self.pantalla)
        self.btn_enviar.dibujar(self.pantalla)

        # ── Instrucciones ─────────────────────────
        _dibujar_texto(self.pantalla,
                       "Arrastra 4 rescatistas a la zona · R = reiniciar · ESC = salir",
                       ANCHO // 2, ALTO - 22, 12, COLOR_SUBTEXTO)

        # ── Resultado final ───────────────────────
        if self.mostrar_resultado:
            desv_usuario = self.zona.desviacion()
            dibujar_resultado(self.pantalla,
                              calcular_estrellas(desv_usuario, self.desv_optima),
                              desv_usuario, self.desv_optima)

        pygame.display.flip()

    def ejecutar(self):
        while True:
            self.manejar_eventos()
            self.actualizar()
            self.dibujar()
            self.reloj.tick(60)


# ─────────────────────────────────────────────
#  FUNCIONES AUXILIARES
# ─────────────────────────────────────────────
_fuente_cache: dict = {}

def _fuente(tamanio: int, negrita: bool = False) -> pygame.font.Font:
    clave = (tamanio, negrita)
    if clave not in _fuente_cache:
        _fuente_cache[clave] = pygame.font.SysFont("segoeui", tamanio, bold=negrita)
    return _fuente_cache[clave]


def _dibujar_texto(surface, texto, x, y, tamanio, color,
                   negrita=False, alineacion="center"):
    fuente  = _fuente(tamanio, negrita)
    render  = fuente.render(str(texto), True, color)
    rect    = render.get_rect()
    if alineacion == "center":
        rect.center = (x, y)
    elif alineacion == "left":
        rect.midleft = (x, y)
    surface.blit(render, rect)


def _color_por_nivel(nivel: int) -> tuple:
    if nivel >= 70:
        return COLOR_VERDE
    elif nivel >= 40:
        return COLOR_AMARILLO
    return COLOR_ROJO


def _color_harmony(valor: float) -> tuple:
    """Interpola verde → amarillo → rojo según el valor (0.0 a 1.0)."""
    if valor < 0.5:
        t = valor * 2
        r = int(COLOR_VERDE[0] + (COLOR_AMARILLO[0] - COLOR_VERDE[0]) * t)
        g = int(COLOR_VERDE[1] + (COLOR_AMARILLO[1] - COLOR_VERDE[1]) * t)
        b = int(COLOR_VERDE[2] + (COLOR_AMARILLO[2] - COLOR_VERDE[2]) * t)
    else:
        t = (valor - 0.5) * 2
        r = int(COLOR_AMARILLO[0] + (COLOR_ROJO[0] - COLOR_AMARILLO[0]) * t)
        g = int(COLOR_AMARILLO[1] + (COLOR_ROJO[1] - COLOR_AMARILLO[1]) * t)
        b = int(COLOR_AMARILLO[2] + (COLOR_ROJO[2] - COLOR_AMARILLO[2]) * t)
    return (r, g, b)


def _ease_out(t: float) -> float:
    return 1 - (1 - t) ** 3


def _dibujar_arco(surface, centro, radio, ang_inicio, ang_fin, color, grosor):
    """Dibuja un arco usando segmentos de línea."""
    pasos = 60
    puntos = []
    for i in range(pasos + 1):
        t   = i / pasos
        ang = math.radians(-(ang_inicio + (ang_fin - ang_inicio) * t))
        px  = centro[0] + int(math.cos(ang) * radio)
        py  = centro[1] + int(math.sin(ang) * radio)
        puntos.append((px, py))
    if len(puntos) > 1:
        pygame.draw.lines(surface, color, False, puntos, grosor)


def _puntos_estrella(cx, cy, radio):
    """Calcula los 10 puntos de una estrella de 5 puntas."""
    puntos = []
    for i in range(10):
        ang = math.radians(-90 + i * 36)
        r   = radio if i % 2 == 0 else radio * 0.45
        puntos.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return puntos


# ─────────────────────────────────────────────
#  PUNTO DE ENTRADA
# ─────────────────────────────────────────────
if __name__ == "__main__":
    juego = JuegoOperacionRescate()
    juego.ejecutar()