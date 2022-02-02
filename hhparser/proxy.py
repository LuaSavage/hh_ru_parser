import asyncio, aiohttp, requests
from proxybroker import Broker
from fake_headers import Headers 
from ssl import Purpose
import random, ssl

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

    async def extract_froxies_from_queue(self, proxies, proxies_to_verify):
        while True:
            proxy = await proxies.get()
            if proxy is None: break

            new_proxy = proxy.host+":"+str(proxy.port)
            await proxies_to_verify.put(new_proxy)
            print("new added to verify",new_proxy)
        await proxies_to_verify.put(None)

    async def verify_proxy(self, proxies_to_verify):
        new_proxies = []
        headers = Headers()
        timeout = aiohttp.ClientTimeout(total=3)
        while True:
            proxy = await proxies_to_verify.get()
            if proxy is None: break
            try:
                async with aiohttp.ClientSession(headers=headers.generate(), 
                                                 timeout = timeout) as session:
                    async with session.get("https://hh.ru",
                                        proxy='http://:@'+str(proxy),
                                        ssl = ssl.create_default_context(purpose=Purpose.CLIENT_AUTH)) as resp:
                        print("Verified, resp status:"+str(resp.status))
                        new_proxies.append(proxy)
            except Exception as err:
                print("async verifying err ",proxy,": "+str(err))
                continue 
        return new_proxies

    def find_proxies(self):
        proxies = asyncio.Queue()
        proxies_to_verify = asyncio.Queue()        
        broker = Broker(proxies)
        proxy_limit = 50
        tasks = asyncio.gather(
            broker.find(types=['HTTPS'], 
                        timout = 3, 
                        verify_ssl  = True,
                        limit=proxy_limit),
            self.extract_froxies_from_queue(proxies, proxies_to_verify),
            self.verify_proxy(proxies_to_verify))

        loop = asyncio.get_event_loop()
        futures = loop.run_until_complete(tasks)
        self.list = list(futures[2])
        if len(self.list) <2:
            print("No one proxy not found, retry")
            self.find_proxies()
