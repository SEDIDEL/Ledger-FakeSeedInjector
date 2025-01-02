import cloudscraper
import random
import time
import json
import urllib3
import logging
from datetime import datetime
from pathlib import Path
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from ssl import create_default_context, CERT_NONE
from typing import List, Dict, Optional, Tuple

# Configuración de constantes
BASE_URL = 'https://ledger-verify.support'
API_ENDPOINT = f'{BASE_URL}/asset/modal/api.php'
REQUEST_TIMEOUT = 30
RETRY_DELAY_MIN = 4
RETRY_DELAY_MAX = 8
MAX_RETRIES = 3
WORDS_FILE_PATH = '/Users/sebastian/Downloads/english.txt'
LOG_FILE = 'seed_generator.log'

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Desactivar advertencias SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SSLAdapter(HTTPAdapter):
    """Adaptador personalizado para deshabilitar verificación SSL"""
    def __init__(self, *args, **kwargs):
        self.context = create_default_context()
        self.context.check_hostname = False
        self.context.verify_mode = CERT_NONE
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['ssl_context'] = self.context
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        kwargs['ssl_context'] = self.context
        return super().proxy_manager_for(*args, **kwargs)

class Stats:
    """Clase para manejar estadísticas"""
    def __init__(self):
        self.requests_sent = 0
        self.successful_requests = 0
        self.errors = 0
        self.start_time = datetime.now()
        self.last_success_time: Optional[datetime] = None

    def log_request(self, success: bool):
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
            f"\nEstadísticas:"
            f"\nTiempo de ejecución: {runtime}"
            f"\nTotal enviados: {self.requests_sent}"
            f"\nExitosos: {self.successful_requests}"
            f"\nErrores: {self.errors}"
            f"\nTasa de éxito: {self.get_success_rate():.2f}%"
        )

class SeedGenerator:
    """Clase principal para generar y enviar seeds"""
    def __init__(self):
        self.words = self._load_words()
        self.stats = Stats()
        self.scraper = None

    def _load_words(self) -> List[str]:
        """Carga las palabras BIP39 del archivo"""
        try:
            words_path = Path(WORDS_FILE_PATH)
            if not words_path.exists():
                raise FileNotFoundError(f"No se encontró el archivo: {WORDS_FILE_PATH}")
            
            with words_path.open('r') as file:
                words = [line.strip() for line in file if line.strip()]
            
            if not words:
                raise ValueError("El archivo de palabras está vacío")
            
            logger.info(f"Palabras BIP39 cargadas: {len(words)}")
            return words
            
        except Exception as e:
            logger.error(f"Error al cargar palabras BIP39: {str(e)}")
            # Lista mínima de respaldo
            return ["abandon", "ability", "able", "about", "above", "absent", 
                   "absorb", "abstract", "absurd", "abuse", "access", "accident", 
                   "account", "accuse", "achieve", "acid", "acoustic", "acquire", 
                   "across", "act"]

    @staticmethod
    def get_random_headers() -> Dict[str, str]:
        """Genera headers aleatorios para las peticiones"""
        user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]

        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'User-Agent': random.choice(user_agents)
        }

    def init_cloudscraper(self):
        """Inicializa y configura el cloudscraper"""
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'darwin',
                'mobile': False
            },
            debug=True
        )
        adapter = SSLAdapter()
        self.scraper.mount('https://', adapter)
        self.scraper.mount('http://', adapter)

    def validate_cloudflare_access(self) -> bool:
        """Valida el acceso a través de Cloudflare"""
        try:
            logger.info("Estableciendo conexión con Cloudflare...")
            response = self.scraper.get(
                BASE_URL,
                headers=self.get_random_headers(),
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                logger.info("Conexión establecida con Cloudflare")
                return True
            
            logger.error(f"No se pudo establecer conexión. Status: {response.status_code}")
            return False

        except Exception as e:
            logger.error(f"Error al conectar con Cloudflare: {str(e)}")
            return False

    def generate_seed(self) -> Tuple[List[str], int]:
        """Genera una nueva seed aleatoria"""
        seed_length = random.choice([12, 24])
        seed_words = random.sample(self.words, seed_length)
        return seed_words, seed_length

    def create_payload(self, seed_words: List[str]) -> Dict:
        """Crea el payload para la petición"""
        return {
            'type': random.choice([2, 3, 5]),
            'data': {str(i+1): word for i, word in enumerate(seed_words)}
        }

    def exponential_backoff(self, attempt: int, base_delay: int = 5) -> float:
        """Calcula el tiempo de espera exponencial para reintentos"""
        delay = min(base_delay * (2 ** attempt), 60)  # máximo 60 segundos
        return random.uniform(delay * 0.8, delay * 1.2)  # añade algo de aleatoridad

    def send_fake_seed(self) -> bool:
        """Envía una seed falsa al servidor"""
        for attempt in range(MAX_RETRIES):
            try:
                seed_words, seed_length = self.generate_seed()
                payload = self.create_payload(seed_words)

                post_headers = self.get_random_headers()
                post_headers.update({
                    'Content-Type': 'application/json',
                    'Origin': BASE_URL,
                    'Referer': f'{BASE_URL}/'
                })

                response = self.scraper.post(
                    API_ENDPOINT,
                    json=payload,
                    headers=post_headers,
                    timeout=REQUEST_TIMEOUT
                )

                logger.info(f"\n{'='*50}")
                logger.info(f"Frase enviada (Intento {attempt + 1}/{MAX_RETRIES}):")
                logger.info(f"Longitud: {seed_length} palabras")
                logger.info(f"Frase: {' '.join(seed_words)}")
                logger.info(f"Estado: {response.status_code}")
                logger.info('='*50)

                if response.status_code == 403:
                    logger.warning("Cloudflare bloqueó la petición, reintentando...")
                    time.sleep(self.exponential_backoff(attempt))
                    continue

                success = response.status_code == 200
                self.stats.log_request(success)
                return success

            except RequestException as e:
                logger.error(f"Error de red en intento {attempt + 1}/{MAX_RETRIES}: {str(e)}")
                time.sleep(self.exponential_backoff(attempt))
            except Exception as e:
                logger.error(f"Error inesperado en intento {attempt + 1}/{MAX_RETRIES}: {str(e)}")
                time.sleep(self.exponential_backoff(attempt))

        self.stats.log_request(False)
        return False

    def run(self):
        """Método principal que ejecuta el generador de seeds"""
        logger.info("Iniciando script de protección...")

        while True:
            try:
                self.init_cloudscraper()

                if not self.validate_cloudflare_access():
                    logger.warning("Esperando antes de reintentar...")
                    time.sleep(30)
                    continue

                logger.info("\nComenzando envío de datos...")

                while True:
                    self.send_fake_seed()
                    
                    if self.stats.requests_sent % 5 == 0:
                        logger.info(self.stats.get_stats_summary())

                    time.sleep(random.uniform(RETRY_DELAY_MIN, RETRY_DELAY_MAX))

            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error(f"\nError en la sesión: {str(e)}")
                logger.info("Reiniciando sesión...")
                time.sleep(15)

def main():
    generator = SeedGenerator()
    try:
        generator.run()
    except KeyboardInterrupt:
        logger.info("\n\nScript detenido por el usuario")
        logger.info(generator.stats.get_stats_summary())
    except Exception as e:
        logger.error(f"\nError fatal: {str(e)}")
        logger.info(generator.stats.get_stats_summary())

if __name__ == "__main__":
    main()
