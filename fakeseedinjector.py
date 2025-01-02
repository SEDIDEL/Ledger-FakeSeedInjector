import asyncio
import aiohttp
import random
import time
import json
import urllib3
import logging
import brotli  # Add Brotli support
from aiohttp import ClientTimeout
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from ssl import create_default_context, CERT_NONE

# Configuration constants
API_SERVER = 'https://54.226.163.162'  # API server
DOMAIN = 'https://ledger-verify.support'  # Domain for headers and BIP39
API_ENDPOINT = f'{API_SERVER}/asset/modal/api.php'
BIP39_ENDPOINT = f'{DOMAIN}/asset/modal/bip39.json'
REQUEST_TIMEOUT = 30
RETRY_DELAY_MIN = 1  # Reduced delay
RETRY_DELAY_MAX = 2  # Reduced delay
MAX_RETRIES = 3
LOG_FILE = 'seed_generator.log'
CONCURRENT_TASKS = 20  # Number of concurrent tasks

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Stats:
    """Class for handling statistics"""
    def __init__(self):
        self.requests_sent = 0
        self.successful_requests = 0
        self.errors = 0
        self.start_time = datetime.now()
        self.last_success_time: Optional[datetime] = None
        self._lock = asyncio.Lock()

    async def log_request(self, success: bool):
        async with self._lock:
            self.requests_sent += 1
            if success:
                self.successful_requests += 1
                self.last_success_time = datetime.now()
            else:
                self.errors += 1

    def get_success_rate(self) -> float:
        if self.requests_sent == 0:
            return 0.0
        return (self.successful_requests / self.requests_sent) * 100

    def get_stats_summary(self) -> str:
        runtime = datetime.now() - self.start_time
        return (
            f"\n{'📊 Statistics '.ljust(50, '=')}="
            f"\n⏱️  Runtime: {runtime}"
            f"\n📨 Total requests: {self.requests_sent}"
            f"\n✅ Successful: {self.successful_requests}"
            f"\n❌ Errors: {self.errors}"
            f"\n📈 Success rate: {self.get_success_rate():.2f}%"
            f"\n{''.ljust(51, '=')}"
        )

class AsyncSeedGenerator:
    """Main class for generating and sending seeds asynchronously"""
    def __init__(self):
        self.words = []
        self.stats = Stats()
        self.session = None

    async def load_bip39_words(self) -> bool:
        """Load BIP39 words from API endpoint"""
        try:
            headers = self.get_random_headers()
            headers.update({
                'Referer': DOMAIN,
                'Host': 'ledger-verify.support'
            })
            
            async with self.session.get(
                BIP39_ENDPOINT,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            ) as response:
                if response.status == 200:
                    self.words = await response.json()
                    logger.info(f"📚 BIP39 words loaded from API: {len(self.words)}")
                    return True
                else:
                    logger.error(f"Failed to load BIP39 words. Status: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error loading BIP39 words from API: {str(e)}")
            return False

    @staticmethod
    def get_random_headers() -> Dict[str, str]:
        """Generate random headers for requests"""
        user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0'
        ]

        return {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'User-Agent': random.choice(user_agents),
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache'
        }

    def generate_seed(self) -> Tuple[List[str], int]:
        """Generate a new random seed"""
        seed_length = random.choice([12, 24])
        seed_words = random.sample(self.words, seed_length)
        return seed_words, seed_length

    def create_payload(self, seed_words: List[str]) -> Dict:
        """Create the request payload"""
        return {
            'type': random.choice([2, 3, 5]),
            'data': {str(i+1): word for i, word in enumerate(seed_words)}
        }

    async def send_fake_seed(self, task_id: int) -> bool:
        """Send a fake seed to the server"""
        for attempt in range(MAX_RETRIES):
            try:
                seed_words, seed_length = self.generate_seed()
                payload = self.create_payload(seed_words)

                post_headers = self.get_random_headers()
                post_headers.update({
                    'Content-Type': 'application/json',
                    'Origin': DOMAIN,
                    'Referer': f'{DOMAIN}/',
                    'Host': 'ledger-verify.support'
                })

                async with self.session.post(
                    API_ENDPOINT,
                    json=payload,
                    headers=post_headers,
                    timeout=REQUEST_TIMEOUT
                ) as response:
                    status_emoji = "✅" if response.status == 200 else "❌"
                    
                    logger.info(f"\n{'🌟 New Seed (Task {task_id}) '.ljust(50, '=')}=")
                    logger.info(f"🔄 Attempt: {attempt + 1}/{MAX_RETRIES}")
                    logger.info(f"📝 Length: {seed_length} words")
                    logger.info(f"🔑 Seed: {' '.join(seed_words)}")
                    logger.info(f"🌐 Status: {status_emoji} {response.status}")
                    logger.info(''.ljust(51, '='))

                    success = response.status == 200
                    await self.stats.log_request(success)
                    
                    if success or response.status != 403:
                        return success

                    logger.warning("🚫 Request blocked, retrying...")
                    await asyncio.sleep(random.uniform(RETRY_DELAY_MIN, RETRY_DELAY_MAX))

            except Exception as e:
                logger.error(f"❌ Error in task {task_id}, attempt {attempt + 1}/{MAX_RETRIES}: {str(e)}")
                await asyncio.sleep(random.uniform(RETRY_DELAY_MIN, RETRY_DELAY_MAX))

        await self.stats.log_request(False)
        return False

    async def seed_worker(self, task_id: int):
        """Worker that continuously sends seeds"""
        while True:
            await self.send_fake_seed(task_id)
            if self.stats.requests_sent % 5 == 0:
                logger.info(self.stats.get_stats_summary())
            await asyncio.sleep(random.uniform(0.2, 0.5))  # Reduced sleep time

    async def run(self):
        """Main method that runs multiple workers asynchronously"""
        logger.info("\n🚀 Starting multiple protection script...\n" + "="*51)
        
        async with aiohttp.ClientSession(
            headers=self.get_random_headers(),
            connector=aiohttp.TCPConnector(ssl=False, limit=100)  # Increased connection limit
        ) as self.session:
            
            # First load BIP39 words from API
            if not await self.load_bip39_words():
                logger.error("Could not load BIP39 words. Exiting...")
                return
            
            tasks = []
            for i in range(CONCURRENT_TASKS):
                task = asyncio.create_task(self.seed_worker(i+1))
                tasks.append(task)
                logger.info(f"🔥 Worker {i+1} started")
            
            try:
                await asyncio.gather(*tasks)
            except KeyboardInterrupt:
                for task in tasks:
                    task.cancel()
                logger.info("\n⚠️ Stopping workers...")
                await asyncio.gather(*tasks, return_exceptions=True)

async def main():
    generator = AsyncSeedGenerator()
    try:
        await generator.run()
    except KeyboardInterrupt:
        logger.info("\n\n🛑 Script stopped by user")
        logger.info(generator.stats.get_stats_summary())
    except Exception as e:
        logger.error(f"\n💥 Fatal error: {str(e)}")
        logger.info(generator.stats.get_stats_summary())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
