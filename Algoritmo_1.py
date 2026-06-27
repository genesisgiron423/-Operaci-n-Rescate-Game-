from dataclasses import dataclass, field
from typing import Callable, Optional, List, Dict, Any


@dataclass(frozen=True)
class Persona:
    id: int
    nombre: str
    habilidad: int


@dataclass
class Equipo:
    miembros: List[Persona] = field(default_factory=list)
    minimo: Optional[int] = None
    maximo: Optional[int] = None

    def esta_vacio(self) -> bool:
        return len(self.miembros) == 0

    def desviacion(self) -> int:
        if len(self.miembros) <= 1:
            return 0
        return self.maximo - self.minimo

    def firma_para_simetria(self) -> tuple:
        habilidades = sorted(persona.habilidad for persona in self.miembros)
        return tuple(habilidades)

    def agregar(self, persona: Persona) -> tuple:
        estado_anterior = (self.minimo, self.maximo)
        self.miembros.append(persona)

        if self.minimo is None:
            self.minimo = persona.habilidad
            self.maximo = persona.habilidad
        else:
            self.minimo = min(self.minimo, persona.habilidad)
            self.maximo = max(self.maximo, persona.habilidad)

        return estado_anterior

    def quitar_ultimo(self, estado_anterior: tuple) -> None:
        self.miembros.pop()
        self.minimo, self.maximo = estado_anterior


def validar_personas(
    personas: List[Dict[str, Any]],
    cantidad_equipos: int
) -> List[Persona]:
    if cantidad_equipos <= 0:
        raise ValueError("La cantidad de equipos debe ser mayor que cero.")

    if len(personas) < cantidad_equipos:
        raise ValueError("No se pueden formar mas equipos que personas.")

    personas_validadas = []
    for indice, persona in enumerate(personas):
        if "nombre" not in persona or "habilidad" not in persona:
            raise ValueError("Cada persona debe tener 'nombre' y 'habilidad'.")

        if not isinstance(persona["habilidad"], int):
            raise ValueError("La habilidad debe ser un numero entero.")

        personas_validadas.append(
            Persona(
                id=indice,
                nombre=str(persona["nombre"]),
                habilidad=persona["habilidad"],
            )
        )

    return personas_validadas


def snapshot_equipos(equipos: List[Equipo]) -> List[List[Dict[str, Any]]]:
    return [
        [
            {
                "id": persona.id,
                "nombre": persona.nombre,
                "habilidad": persona.habilidad,
            }
            for persona in equipo.miembros
        ]
        for equipo in equipos
    ]


def calcular_desviacion_total(equipos: List[Equipo]) -> int:
    return sum(equipo.desviacion() for equipo in equipos)


def calcular_aumento_desviacion(
    equipo: Equipo,
    persona: Persona
) -> int:
    desviacion_antes = equipo.desviacion()

    if equipo.esta_vacio():
        desviacion_despues = 0
    else:
        nuevo_minimo = min(equipo.minimo, persona.habilidad)
        nuevo_maximo = max(equipo.maximo, persona.habilidad)
        desviacion_despues = nuevo_maximo - nuevo_minimo

    return desviacion_despues - desviacion_antes


def debe_podar_por_simetria(
    equipo: Equipo,
    firmas_vistas: set
) -> bool:
    firma = equipo.firma_para_simetria()

    if firma in firmas_vistas:
        return True

    firmas_vistas.add(firma)
    return False


def debe_podar_por_cota_superior(
    desviacion_actual: int,
    mejor_desviacion: int
) -> bool:
    return desviacion_actual >= mejor_desviacion


def debe_podar_por_equipos_imposibles(
    equipos: List[Equipo],
    personas_restantes: int
) -> bool:
    equipos_vacios = sum(1 for equipo in equipos if equipo.esta_vacio())
    return equipos_vacios > personas_restantes


def clave_estado(
    indice_persona: int,
    equipos: List[Equipo],
    desviacion_actual: int,
) -> tuple:
    firmas = sorted(equipo.firma_para_simetria() for equipo in equipos)

    return (
        indice_persona,
        tuple(firmas),
        desviacion_actual,
    )


def construir_solucion_greedy(
    personas: List[Persona],
    cantidad_equipos: int
) -> tuple[int, List[List[Dict[str, Any]]]]:

    equipos = [Equipo() for _ in range(cantidad_equipos)]
    desviacion_total = 0

    for indice, persona in enumerate(personas):
        personas_restantes = len(personas) - indice
        equipos_vacios = [equipo for equipo in equipos if equipo.esta_vacio()]

        if len(equipos_vacios) == personas_restantes:
            candidatos = equipos_vacios
        else:
            candidatos = equipos

        equipo_elegido = min(
            candidatos,
            key=lambda equipo: (
                calcular_aumento_desviacion(equipo, persona),
                len(equipo.miembros),
            ),
        )

        aumento = calcular_aumento_desviacion(equipo_elegido, persona)
        equipo_elegido.agregar(persona)
        desviacion_total += aumento

    return desviacion_total, snapshot_equipos(equipos)


def resolver_distribucion(
    personas: List[Dict[str, Any]],
    cantidad_equipos: int,
    guardar_historial: bool = True,
    max_eventos: Optional[int] = 5000,
    usar_ordenamiento: bool = True,
    usar_cache: bool = True,
    callback_evento: Optional[Callable] = None,
    modo_debug: bool = False,
) -> Dict[str, Any]:

    personas_validadas = validar_personas(personas, cantidad_equipos)

    if usar_ordenamiento:
        personas_validadas = sorted(
            personas_validadas,
            key=lambda persona: persona.habilidad,
            reverse=True,
        )

    equipos = [Equipo() for _ in range(cantidad_equipos)]
    mejor_desviacion_inicial, mejor_equipos_inicial = construir_solucion_greedy(
        personas_validadas,
        cantidad_equipos,
    )

    mejor_solucion = {
        "desviacion": mejor_desviacion_inicial,
        "equipos": mejor_equipos_inicial,
    }

    estadisticas = {
        "nodos_visitados": 0,
        "soluciones_completas": 0,
        "podas_simetria": 0,
        "podas_cota_superior": 0,
        "podas_equipos_imposibles": 0,
        "podas_cache": 0,
    }

    historial_nodos = []
    historial_podas = []
    estados_por_paso = []
    cache_estados = set()
    contador_pasos = {"valor": 0}

    def obtener_snapshot_si_necesario():
        if guardar_historial or callback_evento is not None:
            return snapshot_equipos(equipos)
        return None

    def registrar_evento(tipo: str, **datos) -> None:
        if not modo_debug and tipo not in (
            "mejor_solucion",
            "solucion_inicial",
        ):
            return
        contador_pasos["valor"] += 1
        evento = {
            "paso": contador_pasos["valor"],
            "tipo": tipo,
            **datos,
        }

        if guardar_historial and (
            max_eventos is None or len(estados_por_paso) < max_eventos
        ):
            estados_por_paso.append(evento)

            if tipo == "nodo":
                historial_nodos.append(evento)
            elif tipo == "poda":
                historial_podas.append(evento)

        if callback_evento is not None:
            callback_evento(evento)

    registrar_evento(
        "solucion_inicial",
        desviacion=mejor_solucion["desviacion"],
        equipos=mejor_solucion["equipos"],
    )

    def backtracking(
        indice_persona: int,
        desviacion_actual: int
    ) -> None:
        estadisticas["nodos_visitados"] += 1

        persona_actual = None
        if indice_persona < len(personas_validadas):
            persona_actual = personas_validadas[indice_persona]

        registrar_evento(
            "nodo",
            nivel=indice_persona,
            persona_actual=persona_actual.nombre if persona_actual else None,
            desviacion_actual=desviacion_actual,
            mejor_desviacion=mejor_solucion["desviacion"],
            equipos=obtener_snapshot_si_necesario(),
        )

        personas_restantes = len(personas_validadas) - indice_persona

        if debe_podar_por_equipos_imposibles(equipos, personas_restantes):
            estadisticas["podas_equipos_imposibles"] += 1
            registrar_evento(
                "poda",
                poda="equipos_imposibles",
                nivel=indice_persona,
                motivo="Quedan mas equipos vacios que personas por asignar.",
                equipos=obtener_snapshot_si_necesario(),
            )
            return

        if usar_cache:
            clave = clave_estado(indice_persona, equipos, desviacion_actual)

            if clave in cache_estados:
                estadisticas["podas_cache"] += 1
                registrar_evento(
                    "poda",
                    poda="cache",
                    nivel=indice_persona,
                    motivo="Este estado equivalente ya fue explorado.",
                    equipos=obtener_snapshot_si_necesario(),
                )
                return

            cache_estados.add(clave)

        # CASO BASE
        if indice_persona == len(personas_validadas):

            if any(equipo.esta_vacio() for equipo in equipos):
                return

            estadisticas["soluciones_completas"] += 1

            if desviacion_actual < mejor_solucion["desviacion"]:
                mejor_solucion["desviacion"] = desviacion_actual
                snapshot_actual = snapshot_equipos(equipos)
                mejor_solucion["equipos"] = snapshot_actual

                registrar_evento(
                    "mejor_solucion",
                    desviacion=desviacion_actual,
                    equipos=snapshot_actual,
                )

            return

        firmas_vistas = set()

        for indice_equipo, equipo in enumerate(equipos):

            if debe_podar_por_simetria(equipo, firmas_vistas):
                estadisticas["podas_simetria"] += 1
                registrar_evento(
                    "poda",
                    poda="simetria",
                    nivel=indice_persona,
                    equipo=indice_equipo,
                    persona=persona_actual.nombre if persona_actual else None,
                    motivo="Otro equipo equivalente ya fue probado en este nivel.",
                    equipos=obtener_snapshot_si_necesario(),
                )
                continue

            aumento = calcular_aumento_desviacion(equipo, persona_actual)
            nueva_desviacion = desviacion_actual + aumento
            estado_anterior = equipo.agregar(persona_actual)

            registrar_evento(
                "decision",
                nivel=indice_persona,
                equipo=indice_equipo,
                persona=persona_actual.nombre if persona_actual else None,
                desviacion_actual=nueva_desviacion,
                equipos=obtener_snapshot_si_necesario(),
            )

            if debe_podar_por_cota_superior(
                nueva_desviacion,
                mejor_solucion["desviacion"],
            ):
                estadisticas["podas_cota_superior"] += 1
                registrar_evento(
                    "poda",
                    poda="cota_superior",
                    nivel=indice_persona,
                    equipo=indice_equipo,
                    persona=persona_actual.nombre if persona_actual else None,
                    desviacion_actual=nueva_desviacion,
                    mejor_desviacion=mejor_solucion["desviacion"],
                    motivo="La rama ya no puede mejorar la mejor solucion.",
                    equipos=obtener_snapshot_si_necesario(),
                )
                equipo.quitar_ultimo(estado_anterior)
                continue

            backtracking(indice_persona + 1, nueva_desviacion)

            equipo.quitar_ultimo(estado_anterior)

            registrar_evento(
                "vuelta_atras",
                nivel=indice_persona,
                equipo=indice_equipo,
                persona=persona_actual.nombre if persona_actual else None,
                equipos=obtener_snapshot_si_necesario(),
            )

    backtracking(indice_persona=0, desviacion_actual=0)

    return {
        "mejor_desviacion": mejor_solucion["desviacion"],
        "mejores_equipos": mejor_solucion["equipos"],
        "personas_ordenadas": [
            {
                "id": persona.id,
                "nombre": persona.nombre,
                "habilidad": persona.habilidad,
            }
            for persona in personas_validadas
        ],
        "estadisticas": estadisticas,
        "nodos_visitados": estadisticas["nodos_visitados"],
        "podas_simetria": estadisticas["podas_simetria"],
        "podas_cota_superior": estadisticas["podas_cota_superior"],
        "historial_nodos_explorados": historial_nodos,
        "historial_podas": historial_podas,
        "estados_por_paso": estados_por_paso,
    }


if __name__ == "__main__":
    personas_de_prueba = [
        {"nombre": "Ana", "habilidad": 8},
        {"nombre": "Luis", "habilidad": 5},
        {"nombre": "Marta", "habilidad": 9},
        {"nombre": "Carlos", "habilidad": 4},
        {"nombre": "Sofia", "habilidad": 7},
    ]

    resultado = resolver_distribucion(personas_de_prueba, cantidad_equipos=2)
    print(resultado["mejor_desviacion"])
    print(resultado["mejores_equipos"])
    print(resultado["estadisticas"])