"""Datos sintéticos y autorización por objeto. Ninguna conexión con un banco real."""

import json
from typing import Annotated, Literal
from uuid import UUID

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, Field

from bank_mcp.config import USER_A, USER_B, Settings

RequestId = Annotated[str, Field(strict=True, pattern=r"^SOL-[0-9]{4}$")]
Limit = Annotated[int, Field(strict=True, ge=1, le=10)]


class GetInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    solicitud_id: RequestId


class ListInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    limite: Limit = 5


class Solicitud(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    solicitud_id: RequestId
    producto: Literal["credito_personal", "tarjeta"]
    estado: Literal["en_revision", "aprobada", "observada"]
    actualizado: str
    datos_ficticios: Literal[True] = True


class ListaSolicitudes(BaseModel):
    model_config = ConfigDict(extra="forbid")
    solicitudes: list[Solicitud] = Field(max_length=10)
    hay_mas: bool


class SyntheticRepository:
    def __init__(self, settings: Settings):
        self.rows = {
            "SOL-1001": Solicitud(
                solicitud_id="SOL-1001",
                producto="credito_personal",
                estado="en_revision",
                actualizado="2026-10-28",
            ),
            "SOL-1002": Solicitud(
                solicitud_id="SOL-1002",
                producto="tarjeta",
                estado="aprobada",
                actualizado="2026-10-28",
            ),
            "SOL-2001": Solicitud(
                solicitud_id="SOL-2001",
                producto="credito_personal",
                estado="observada",
                actualizado="2026-10-28",
            ),
        }
        if settings.grants_file:
            document = json.loads(settings.grants_file.read_text(encoding="utf-8"))
            grants = document["users"]
            self.grants = {}
            for user, request_ids in grants.items():
                UUID(user)
                if not isinstance(request_ids, list) or not all(
                    item in self.rows for item in request_ids
                ):
                    raise ValueError("GRANTS_FILE contiene solicitudes inválidas.")
                self.grants[f"{settings.tenant_id}:{user}"] = frozenset(request_ids)
        else:
            self.grants = {
                f"{settings.tenant_id}:{USER_A}": frozenset(["SOL-1001", "SOL-1002"]),
                f"{settings.tenant_id}:{USER_B}": frozenset(["SOL-2001"]),
            }

    async def get(self, principal: str, solicitud_id: str) -> Solicitud:
        # La misma respuesta evita distinguir objetos ajenos de objetos inexistentes.
        if solicitud_id not in self.grants.get(principal, ()) or solicitud_id not in self.rows:
            raise ToolError("RECURSO_NO_DISPONIBLE")
        return self.rows[solicitud_id]

    async def list_for(self, principal: str, limite: int) -> ListaSolicitudes:
        ids = sorted(self.grants.get(principal, ()))
        return ListaSolicitudes(
            solicitudes=[self.rows[key] for key in ids[:limite]],
            hay_mas=len(ids) > limite,
        )
