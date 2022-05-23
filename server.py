#!/bin/env python
import asyncio
from mitmproxy import options
from mitmproxy.tools import dump
from mitmproxy.script import concurrent
from data.db import init_db
from mitmproxy import http
from flows import save_tinder_dislikes, save_tinder_likes, save_tinder_matches, save_tinder_recs

class TinderMiddleware:
    @concurrent
    def response(self, flow: http.HTTPFlow):
        if "tinder" not in flow.request.pretty_host:
            return
        session = init_db()
        save_tinder_recs(flow, session)
        save_tinder_likes(flow, session)
        save_tinder_dislikes(flow, session)
        save_tinder_matches(flow, session)

async def start_proxy(host, port):
    opts = options.Options(listen_host=host, listen_port=port)

    master = dump.DumpMaster(
        opts,
        with_termlog=False,
        with_dumper=False,
    )
    master.addons.add(TinderMiddleware())
    try:
        await master.run()
    except KeyboardInterrupt:
        master.shutdown()
    return master

if __name__ == '__main__':
    asyncio.run(start_proxy("0.0.0.0", 3000))