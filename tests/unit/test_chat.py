from __future__ import annotations

from pathwise.core.chat import ChatService, ChatTurn
from pathwise.core.store import FileStore


def test_history_round_trip(store: FileStore) -> None:
    """Persistence layer: append jsonl, read back as ChatTurns."""
    user_id = "abcdef0123456789abcdef0123456789"
    season_id = "build-independence"
    version = 1

    chat = ChatService(store)
    assert chat.history(user_id, season_id, version) == []

    path = store.chat_history_path(user_id, season_id, version)
    store.append_jsonl(path, {"role": "user", "text": "hi", "at": 1.0})
    store.append_jsonl(path, {"role": "assistant", "text": "hello", "at": 2.0})

    turns = chat.history(user_id, season_id, version)
    assert turns == [
        ChatTurn(role="user", text="hi", at=1.0),
        ChatTurn(role="assistant", text="hello", at=2.0),
    ]


def test_history_filters_malformed(store: FileStore) -> None:
    """Records missing role/text are skipped silently."""
    user_id = "abcdef0123456789abcdef0123456789"
    path = store.chat_history_path(user_id, "build-independence", 1)
    store.append_jsonl(path, {"role": "user", "text": "good", "at": 1.0})
    store.append_jsonl(path, {"role": "system", "text": "wrong role", "at": 1.5})
    store.append_jsonl(path, {"role": "assistant", "text": "", "at": 2.0})

    turns = ChatService(store).history(user_id, "build-independence", 1)
    assert [t.text for t in turns] == ["good"]
