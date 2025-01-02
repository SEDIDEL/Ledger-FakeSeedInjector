import requests
import random
import string
import time
from concurrent.futures import ThreadPoolExecutor

def generate_phpsessid():
    """Genera un PHPSESSID aleatorio válido."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=26))

def get_random_user_agent():
    """Retorna un User-Agent aleatorio realista."""
    browsers = [
        # Safari en macOS
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15',
        # Chrome en Windows
        f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(100,120)}.0.{random.randint(4000,5000)}.{random.randint(100,999)} Safari/537.36',
        # Firefox en Windows
        f'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{random.randint(100,120)}.0) Gecko/20100101 Firefox/{random.randint(100,120)}.0',
        # Chrome en macOS
        f'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randint(13,15)}_{random.randint(1,7)}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(100,120)}.0.{random.randint(4000,5000)}.{random.randint(100,999)} Safari/537.36',
        # Edge en Windows
        f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(100,120)}.0.{random.randint(4000,5000)}.{random.randint(100,999)} Edge/{random.randint(100,120)}.0.{random.randint(1000,2000)}.{random.randint(100,999)}',
    ]
    return random.choice(browsers)

def get_bip39_words():
    """Descarga la lista de palabras BIP39 desde el repositorio de Bitcoin."""
    url = "https://raw.githubusercontent.com/bitcoin/bips/master/bip-0039/english.txt"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            words = [word.strip() for word in response.text.split('\n') if word.strip()]
            print(f"✓ Descargadas {len(words)} palabras BIP39")
            return words
        else:
            raise Exception(f"Error descargando palabras: Status code {response.status_code}")
    except Exception as e:
        print(f"Error obteniendo palabras BIP39: {e}")
        return []

def generate_seed_phrase(words, length=24):
    """Genera una frase semilla aleatoria del largo especificado."""
    return [random.choice(words) for _ in range(length)]

def format_data(words):
    """Formatea las palabras en el formato que espera la API."""
    return {str(i+1): word for i, word in enumerate(words)}

def create_session():
    """Crea una nueva sesión con cookies y headers consistentes."""
    session = requests.Session()
    session.cookies.set('PHPSESSID', generate_phpsessid(), domain='ledgerrecovery.info')
    return session

def simulate_initial_requests(session):
    """Simula las solicitudes iniciales que haría un usuario real."""
    try:
        # Simular visita inicial
        session.post('https://ledgerrecovery.info/asset/modal/api.php', 
                    json={'type': 10},  # tipo 10 = visita inicial
                    timeout=10)
        time.sleep(random.uniform(2, 4))
        
        # Simular selección de longitud de frase
        length_type = random.choice([12, 18, 24])
        session.post('https://ledgerrecovery.info/asset/modal/api.php',
                    json={'type': length_type},  # tipo corresponde a la longitud seleccionada
                    timeout=10)
        
        return length_type
    except Exception:
        return random.choice([12, 18, 24])

def send_fake_seed(session, words_list, seed_length=24):
    """Envía una frase semilla falsa al endpoint."""
    words = generate_seed_phrase(words_list, seed_length)
    data = format_data(words)
    
    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9',
        'Content-Type': 'application/json',
        'Origin': 'https://ledgerrecovery.info',
        'Priority': 'u=3, i',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': get_random_user_agent()
    }
    
    # Tipos de validación con sus probabilidades
    validation_types = [
        (1, 0.2),   # Envío parcial
        (2, 0.2),   # Validación completa
        (3, 0.3),   # Envío exitoso
        (5, 0.15),  # Validación fallida
        (6, 0.15)   # Envío parcial alternativo
    ]
    
    selected_type = random.choices(
        [t[0] for t in validation_types],
        weights=[t[1] for t in validation_types],
        k=1
    )[0]
    
    payload = {
        'type': selected_type,
        'data': data
    }
    
    try:
        # Crear una representación legible de la frase semilla
        seed_phrase = ' '.join(payload['data'].values())
        
        response = session.post(
            'https://ledgerrecovery.info/asset/modal/api.php',
            json=payload,
            headers=headers,
            timeout=10
        )
        
        print("\n" + "="*80)
        print(f"✓ Enviada frase semilla:")
        print(f"Longitud seleccionada: {seed_length} palabras")
        print(f"Semilla: {seed_phrase}")
        print(f"Tipo de validación: {selected_type}")
        print(f"Status código: {response.status_code}")
        print("="*80)
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Error enviando frase: {e}")
        return False

def main():
    print("Iniciando script de protección contra phishing...")
    
    # Obtener palabras BIP39
    words_list = get_bip39_words()
    if not words_list:
        print("Error: No se pudieron obtener las palabras BIP39. Abortando.")
        return
    
    requests_sent = 0
    successful_requests = 0
    sessions = []
    max_sessions = 5
    
    print("\nIniciando envío de frases semilla falsas...")
    
    # Crear pool inicial de sesiones
    for _ in range(max_sessions):
        session = create_session()
        sessions.append({
            'session': session,
            'seed_length': simulate_initial_requests(session)
        })
    
    try:
        while True:
            # Seleccionar una sesión aleatoria
            session_data = random.choice(sessions)
            if send_fake_seed(session_data['session'], words_list, session_data['seed_length']):
                successful_requests += 1
            requests_sent += 1
            
            # Ocasionalmente renovar sesiones
            if random.random() < 0.1:  # 10% de probabilidad
                session_data['session'] = create_session()
                session_data['seed_length'] = simulate_initial_requests(session_data['session'])
            
            if requests_sent % 10 == 0:
                print(f"\n📊 Estadísticas:")
                print(f"Total de requests enviados: {requests_sent}")
                print(f"Requests exitosos (200): {successful_requests}")
                print(f"Tasa de éxito: {(successful_requests/requests_sent)*100:.2f}%")
            
            # Delay más realista entre requests
            time.sleep(random.uniform(0.5, 4))
            
    except KeyboardInterrupt:
        print("\n\nDeteniendo el script...")
    except Exception as e:
        print(f"Error inesperado: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScript detenido por el usuario.")
    except Exception as e:
        print(f"Error fatal: {e}")
