import json
from playwright.sync_api import sync_playwright
from test_network import live_server, wait


def test_chat_sdk_real_browsers_sync_privacy_reconnect_and_revocation(live_server):
    url, _, _ = live_server
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        contexts = []
        try:
            pages = []
            for account in ("kp", "player1", "player2"):
                context = browser.new_context(); contexts.append(context)
                page = context.new_page(); pages.append(page)
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(url)
                page.evaluate("async account=>await playtest.login(account,'test-password')", account)
                wait(page, "playtest.connected")
            kp, p1, p2 = pages
            assert len(p1.evaluate("async()=> (await playtest.chatMembers()).items")) == 3
            sent = p1.evaluate("async()=>await playtest.sendChat('general','browser hello',{},'chat-browser-send')")
            assert sent["status"] == "committed"
            for page in pages:
                wait(page, "playtest.view.chatChannels.general.lastSequence===1")
            assert p2.evaluate("async()=> (await playtest.chatHistory('general')).items[0].text") == "browser hello"
            # Reconnect resets view; exact envelope retry produces one message.
            p1.evaluate("playtest.socket.close()")
            wait(p1, "!playtest.connected")
            wait(p1, "playtest.connected")
            assert p1.evaluate("async()=>await playtest.sendChat('general','browser hello',{},'chat-browser-send')") == sent
            assert len(p2.evaluate("async()=> (await playtest.chatHistory('general')).items")) == 1
            p2.evaluate("async()=>await playtest.markChatRead('general',1)")
            wait(p2, "playtest.view.chatChannels.general.readSequence===1")
            # Private-channel traffic never appears in a nonparticipant's full projection.
            public_before = kp.evaluate("JSON.stringify(playtest.view)")
            direct = p1.evaluate("async()=> (await playtest.openDirect('player2')).result.channelId")
            wait(p2, "cid=>!!playtest.view.chatChannels[cid]", arg=direct)
            p1.evaluate("async cid=>await playtest.sendChat(cid,'private browser text')", direct)
            wait(p2, "cid=>playtest.view.chatChannels[cid].lastSequence===1", arg=direct)
            assert kp.evaluate("JSON.stringify(playtest.view)") == public_before
            assert p2.evaluate("async cid=>(await playtest.chatHistory(cid)).items[0].text", direct) == "private browser text"
            assert kp.evaluate("async cid=>{try{await playtest.chatHistory(cid);return 'allowed'}catch(e){return e.code}}", direct) == "NOT_VISIBLE"
            cid = kp.evaluate("async()=> (await playtest.command('chat.channel.create',{kind:'group',name:'group',participants:['kp','player1']})).result.channelId")
            wait(p1, "cid=>!!playtest.view.chatChannels[cid]", arg=cid)
            assert p2.evaluate("cid=>cid in playtest.view.chatChannels", cid) is False
            kp.evaluate("async cid=>await playtest.command('chat.channel.update',{channelId:cid,revision:1,participants:['kp']})", cid)
            wait(p1, "cid=>!(cid in playtest.view.chatChannels)", arg=cid)
            assert p1.evaluate("async cid=>{try{await playtest.chatHistory(cid);return 'allowed'}catch(e){return e.code}}", cid) == "NOT_VISIBLE"
            assert not errors, errors
        finally:
            for context in contexts: context.close()
            browser.close()
