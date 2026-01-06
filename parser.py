import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass
class ParseOutcome:
    parse_ok: bool
    format_ok: bool
    error: str
    data: Optional[Dict[str, Any]]


class ResponseParser:
    def strip_code_fences(self, s: str) -> str:
        s = (s or "").strip()
        if s.startswith("```"):
            first_nl = s.find("\n")
            if first_nl != -1:
                s = s[first_nl + 1 :]
            if s.endswith("```"):
                s = s[:-3]
        return s.strip()

    def extract_json_object(self, s: str) -> str:
        s = (s or "").strip()
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            return s[start : end + 1]
        return s

    def maybe_wrap_json(self, s: str) -> str:
        t = (s or "").strip()
        if not t.startswith("{") and ('"eventos"' in t or '"Narracion"' in t or '"Personajes"' in t):
            return "{\n" + t.strip().strip(",") + "\n}"
        return t

    def parse(self, raw: str) -> ParseOutcome:
        cleaned = self.strip_code_fences(raw)
        cleaned = self.extract_json_object(cleaned)
        cleaned = self.maybe_wrap_json(cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            return ParseOutcome(parse_ok=False, format_ok=False, error=f"JSONDecodeError: {e}", data=None)

        if not isinstance(data, dict):
            return ParseOutcome(parse_ok=True, format_ok=False, error="root no es un objeto JSON", data=None)

        if "eventos" in data and "opciones" in data:
            ok, err = self.validate_new_format(data)
            return ParseOutcome(parse_ok=True, format_ok=ok, error=err, data=data)

        return ParseOutcome(parse_ok=True, format_ok=False, error="JSON parseado pero no tiene 'eventos'/'opciones'", data=data)

    def validate_new_format(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        eventos = data.get("eventos")
        opciones = data.get("opciones")

        if not isinstance(eventos, list):
            return False, "falta 'eventos' o no es lista"

        for i, ev in enumerate(eventos):
            if not isinstance(ev, dict):
                return False, f"eventos[{i}] no es objeto"

            tipo = ev.get("tipo")
            texto = ev.get("texto")

            if tipo not in ("narracion", "dialogo"):
                return False, f"eventos[{i}].tipo invalido: {tipo}"
            if not isinstance(texto, str):
                return False, f"eventos[{i}].texto no es string"

            if tipo == "dialogo":
                nombre = ev.get("nombre")
                if not isinstance(nombre, str) or not nombre.strip():
                    return False, f"eventos[{i}].nombre invalido o vacio"

        if not isinstance(opciones, list):
            return False, "falta 'opciones' o no es lista"
        clean = [c for c in opciones if isinstance(c, str) and c.strip()]
        if len(clean) < 2 or len(clean) > 4:
            return False, f"'opciones' debe tener 2-4 strings (tiene {len(clean)})"

        return True, ""
