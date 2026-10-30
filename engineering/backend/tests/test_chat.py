import copy
import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from onlinecoc import chat
from onlinecoc.assets import Assets, restore_host
from onlinecoc.contracts import check
from onlinecoc.errors import DomainError
from onlinecoc.gateway import InProcessTransport
from onlinecoc.host import Host
from onlinecoc.model import validate
from onlinecoc.server import create_app
from test_host import host, message, invoke

ROOT = Path(__file__).resolve().parents[2]


def command(h, account, op, args):
    return h.command(account, message(h, account, op, args, uuid.uuid4().hex))


def send(h, account="player1", cid="general", text="你好", **extra):
    return command(h, account, "chat.message.send", {"channelId": cid, "text": text, **extra})


def group(h):
    return command(h, "kp", "chat.channel.create", {
        "kind": "group", "name": "调查小组", "participants": ["kp", "player1"]})["result"]["channelId"]


def update(h, cid, **fields):
    revision = h.project("kp")["chatChannels"][cid]["revision"]
    return command(h, "kp", "chat.channel.update", {"channelId": cid, "revision": revision, **fields})


def test_public_send_restart_idempotency_and_projection(host):
    m = message(host, "player1", "chat.message.send", {
        "channelId": "general", "text": "中文 / <script>alert(1)</script>", "speakerId": "actor-player1"}, "send")
    r = host.command("player1", m)
    assert r["status"] == "committed", r
    assert host.command("player1", m) == r
    page = host.chat_history("player2", "general")
    assert len(page["items"]) == 1
    msg = page["items"][0]
    assert msg["text"] == m["payload"]["args"]["text"]
    assert msg["senderAccountId"] == "player1" and msg["speakerId"] == "actor-player1"
    projection = host.project("player2")
    check("projection", projection)
    assert "<script>" not in json.dumps(projection)
    assert projection["chatChannels"]["general"]["unreadCount"] == 1
    assert host.project("player1")["chatChannels"]["general"]["unreadCount"] == 0
    host.close(); host.__init__(host.path)
    assert host.command("player1", m) == r
    assert host.chat_history("player2", "general") == page
    altered = copy.deepcopy(m); altered["payload"]["args"]["text"] = "different"
    with pytest.raises(DomainError, match="COMMAND_ID_CONFLICT"):
        host.command("player1", altered)


def test_private_channels_revoke_and_no_projection_side_channel(host):
    before = host.project("player2")
    cid = group(host)
    sent = send(host, cid=cid, text="秘密")
    mid = sent["result"]["messageId"]
    assert host.project("player2") == before
    for hidden in (cid, "not-a-channel"):
        with pytest.raises(DomainError, match="NOT_VISIBLE"):
            host.chat_history("player2", hidden)
    assert command(host, "player2", "chat.message.send", {"channelId": cid, "text": "猜 ID"})["code"] == "NOT_VISIBLE"
    assert send(host, replyTo=mid)["code"] == "NOT_VISIBLE"
    assert update(host, cid, participants=["kp"])["status"] == "committed"
    assert cid not in host.project("player1")["chatChannels"]
    assert "result" not in host.receipt("player1", sent["commandId"])
    with pytest.raises(DomainError, match="NOT_VISIBLE"):
        host.chat_history("player1", cid)


def test_direct_pair_dedup_and_kp_not_implicit_recipient(host):
    before = host.project("kp")
    a = command(host, "player1", "chat.direct.open", {"accountId": "player2"})
    b = command(host, "player2", "chat.direct.open", {"accountId": "player1"})
    assert a["result"] == b["result"]
    cid = a["result"]["channelId"]
    assert send(host, cid=cid)["status"] == "committed"
    assert host.project("kp") == before
    with pytest.raises(DomainError, match="NOT_VISIBLE"):
        host.chat_history("kp", cid)
    assert command(host, "player1", "chat.direct.open", {"accountId": "player1"})["code"] == "INPUT_INVALID"


def test_pagination_read_positions_and_old_message_edits(host):
    host.clock = lambda: 1000
    sent = [send(host, text=str(i))["result"] for i in range(7)]
    p = host.chat_history("player2", "general", limit=3)
    assert [m["sequence"] for m in p["items"]] == [5, 6, 7] and p["nextBefore"] == 5
    send(host, text="arrived after first page")
    q = host.chat_history("player2", "general", before=p["nextBefore"], limit=3)
    assert [m["sequence"] for m in q["items"]] == [2, 3, 4]
    assert host.chat_history("player2", "general", before=q["nextBefore"], limit=3)["items"][0]["sequence"] == 1
    for seq in (6, 3):
        assert command(host, "player2", "chat.read", {"channelId": "general", "sequence": seq})["result"]["readSequence"] == 6
    assert host.project("player2")["chatChannels"]["general"]["unreadCount"] == 2
    assert host.project("player1")["chatChannels"]["general"]["readSequence"] == 0
    assert command(host, "player2", "chat.read", {"channelId": "general", "sequence": 9})["status"] == "rejected"
    revision = host.project("player2")["chatChannels"]["general"]["revision"]
    assert command(host, "player1", "chat.message.edit", {"channelId": "general", "messageId": sent[0]["messageId"], "revision": 1, "text": "edited"})["status"] == "committed"
    assert host.project("player2")["chatChannels"]["general"]["revision"] > revision
    assert host.chat_history("player2", "general", before=2)["items"][0]["text"] == "edited"
    host.close(); host.__init__(host.path)
    assert host.project("player2")["chatChannels"]["general"]["readSequence"] == 6


def test_edit_retract_moderation_and_channel_policy(host):
    r = send(host)["result"]
    args = {"channelId": "general", "messageId": r["messageId"], "revision": 1}
    assert command(host, "player2", "chat.message.edit", {**args, "text": "forged"})["code"] == "PERMISSION_DENIED"
    assert command(host, "kp", "chat.message.edit", {**args, "text": "forged"})["code"] == "PERMISSION_DENIED"
    assert command(host, "player1", "chat.message.edit", {**args, "text": "new"})["status"] == "committed"
    assert command(host, "player1", "chat.message.retract", args)["code"] == "VERSION_CONFLICT"
    assert command(host, "kp", "chat.message.retract", {**args, "revision": 2})["status"] == "committed"
    tombstone = host.chat_history("player1", "general")["items"][0]
    assert tombstone["deleted"] and tombstone["text"] == "" and tombstone["sequence"] == 1
    assert update(host, "general", muted=["player1"])["status"] == "committed"
    assert send(host)["code"] == "CHANNEL_READ_ONLY"
    assert send(host, "player2")["status"] == "committed"
    assert update(host, "general", posting="kp")["status"] == "committed"
    assert send(host, "player2")["code"] == "CHANNEL_READ_ONLY"
    assert send(host, "kp")["status"] == "committed"
    update(host, "general", archived=True)
    assert send(host, "kp")["code"] == "CHANNEL_READ_ONLY"
    assert host.chat_history("player1", "general")["items"]


def test_paused_room_can_chat_archived_room_read_only(host):
    command(host, "kp", "room.status", {"status": "paused"})
    assert send(host)["status"] == "committed"
    command(host, "kp", "room.status", {"status": "archived"})
    assert send(host)["code"] == "ROOM_ARCHIVED"
    assert command(host, "player1", "chat.read", {"channelId": "general", "sequence": 1})["status"] == "committed"
    assert host.chat_history("player1", "general")["items"]


@pytest.mark.parametrize("extra", [{"senderAccountId": "kp"}, {"createdAt": 0}, {"kind": "action"}, {"card": {"result": 100}}, {"text": "x" * 4001}, {"assetIds": ["x", "x"]}])
def test_message_schema_rejects_forgery_and_limits(host, extra):
    before = host.store.generation
    with pytest.raises(DomainError, match="INPUT_INVALID"):
        command(host, "player1", "chat.message.send", {"channelId": "general", "text": "hello", **extra})
    assert host.store.generation == before


def test_speaker_attachment_reference_and_private_asset_boundary(host):
    assets = Assets(host)
    public = assets.upload("kp", "handout.txt", b"public")
    private = assets.upload("kp", "secret.txt", b"secret", "kp")
    assert send(host, assetIds=[private])["code"] == "NOT_VISIBLE"
    assert send(host, speakerId="actor-player2")["code"] == "NOT_VISIBLE"
    r = send(host, text="", assetIds=[public])["result"]
    assert command(host, "kp", "asset.remove", {"assetId": public})["code"] == "REFERENCE_CONFLICT"
    assert command(host, "player1", "chat.message.retract", {"channelId": "general", "messageId": r["messageId"], "revision": 1})["status"] == "committed"
    assert command(host, "kp", "asset.remove", {"assetId": public})["status"] == "committed"


def test_verified_action_card_uses_host_receipt_and_is_immutable(host):
    result = invoke(host, "player1", "demo.check", {"actor": "actor-player1", "skill": "skill-player1"}, "roll")
    assert result["status"] == "committed", result
    r = command(host, "player1", "chat.message.share", {"channelId": "general", "commandId": "roll"})
    assert r["status"] == "committed", r
    msg = host.chat_history("player2", "general")["items"][0]
    assert msg["card"]["result"] == result["result"]
    assert msg["card"]["rolls"] == host.state()["commands"]["player1:roll"]["random"]
    assert command(host, "player1", "chat.message.edit", {"channelId": "general", "messageId": msg["messageId"], "revision": 1, "text": "forged"})["code"] == "INPUT_INVALID"
    assert command(host, "player2", "chat.message.share", {"channelId": "general", "commandId": "roll"})["code"] == "NOT_VISIBLE"
    command(host, "kp", "entity.update", {"id": "skill-player1", "visibility": "owner"})
    assert command(host, "player1", "chat.message.share", {"channelId": "general", "commandId": "roll"})["code"] == "PERMISSION_DENIED"


def test_legacy_room_upgrade_is_once_and_backup_restores_chat(host, tmp_path):
    legacy = host.state(); legacy.pop("chat"); host.commit(legacy)
    before = host.store.generation
    host.close(); host.__init__(host.path)
    assert host.store.generation == before + 1
    assert host.project("player1")["chatChannels"]["general"]["lastSequence"] == 0
    host.close(); host.__init__(host.path)
    assert host.store.generation == before + 1
    cid = group(host); send(host, cid=cid)
    command(host, "player1", "chat.read", {"channelId": cid, "sequence": 1})
    assets = Assets(host); assets.backup("kp", tmp_path / "backup", True)
    restore_host(tmp_path / "backup", tmp_path / "restored")
    restored = Host(tmp_path / "restored")
    try:
        assert restored.state()["chat"] == host.state()["chat"]
        assert restored.chat_history("player1", cid) == host.chat_history("player1", cid)
        with pytest.raises(DomainError, match="NOT_VISIBLE"):
            restored.chat_history("player2", cid)
    finally:
        restored.close()


@pytest.mark.parametrize("corrupt", ["sequence", "reply", "sender", "read", "asset"])
def test_model_rejects_corrupt_chat_references(host, corrupt):
    send(host)
    s = host.state(); msg = s["chat"]["messages"]["general"][0]
    if corrupt == "sequence": msg["sequence"] = 2
    if corrupt == "reply": msg["replyTo"] = msg["messageId"]
    if corrupt == "sender": msg["senderAccountId"] = "missing"
    if corrupt == "read": s["chat"]["readPositions"]["player1"] = {"general": 2}
    if corrupt == "asset": msg["assetIds"] = ["missing"]
    with pytest.raises(DomainError):
        validate(s)


def test_rate_limit_and_retention_limit_roll_back(host, monkeypatch):
    now = [1000]; host.clock = lambda: now[0]
    for i in range(30):
        assert send(host, text=str(i))["status"] == "committed"
    assert send(host)["code"] == "RATE_LIMITED"
    now[0] += 11
    assert send(host)["status"] == "committed"
    monkeypatch.setattr(chat, "MAX_MESSAGES", 31)
    assert send(host)["code"] == "LIMIT_EXCEEDED"
    assert len(host.chat_history("player1", "general")["items"]) == 31


@pytest.mark.parametrize("point", ["before_chat_commit", "after_chat_commit"])
def test_real_process_crash_chat_and_receipt_are_atomic(tmp_path, point):
    folder = tmp_path / "host"
    h = Host(folder, bootstrap="test-password")
    envelope = message(h, "player1", "chat.message.send", {"channelId": "general", "text": "durable"}, "crash-chat")
    path = tmp_path / "message.json"; path.write_text(json.dumps(envelope))
    h.close()
    result = subprocess.run([sys.executable, str(ROOT / "acceptance/crash_worker.py"), "host", str(folder), point, str(path)], capture_output=True, timeout=30)
    assert result.returncode == 70, result.stderr.decode(errors="replace")
    h = Host(folder)
    try:
        saved = json.loads(path.read_text())
        if point == "before_chat_commit":
            assert h.receipt("player1", "crash-chat")["status"] == "unknown"
            assert not h.chat_history("player1", "general")["items"]
            saved["payload"]["authorityEpoch"] = h.epoch
        assert h.command("player1", saved)["status"] == "committed"
        assert h.command("player1", saved)["status"] == "committed"
        assert len(h.chat_history("player1", "general")["items"]) == 1
    finally:
        h.close()


def test_http_history_auth_csrf_and_inprocess_equivalence(host):
    cid = group(host); send(host, cid=cid)
    with TestClient(create_app(host, 8765), base_url="http://127.0.0.1:8765") as c:
        c.headers["origin"] = "http://127.0.0.1:8765"
        assert c.post("/api/v1/chat/history", json={"channelId": cid}).status_code == 401
        csrf = c.post("/api/v1/login", json={"loginName": "player1", "password": "test-password"}).json()["csrf"]
        assert c.post("/api/v1/chat/history", json={"channelId": cid}).status_code == 403
        c.headers["x-csrf-token"] = csrf
        people = c.get("/api/v1/chat/members").json()["items"]
        assert people == InProcessTransport(host, "player1").chat_members()
        assert all(set(person) == {"accountId", "memberId", "nickname", "role"} for person in people)
        assert c.post("/api/v1/chat/history", json={"channelId": cid}).json() == InProcessTransport(host, "player1").chat_history(cid)
        for args in ({"channelId": cid, "limit": 101}, {"channelId": cid, "before": 0}, {"channelId": cid, "limit": True}):
            assert c.post("/api/v1/chat/history", json=args).json()["code"] == "INPUT_INVALID"
        update(host, cid, participants=["kp"])
        assert c.post("/api/v1/chat/history", json={"channelId": cid}).status_code == 404
        command(host, "kp", "member.update", {"accountId": "player1", "active": False})
        assert c.post("/api/v1/chat/history", json={"channelId": "general"}).status_code == 403


def test_channel_management_permissions_stale_versions_and_atomic_rejection(host, monkeypatch):
    assert command(host, "player1", "chat.channel.create", {"kind": "room", "name": "x"})["code"] == "PERMISSION_DENIED"
    cid = group(host)
    args = {"channelId": cid, "revision": 1, "participants": ["kp", "missing"]}
    assert command(host, "kp", "chat.channel.update", args)["code"] == "NOT_VISIBLE"
    assert host.project("player1")["chatChannels"][cid]["revision"] == 1
    assert command(host, "player1", "chat.channel.update", {"channelId": cid, "revision": 1, "name": "x"})["code"] == "PERMISSION_DENIED"
    send(host, cid=cid)
    assert command(host, "kp", "chat.channel.update", {"channelId": cid, "revision": 1, "name": "stale"})["code"] == "VERSION_CONFLICT"
    monkeypatch.setattr(chat, "MAX_CHANNELS", 2)
    assert command(host, "kp", "chat.channel.create", {"kind": "room", "name": "full"})["code"] == "LIMIT_EXCEEDED"
    assert len(host.state()["chat"]["channels"]) == 2


def test_empty_message_and_retracted_reply_are_consistent(host):
    assert send(host, text=" ")["code"] == "INPUT_INVALID"
    first = send(host)["result"]
    command(host, "player1", "chat.message.retract", {"channelId": "general", "messageId": first["messageId"], "revision": 1})
    assert send(host, "player2", replyTo=first["messageId"])["status"] == "committed"
    assert host.chat_history("player2", "general")["items"][1]["replyTo"] == first["messageId"]
