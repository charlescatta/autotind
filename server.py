#!/bin/env python
import asyncio
import threading
from mitmproxy import options
from mitmproxy.tools import dump
from autotind.db import DB
from autotind.flow_utils import InterceptorMiddleware
from autotind.image_downloader import download_images
from flows import DislikeInterceptor, LikeInterceptor, MatchInterceptor, RecsInterceptor

async def start_proxy(host, port):
    opts = options.Options(listen_host=host, listen_port=port)
    db = DB()
    master = dump.DumpMaster(
        opts,
        with_termlog=True,
        with_dumper=False,
    )

    tinder_middleware = InterceptorMiddleware([
        RecsInterceptor(db),
        LikeInterceptor(db),
        DislikeInterceptor(db),
        MatchInterceptor(db)
    ])

    master.addons.add(tinder_middleware)
    
    try:
        await master.run()
    except KeyboardInterrupt:
        master.shutdown()
    return master

def run():
    asyncio.run(start_proxy("localhost", 3000))

if __name__ == '__main__':
    server_thread = threading.Thread(target=run)
    server_thread.start()
    downloader_thread = threading.Thread(target=download_images, daemon=True)
    downloader_thread.start()
    server_thread.join()
    downloader_thread.join()