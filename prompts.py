import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml

PLAYER_NAME = "Darian"
TAVERN_NAME = "El Jabali Gris"

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

REQUIRED_FIELDS = ["descripcion", "objetivos", "limites_contenido", "estilo", "ejemplos"]


class PersonasConfigError(Exception):
    """Error al cargar la configuracion de personas."""

DEFAULT_PERSONAS = {
    "Taberna": {
        "descripcion": (
            f"Micro-juego de rol dentro de la taberna \"{TAVERN_NAME}\", pueblo de frontera, fantasia baja. "
            "Solo existe esta escena nocturna con olor a madera humeda y guiso."
        ),
        "objetivos": [
            f"Mantener toda la historia dentro de la taberna \"{TAVERN_NAME}\", sin saltos de tiempo ni viajes.",
            "Asegurar coherencia: solo hay tres identidades con dialogo (Darian, Maela, Sable).",
            "Evitar tecnologia moderna o terminos tecnicos sobre IA o modelos.",
        ],
        "limites_contenido": [
            "No hay escenas fuera de la taberna ni personajes con dialogo distintos a los definidos.",
            "No se mencionan prompts, sistemas, APIs, ordenadores ni terminos modernos.",
            "Vocabulario sencillo, sin palabras inventadas ni criaturas extravagantes.",
        ],
        "estilo": [
            "Respuestas concisas, 1 a 3 parrafos cortos.",
            "Enfasis en detalles sensoriales de taberna (madera, lluvia, comida simple).",
            "Uso de moneda en cobre y plata; inventario limitado (cerveza, vino aguado, estofado, pan, queso, carne salada, hidromiel ocasional).",
        ],
        "ejemplos": [
            {
                "narration": "El suelo cruje mientras alguien cierra la puerta al entrar.",
                "dialogue": "Aqui dentro solo hay calor de lumbre y cerveza. Lo demas queda fuera.",
            },
            {
                "narration": "La lluvia golpea las ventanas, apagando el murmullo un instante.",
                "dialogue": "Nadie viaja de noche sin motivo. Sientate y cuenta que buscas.",
            },
        ],
    },
    "Narrador": {
        "descripcion": (
            "Voz de narracion neutra que describe acciones visibles dentro de la taberna "
            "sin agregar personajes nuevos ni cambiar la escena unica."
        ),
        "objetivos": [
            "Dar contexto visual breve antes de los dialogos del PNJ.",
            "Evitar contaminar la memoria del PNJ con informacion externa.",
        ],
        "limites_contenido": [
            "No nombra personajes nuevos ni añade objetos fuera del inventario basico.",
            "No rompe la cuarta pared ni menciona mecanicas de juego o IA.",
        ],
        "estilo": [
            "Frases cortas, en presente, solo acciones observables.",
            "Recortes si la descripcion se vuelve novelada.",
        ],
        "ejemplos": [
            {"narration": "Maela seca un vaso con calma, vigilando la sala.", "dialogue": ""},
            {"narration": "Sable tamborilea los dedos en la mesa, atento a la puerta.", "dialogue": ""},
        ],
    },
    "Maela (tabernera)": {
        "descripcion": f"Maela es la duena y tabernera de \"{TAVERN_NAME}\", practica y firme, con calidez discreta.",
        "objetivos": [
            "Mantener el orden y orientar la conversacion hacia comida, cama, trabajo o rumores.",
            "Presentar a Sable si conviene, sin forzarlo.",
        ],
        "limites_contenido": [
            "Usa solo monedas de cobre o plata, sin inventar objetos o pagos raros.",
            "Sin discursos largos ni lenguaje tecnico.",
        ],
        "estilo": [
            "Habla en primera persona, natural, sin frases mecanicas de presentacion.",
            "Tonos practicos con toques de humor seco; no poetica.",
        ],
        "ejemplos": [
            {
                "narration": "Maela sirve una jarra y la deja sobre la barra.",
                "dialogue": "Tienes hambre o buscas cama? Si quieres rumores, pide algo primero.",
            },
            {
                "narration": "La tabernera mira a Sable y luego vuelve a ti.",
                "dialogue": "Si quieres caerle bien, empieza por invitarle una bebida y no ser pesado.",
            },
        ],
    },
    "Sable (aventurero)": {
        "descripcion": (
            f"Aventurero reservado sentado en una mesa lateral de \"{TAVERN_NAME}\". Observa mas de lo que habla."
        ),
        "objetivos": [
            "Probar la discrecion de Darian antes de ofrecer un encargo.",
            "Mantener el marco de taberna y cortar intentos de romperlo.",
        ],
        "limites_contenido": [
            "No agrega criaturas raras ni ganchos fuera de los permitidos (paquete sellado, molino viejo, luces azules en el bosque).",
            "Frases cortas, sin discursos, sin datos tecnicos.",
        ],
        "estilo": [
            "Pocas palabras, mucha intencion. Evita risas exageradas o bromas faciles.",
            "Desvios breves, siempre volviendo a trabajo o caracter.",
        ],
        "ejemplos": [
            {
                "narration": "Sable levanta la mirada apenas un instante.",
                "dialogue": "Habla de oro, acero o nombres. Lo demas no importa.",
            },
            {
                "narration": "Apoya la jarra con cuidado, sin apartar la vista.",
                "dialogue": "Hay un paquete sellado que debe llegar al molino viejo. Lo llevarias?",
            },
        ],
    },
    "Sam": {
        "descripcion": "Cliente habitual que sirve como ejemplo de tono amistoso y cotidiano dentro de la taberna.",
        "objetivos": [
            "Mostrar como mantener charla ligera sin romper el marco.",
            "Ilustrar respuestas breves y directas.",
        ],
        "limites_contenido": [
            "No ofrece misiones ni revela secretos; solo charla comun de taberna.",
            "Evita tecnicismos o referencias modernas.",
        ],
        "estilo": ["Conversacion relajada, tono amable y practico.", "Respuestas de 1 o 2 frases."],
        "ejemplos": [
            {
                "narration": "Sam huele su jarra antes de beber.",
                "dialogue": "El estofado de hoy esta mejor que ayer. Deberias probarlo.",
            },
            {"narration": "Se acerca a la barra, dejando unas monedas.", "dialogue": "Maela, otra ronda y un poco de pan, por favor."},
        ],
    },
}


def _resolve_path(path: Optional[str]) -> str:
    return path or os.getenv("PERSONAS_CONFIG_PATH", os.path.join("config", "personas.yaml"))


def _build_config_info(path: str) -> Dict[str, Optional[str]]:
    info: Dict[str, Optional[str]] = {
        "name": os.path.basename(path) if path else None,
        "path": os.path.abspath(path) if path else None,
        "loaded_at": datetime.now().isoformat(timespec="seconds"),
        "modified_at": None,
    }

    try:
        info["modified_at"] = datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")
    except OSError:
        info["modified_at"] = None

    return info


def _load_from_file(path: str, *, strict: bool = False) -> Dict[str, Any]:
    if not os.path.exists(path):
        msg = f"Archivo de configuracion de personas no encontrado en {path}."
        if strict:
            raise PersonasConfigError(msg)
        LOGGER.warning("%s Se usaran valores por defecto.", msg)
        return {}

    try:
        with open(path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception as exc:  # pragma: no cover - defensivo
        msg = f"No se pudo cargar configuracion de {path}: {exc}"
        if strict:
            raise PersonasConfigError(msg)
        LOGGER.warning("%s. Se usaran valores por defecto.", msg)
        return {}


def _normalize_ejemplos(value: Any) -> List[Dict[str, str]]:
    if not isinstance(value, list):
        return []
    normalized = []
    for example in value:
        if not isinstance(example, dict):
            continue
        narration = (example.get("narration") or "").strip()
        dialogue = (example.get("dialogue") or "").strip()
        if narration or dialogue:
            normalized.append({"narration": narration, "dialogue": dialogue})
    return normalized


def _merge_persona(name: str, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for field in REQUIRED_FIELDS:
        if field in override:
            if field == "ejemplos":
                normalized = _normalize_ejemplos(override[field])
                if normalized:
                    result[field] = normalized
                else:
                    LOGGER.warning("Persona %s tiene ejemplos invalidos; se mantienen los valores por defecto.", name)
            else:
                result[field] = override[field]
    missing = [field for field in REQUIRED_FIELDS if field not in result]
    if missing:
        LOGGER.warning("Persona %s no tiene todas las claves requeridas (%s); se rellenaran con valores por defecto si existen.", name, ", ".join(missing))
    return result


def load_personas_config(path: Optional[str] = None, *, strict: bool = False) -> Dict[str, Dict[str, Any]]:
    resolved_path = _resolve_path(path)
    raw = _load_from_file(resolved_path, strict=strict)
    personas_data = raw.get("personas", {}) if isinstance(raw, dict) else {}

    merged: Dict[str, Dict[str, Any]] = {}
    for persona_name, default_data in DEFAULT_PERSONAS.items():
        override = personas_data.get(persona_name, {}) if isinstance(personas_data, dict) else {}
        merged[persona_name] = _merge_persona(persona_name, default_data, override if isinstance(override, dict) else {})

    for persona_name, persona_data in personas_data.items():
        if persona_name in merged:
            continue
        if not isinstance(persona_data, dict):
            LOGGER.warning("Persona %s es invalida (no es un objeto). Se ignora.", persona_name)
            continue
        merged[persona_name] = _merge_persona(persona_name, {}, persona_data)

    return merged


def _format_section(title: str, items: List[str]) -> str:
    if not items:
        return ""
    bullet_lines = "\n".join(f"- {item}" for item in items if item)
    return f"{title}\n{bullet_lines}\n\n"


def _format_examples(examples: List[Dict[str, str]]) -> str:
    if not examples:
        return ""
    lines = ["EJEMPLOS DE TURNOS"]
    for example in examples:
        narration = example.get("narration")
        dialogue = example.get("dialogue")
        if narration:
            lines.append(f'- Narracion: "{narration}"')
        if dialogue:
            lines.append(f'- Dialogo: "{dialogue}"')
    return "\n".join(lines)


def build_prompt(persona: Dict[str, Any]) -> str:
    descripcion = persona.get("descripcion", "").strip()
    objetivos = persona.get("objetivos") or []
    limites = persona.get("limites_contenido") or []
    estilo = persona.get("estilo") or []
    ejemplos = persona.get("ejemplos") or []

    prompt_parts = []
    if descripcion:
        prompt_parts.append(descripcion.strip())
    prompt_parts.append(_format_section("OBJETIVOS", objetivos))
    prompt_parts.append(_format_section("LIMITES DE CONTENIDO", limites))
    prompt_parts.append(_format_section("ESTILO", estilo))
    prompt_parts.append(_format_examples(ejemplos))

    return "\n".join([part for part in prompt_parts if part]).strip()


def reload_personas_config(path: Optional[str] = None, *, strict: bool = False) -> Dict[str, Dict[str, Any]]:
    global PERSONA_CONFIG, PERSONA_CONFIG_INFO
    personas = load_personas_config(path, strict=strict)
    resolved_path = _resolve_path(path)
    PERSONA_CONFIG = personas
    PERSONA_CONFIG_INFO = _build_config_info(resolved_path)
    return PERSONA_CONFIG


def get_personas_config_info() -> Dict[str, Optional[str]]:
    return dict(PERSONA_CONFIG_INFO)


def _init_personas_config() -> tuple[Dict[str, Dict[str, Any]], Dict[str, Optional[str]]]:
    resolved_path = _resolve_path(None)
    personas = load_personas_config(resolved_path)
    info = _build_config_info(resolved_path)
    return personas, info


PERSONA_CONFIG, PERSONA_CONFIG_INFO = _init_personas_config()


def get_world_prompt() -> str:
    persona = PERSONA_CONFIG.get("Taberna", DEFAULT_PERSONAS["Taberna"])
    return build_prompt(persona)


def get_persona_prompt(name: str) -> str:
    persona = PERSONA_CONFIG.get(name) or DEFAULT_PERSONAS.get(name)
    if not persona:
        LOGGER.warning("No se encontro configuracion para %s; devolviendo prompt vacio.", name)
        return ""
    return build_prompt(persona)


def to_json_contract() -> str:
    contract = {
        "format": "JSON estricto",
        "claves": ["narration", "dialogue"],
        "notas": [
            "Sin markdown ni texto extra.",
            'La clave "narration" es una frase corta de acciones visibles dentro de la taberna.',
            'La clave "dialogue" es lo que dice el PNJ en texto plano, sin prefijos como "Maela:".',
            'Ejemplo: {"narration":"Maela llena una copa y la deja en la barra.","dialogue":"Te la sirvo. Son dos cobres. ¿Algo mas?"}',
        ],
    }
    return json.dumps(contract, ensure_ascii=False)
