"""Transport-independent chat domain. Mutations run inside Host's room transaction."""
import copy
import uuid
from onlinecoc_data import canonical
from .errors import require
from .contracts import validate_model

MAX_CHANNELS = 128
MAX_MESSAGES = 10000
MAX_TEXT = 4000
MAX_PAGE = 100


def channel(channel_id, kind, name, participants=()):
    return {"channelId": channel_id, "kind": kind, "name": name,
            "participants": sorted(participants), "posting": "all", "muted": [],
            "archived": False, "revision": 1, "lastSequence": 0}


def initial_state():
    return {"schemaVersion": 1, "channels": {"general": channel("general", "room", "公共频道")},
            "messages": {"general": []}, "readPositions": {}}


def can_read(state, account, c):
    m = state["members"].get(account)
    return bool(m and m["active"] and c and
                (c["kind"] == "room" or account in c["participants"]))


def get_channel(state, account, channel_id):
    c = state["chat"]["channels"].get(channel_id)
    require(can_read(state, account, c), "NOT_VISIBLE")
    return c


def can_post(state, account, c):
    return (can_read(state, account, c) and state["status"] != "archived"
            and not c["archived"] and account not in c["muted"]
            and (c["posting"] == "all" or state["members"][account]["role"] == "kp"))


def project(state, account):
    result = {}
    positions = state["chat"]["readPositions"].get(account, {})
    for cid, c in state["chat"]["channels"].items():
        if not can_read(state, account, c):
            continue
        out = copy.deepcopy(c)
        if state["members"][account]["role"] != "kp":
            out.pop("muted")
        out["canPost"] = can_post(state, account, c)
        out["readSequence"] = positions.get(cid, 0)
        out["unreadCount"] = sum(m["sequence"] > out["readSequence"] and
                                  m["senderAccountId"] != account and not m["deleted"]
                                  for m in state["chat"]["messages"][cid])
        result[cid] = out
    return result


def history(state, account, channel_id, before=None, limit=50):
    c = get_channel(state, account, channel_id)
    require(type(limit) is int and 1 <= limit <= MAX_PAGE)
    require(before is None or (type(before) is int and 1 <= before <= 2**53-1))
    # Sequence numbers belong to a single channel; private activity has no public cursor.
    end = min(c["lastSequence"], before - 1) if before is not None else c["lastSequence"]
    start = max(0, end - limit)
    return {"channelId": channel_id, "channelRevision": c["revision"],
            "lastSequence": c["lastSequence"],
            "items": copy.deepcopy(state["chat"]["messages"][channel_id][start:end]),
            "nextBefore": start + 1 if start else None}


def valid_participants(state, accounts):
    require(all(a in state["members"] and state["members"][a]["active"] for a in accounts),
            "NOT_VISIBLE")


def create(state, c):
    require(len(state["chat"]["channels"]) < MAX_CHANNELS, "LIMIT_EXCEEDED")
    state["chat"]["channels"][c["channelId"]] = c
    state["chat"]["messages"][c["channelId"]] = []
    return {"channelId": c["channelId"]}


def apply(state, account, op, args, now):
    chat = state["chat"]
    is_kp = state["members"][account]["role"] == "kp"
    if op == "chat.direct.open":
        require(state["status"] != "archived", "ROOM_ARCHIVED")
        peer = args["accountId"]
        require(peer != account)
        valid_participants(state, [peer])
        pair = sorted([account, peer])
        for c in chat["channels"].values():
            if c["kind"] == "direct" and sorted(c["participants"]) == pair:
                return {"channelId": c["channelId"]}
        return create(state, channel(uuid.uuid4().hex, "direct", "私聊", pair))
    if op == "chat.channel.create":
        require(is_kp, "PERMISSION_DENIED")
        require(state["status"] != "archived", "ROOM_ARCHIVED")
        require(args["name"].strip())
        participants = args.get("participants", [])
        if args["kind"] == "group":
            require(account in participants)
            valid_participants(state, participants)
        else:
            require(not participants)
        c = channel(uuid.uuid4().hex, args["kind"], args["name"], participants)
        c["posting"] = args.get("posting", "all")
        return create(state, c)

    c = get_channel(state, account, args["channelId"])
    cid = c["channelId"]
    if op == "chat.read":
        require(args["sequence"] <= c["lastSequence"])
        positions = chat["readPositions"].setdefault(account, {})
        positions[cid] = max(positions.get(cid, 0), args["sequence"])
        return {"channelId": cid, "readSequence": positions[cid]}
    require(state["status"] != "archived", "ROOM_ARCHIVED")
    if op == "chat.channel.update":
        require(is_kp and c["kind"] != "direct", "PERMISSION_DENIED")
        require(c["revision"] == args["revision"], "VERSION_CONFLICT")
        if "participants" in args:
            require(c["kind"] == "group")
            valid_participants(state, args["participants"])
        if "muted" in args:
            valid_participants(state, args["muted"])
        if "name" in args:
            require(args["name"].strip())
        for field in ("name", "participants", "posting", "muted", "archived"):
            if field in args:
                c[field] = copy.deepcopy(args[field])
        c["revision"] += 1
        return {"channelId": cid, "revision": c["revision"]}

    messages = chat["messages"][cid]
    if op in ("chat.message.edit", "chat.message.retract"):
        require(not c["archived"], "CHANNEL_READ_ONLY")
        msg = next((m for m in messages if m["messageId"] == args["messageId"]), None)
        require(msg, "NOT_VISIBLE")
        own = msg["senderAccountId"] == account
        require(own or (op == "chat.message.retract" and is_kp), "PERMISSION_DENIED")
        # Retraction remains possible for a muted author; editing must obey posting policy.
        if op == "chat.message.edit":
            require(can_post(state, account, c), "CHANNEL_READ_ONLY")
            require(msg["kind"] == "text" and args["text"].strip())
        require(msg["revision"] == args["revision"], "VERSION_CONFLICT")
        require(not msg["deleted"], "MESSAGE_RETRACTED")
        msg.update(revision=msg["revision"] + 1, updatedAt=max(now, msg["createdAt"]))
        if op == "chat.message.edit":
            msg["text"] = args["text"]
        else:
            msg.update(deleted=True, text="", assetIds=[], card=None,
                       speakerId=None, speakerName=None)
        c["revision"] += 1
        return {"channelId": cid, "messageId": msg["messageId"], "revision": msg["revision"]}

    require(op in ("chat.message.send", "chat.message.share"), "UNKNOWN_OPERATION")
    require(can_post(state, account, c), "CHANNEL_READ_ONLY")
    require(sum(len(ms) for ms in chat["messages"].values()) < MAX_MESSAGES, "LIMIT_EXCEEDED")
    require(sum(m["senderAccountId"] == account and m["createdAt"] > now - 10
                for ms in chat["messages"].values() for m in ms) < 30, "RATE_LIMITED")
    reply = args.get("replyTo")
    require(reply is None or any(m["messageId"] == reply for m in messages), "NOT_VISIBLE")
    msg = {"messageId": uuid.uuid4().hex, "channelId": cid,
           "sequence": c["lastSequence"] + 1, "senderAccountId": account,
           "createdAt": now, "updatedAt": now, "revision": 1, "deleted": False,
           "kind": "text", "text": args.get("text", ""), "replyTo": reply,
           "assetIds": args.get("assetIds", []), "speakerId": None, "speakerName": None, "card": None}
    if op == "chat.message.send":
        require(msg["text"].strip() or msg["assetIds"])
        for aid in msg["assetIds"]:
            a = state["assets"].get(aid)
            # Asset permissions are separate; a private channel does not make a public file private.
            require(a and a["ready"] and a["visibility"] == "public", "NOT_VISIBLE")
        if args.get("speakerId"):
            e = state["entities"].get(args["speakerId"])
            require(e and e["lifecycle"] == "active" and e["typeRef"] == "actor"
                    and e["visibility"] == "public" and (is_kp or e["owner"] == account), "NOT_VISIBLE")
            msg.update(speakerId=e["instanceId"], speakerName=e["name"])
    else:
        rec = state["commands"].get(account + ":" + args["commandId"])
        require(rec and rec["status"] == "committed" and
                rec.get("op") in ("action.invoke", "behavior.invoke"), "NOT_VISIBLE")
        metadata = state["artifacts"][rec["ruleset"]]["metadata"][rec["rule"]]
        require(metadata["mode"] == "action" and metadata["public"] and not metadata["kp"], "PERMISSION_DENIED")
        require(all(k == "@relations" or (k in state["entities"] and state["entities"][k]["visibility"] == "public")
                    for k in rec.get("reads", {})), "PERMISSION_DENIED")
        card = {"accountId": account, "commandId": rec["id"], "ruleId": rec["rule"],
                "rulesetRevision": rec["ruleset"], "result": copy.deepcopy(rec["receipt"].get("result")),
                "rolls": copy.deepcopy(rec["random"])}
        require(len(canonical(card)) <= 8192, "LIMIT_EXCEEDED")
        msg.update(kind="action", card=card)
    messages.append(msg)
    c.update(lastSequence=msg["sequence"], revision=c["revision"] + 1)
    return {"channelId": cid, "messageId": msg["messageId"], "sequence": msg["sequence"], "revision": 1}


def validate(state):
    chat = state["chat"]
    validate_model("ChatState", chat)
    require(set(chat["channels"]) == set(chat["messages"]), "REFERENCE_CONFLICT")
    require(sum(map(len, chat["messages"].values())) <= MAX_MESSAGES, "LIMIT_EXCEEDED")
    ids = set()
    pairs = set()
    for cid, c in chat["channels"].items():
        require(cid == c["channelId"] and c["name"].strip())
        require(all(a in state["members"] for a in c["participants"] + c["muted"]), "REFERENCE_CONFLICT")
        require(c["kind"] != "room" or not c["participants"])
        if c["kind"] == "direct":
            pair = tuple(sorted(c["participants"]))
            require(len(pair) == 2 and pair not in pairs and c["posting"] == "all" and not c["muted"] and not c["archived"])
            pairs.add(pair)
        messages = chat["messages"][cid]
        require(c["lastSequence"] == len(messages))
        seen = set()
        for seq, m in enumerate(messages, 1):
            require(m["messageId"] not in ids and m["channelId"] == cid and m["sequence"] == seq)
            require(m["senderAccountId"] in state["members"], "REFERENCE_CONFLICT")
            require(m["replyTo"] is None or m["replyTo"] in seen, "REFERENCE_CONFLICT")
            require(m["speakerId"] is None or m["speakerId"] in state["entities"], "REFERENCE_CONFLICT")
            require(all(a in state["assets"] and state["assets"][a]["visibility"] == "public" for a in m["assetIds"]), "REFERENCE_CONFLICT")
            require(m["updatedAt"] >= m["createdAt"])
            if m["deleted"]:
                require(not m["text"] and not m["assetIds"] and m["card"] is None and m["speakerId"] is None and m["speakerName"] is None)
            elif m["kind"] == "action":
                require(m["card"] is not None and not m["text"] and not m["assetIds"])
                card = m["card"]
                rec = state["commands"].get(card["accountId"] + ":" + card["commandId"])
                require(rec and rec["status"] == "committed" and card["accountId"] == m["senderAccountId"]
                        and rec.get("rule") == card["ruleId"] and rec.get("ruleset") == card["rulesetRevision"]
                        and rec["receipt"].get("result") == card["result"] and rec["random"] == card["rolls"], "REFERENCE_CONFLICT")
                require(len(canonical(card)) <= 8192, "LIMIT_EXCEEDED")
            else:
                require(m["card"] is None and (m["text"].strip() or m["assetIds"]))
            ids.add(m["messageId"])
            seen.add(m["messageId"])
    for account, positions in chat["readPositions"].items():
        require(account in state["members"], "REFERENCE_CONFLICT")
        require(all(cid in chat["channels"] and seq <= chat["channels"][cid]["lastSequence"] for cid, seq in positions.items()), "REFERENCE_CONFLICT")
