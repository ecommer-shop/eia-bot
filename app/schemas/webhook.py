"""
Esquemas Pydantic para validar el payload que envía el Agent Bot de Chatwoot.

Esto reemplaza el filtrado frágil que teníamos en N8N: en lugar de adivinar
rutas como $json.body.messages[0].message_type, Pydantic valida la estructura
de forma explícita y nos da un objeto tipado. Si un campo no existe, lo
manejamos con valores por defecto en vez de que reviente el flujo.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class Sender(BaseModel):
    """Quién envió el mensaje. type puede ser 'contact', 'user' o 'agent_bot'."""
    id: Optional[int] = None
    name: Optional[str] = None
    type: Optional[str] = None
    phone_number: Optional[str] = None


class Conversation(BaseModel):
    id: int
    # Estado de la conversación en Chatwoot: 'open', 'pending', 'resolved'
    status: Optional[str] = None


class Account(BaseModel):
    id: int
    name: Optional[str] = None


class ChatwootWebhook(BaseModel):
    """
    Payload que Chatwoot envía a la Outgoing URL del Agent Bot.

    Campos clave para nosotros:
    - event: tipo de evento ('message_created', etc.)
    - message_type: 'incoming' (cliente) o 'outgoing' (bot/agente)
    - content: el texto del mensaje
    - sender.type: 'contact' = cliente real; 'agent_bot'/'user' = no responder
    """
    event: Optional[str] = None
    message_type: Optional[str] = None
    content: Optional[str] = None
    conversation: Optional[Conversation] = None
    account: Optional[Account] = None
    sender: Optional[Sender] = Field(default=None)

    # Chatwoot a veces anida sender dentro de 'meta'; lo capturamos también
    class Config:
        extra = "allow"

    def is_from_customer(self) -> bool:
        """
        True solo si es un mensaje entrante escrito por un cliente real.
        Esta única función reemplaza todo el lío de IF + Switch de N8N.
        """
        if self.event != "message_created":
            return False
        if self.message_type != "incoming":
            return False
        if not self.content or not self.content.strip():
            return False
        # Si el sender es un bot o agente, nunca respondemos (evita bucle)
        if self.sender and self.sender.type in ("agent_bot", "user"):
            return False
        return True

    def conversation_id(self) -> Optional[int]:
        return self.conversation.id if self.conversation else None

    def account_id(self) -> int:
        return self.account.id if self.account else 1

    def customer_phone(self) -> Optional[str]:
        return self.sender.phone_number if self.sender else None
