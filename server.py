#!/bin/env python
import asyncio
import threading
from mitmproxy import options
from mitmproxy.tools import dump
from autotind.flow_utils import InterceptorMiddleware
from flows import DislikeInterceptor, LikeInterceptor, MatchInterceptor, RecsInterceptor
from handlers import register_work_handlers
from autotind.processor import Processor

processor = Processor()
register_work_handlers(processor)

async def start_proxy(host, port):
    opts = options.Options(listen_host=host, listen_port=port)

    master = dump.DumpMaster(
        opts,
        with_termlog=False,
        with_dumper=False,
    )
    master.options.setter('block_global')(False)
    tinder_middleware = InterceptorMiddleware([
        RecsInterceptor(processor),
        LikeInterceptor(processor),
        DislikeInterceptor(processor),
        MatchInterceptor(processor)
    ])

    master.addons.add(tinder_middleware)

    try:
        await master.run()
    except KeyboardInterrupt:
        master.shutdown()
    return master

def run_proxy():
    asyncio.run(start_proxy("*", 3000))

if __name__ == '__main__':
    t = threading.Thread(target=run_proxy)
    t.start()
    processor.run()
    t.join()
