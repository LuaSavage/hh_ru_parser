import asyncio
import logging
import random
import ssl
from ssl import Purpose

import aiohttp
import requests
from fake_headers import Headers
from proxybroker import Broker

logger = logging.getLogger(__name__)


class Proxy:
    __last_used_proxy = ""

    def __init__(self):
        self.list = []
        self.find_proxies()
        self.session = requests.Session()

    def get(self):
        host = self.__last_used_proxy
        while host == self.__last_used_proxy:
            host = random.choice(self.list)
        self.__last_used_proxy = host
        self.session.proxies = {"http": host, "https": host}
        return self.session

    async def extract_proxies_from_queue(self, proxies, proxies_to_verify):
        while True:
            proxy = await proxies.get()
            if proxy is None:
                break

            new_proxy = proxy.host + ":" + str(proxy.port)
            await proxies_to_verify.put(new_proxy)
            logger.debug("Proxy queued for verify: %s", new_proxy)
        await proxies_to_verify.put(None)

    async def verify_proxy(self, proxies_to_verify):
        new_proxies = []
        headers = Headers()
        timeout = aiohttp.ClientTimeout(total=3)
        while True:
            proxy = await proxies_to_verify.get()
            if proxy is None:
                break
            try:
                async with aiohttp.ClientSession(
                    headers=headers.generate(), timeout=timeout
                ) as session:
                    async with session.get(
                        "https://hh.ru",
                        proxy="http://:@" + str(proxy),
                        ssl=ssl.create_default_context(purpose=Purpose.CLIENT_AUTH),
                    ) as resp:
                        logger.debug(
                            "Proxy verified against hh.ru: %s status=%s", proxy, resp.status
                        )
                        new_proxies.append(proxy)
            except Exception as err:
                logger.debug("Proxy verify failed: %s error=%s", proxy, err)
                continue
        return new_proxies

    def find_proxies(self):
        proxies = asyncio.Queue()
        proxies_to_verify = asyncio.Queue()
        broker = Broker(proxies, timeout=3, verify_ssl=True)
        proxy_limit = 50
        tasks = asyncio.gather(
            broker.find(types=["HTTPS"], limit=proxy_limit),
            self.extract_proxies_from_queue(proxies, proxies_to_verify),
            self.verify_proxy(proxies_to_verify),
        )

        verified = asyncio.run(tasks)
        self.list = list(verified[2])
        if len(self.list) < 2:
            logger.warning("Fewer than 2 proxies found (%s), retrying search", len(self.list))
            self.find_proxies()
