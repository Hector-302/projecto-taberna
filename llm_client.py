import os
from typing import Any, Dict, Optional

import requests


class LLMClient:
    def __init__(self):
        self.completion_url = os.getenv("LLAMA_COMPLETION_URL", "http://localhost:10000/completion")
        self.system_prompt = self._build_system_prompt()
        self.grammar = self._build_grammar()

    def _build_system_prompt(self) -> str:
        return (
            "Salida JSON estricto\n"
            "Responder solo con un unico JSON valido sin texto extra sin bloques de codigo\n"
            "Estructura\n"
            '{ "eventos": [ { "tipo": "narracion", "texto": string }, { "tipo": "dialogo", "nombre": string, "texto": string } ], "opciones": [ string, string ] }\n'
            "Eventos en orden cronologico alterna lo necesario\n"
            "Tipos narracion o dialogo\n"
            "Narracion solo texto dialogo nombre y texto\n"
            "Opciones 2 a 4 strings coherentes\n"
            "Sin comillas dobles dentro de textos usar comillas simples o reescribir si imprescindible escapar \\\"\n"
            "Sin comas colgantes nada fuera del JSON\n"
        )

    def _build_grammar(self) -> str:
        return r"""
root ::= object
object ::= "{" wsp "\"eventos\"" wsp ":" wsp event_array wsp "," wsp "\"opciones\"" wsp ":" wsp opciones wsp "}"
event_array ::= "[" wsp evento (wsp "," wsp evento)* wsp "]"
evento ::= narracion / dialogo
narracion ::= "{" wsp "\"tipo\"" wsp ":" wsp "\"narracion\"" wsp "," wsp "\"texto\"" wsp ":" wsp string wsp "}"
dialogo ::= "{" wsp "\"tipo\"" wsp ":" wsp "\"dialogo\"" wsp "," wsp "\"nombre\"" wsp ":" wsp string wsp "," wsp "\"texto\"" wsp ":" wsp string wsp "}"
opciones ::= "[" wsp opcion_items wsp "]"
opcion_items ::= string wsp "," wsp string (wsp "," wsp string (wsp "," wsp string)?)?
string ::= "\"" (escape / safe_char)* "\""
escape ::= "\\" ["\\/bfnrt\""]
safe_char ::= ~["\\]
wsp ::= [ \t\n\r]*
"""

    def _extract_content(self, data: Dict[str, Any]) -> Optional[str]:
        if isinstance(data.get("content"), str):
            return data["content"]

        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            top = choices[0]
            if isinstance(top, dict):
                text = top.get("text") or top.get("content")
                if isinstance(text, str):
                    return text
        return None

    def complete_with_grammar(self, prompt: str, temperature: float = 0.7, max_tokens: int = 260) -> str:
        payload = {
            "prompt": f"{self.system_prompt}\n\n{prompt.strip()}",
            "grammar": self.grammar,
            "stream": False,
            "temperature": float(temperature),
            "n_predict": int(max_tokens),
        }

        resp = requests.post(self.completion_url, json=payload, timeout=120)
        resp.raise_for_status()

        data = resp.json()
        content = self._extract_content(data)

        if not isinstance(content, str):
            raise ValueError("La respuesta del servidor de Llama no contiene texto utilizable.")

        return content.strip()
