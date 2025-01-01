import requests
import random
import string
import time
from concurrent.futures import ThreadPoolExecutor

def generate_phpsessid():
    """Generates a random valid PHPSESSID."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=26))

def get_random_user_agent():
    """Returns a random realistic User-Agent."""
    browsers = [
        # Safari on macOS
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15',
        # Chrome on Windows
        f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(100,120)}.0.{random.randint(4000,5000)}.{random.randint(100,999)} Safari/537.36',
        # Firefox on Windows
        f'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{random.randint(100,120)}.0) Gecko/20100101 Firefox/{random.randint(100,120)}.0',
        # Chrome on macOS
        f'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randint(13,15)}_{random.randint(1,7)}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(100,120)}.0.{random.randint(4000,5000)}.{random.randint(100,999)} Safari/537.36',
        # Edge on Windows
        f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(100,120)}.0.{random.randint(4000,5000)}.{random.randint(100,999)} Edge/{random.randint(100,120)}.0.{random.randint(1000,2000)}.{random.randint(100,999)}',
    ]
    return random.choice(browsers)

def get_bip39_words():
    """Downloads the BIP39 word list from the Bitcoin repository."""
    url = "https://raw.githubusercontent.com/bitcoin/bips/master/bip-0039/english.txt"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            words = [word.strip() for word in response.text.split('\n') if word.strip()]
            print(f"✓ Downloaded {len(words)} BIP39 words")
            return words
        else:
            raise Exception(f"Error downloading words: Status code {response.status_code}")
    except Exception as e:
        print(f"Error fetching BIP39 words: {e}")
        return []

def generate_seed_phrase(words, length=24):
    """Generates a random seed phrase of the specified length."""
    return [random.choice(words) for _ in range(length)]

def format_data(words):
    """Formats the words in the format expected by the API."""
    return {str(i+1): word for i, word in enumerate(words)}

def create_session():
    """Creates a new session with consistent cookies and headers."""
    session = requests.Session()
    session.cookies.set('PHPSESSID', generate_phpsessid(), domain='ledgerrecovery.info')
    return session

def simulate_initial_requests(session):
    """Simulates the initial requests a real user would make."""
    try:
        # Simulate initial visit
        session.post('https://ledgerrecovery.info/asset/modal/api.php', 
                    json={'type': 10},  # type 10 = initial visit
                    timeout=10)
        time.sleep(random.uniform(2, 4))
        
        # Simulate seed phrase length selection
        length_type = random.choice([12, 18, 24])
        session.post('https://ledgerrecovery.info/asset/modal/api.php',
                    json={'type': length_type},  # type corresponds to the selected length
                    timeout=10)
        
        return length_type
    except Exception:
        return random.choice([12, 18, 24])

def send_fake_seed(session, words_list, seed_length=24):
    """Sends a fake seed phrase to the endpoint."""
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
    
    # Validation types with their probabilities
    validation_types = [
        (1, 0.2),   # Partial submission
        (2, 0.2),   # Full validation
        (3, 0.3),   # Successful submission
        (5, 0.15),  # Failed validation
        (6, 0.15)   # Alternative partial submission
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
        # Create a readable representation of the seed phrase
        seed_phrase = ' '.join(payload['data'].values())
        
        response = session.post(
            'https://ledgerrecovery.info/asset/modal/api.php',
            json=payload,
            headers=headers,
            timeout=10
        )
        
        print("\n" + "="*80)
        print(f"✓ Sent seed phrase:")
        print(f"Selected length: {seed_length} words")
        print(f"Seed: {seed_phrase}")
        print(f"Validation type: {selected_type}")
        print(f"Status code: {response.status_code}")
        print("="*80)
        return True
    except Exception as e:
        print(f"✗ Error sending seed: {e}")
        return False

def main():
    print("Starting phishing protection script...")
    
    # Get BIP39 words
    words_list = get_bip39_words()
    if not words_list:
        print("Error: Could not fetch BIP39 words. Aborting.")
        return
    
    requests_sent = 0
    sessions = []
    max_sessions = 5
    
    print("\nStarting fake seed phrase submissions...")
    
    # Create initial session pool
    for _ in range(max_sessions):
        session = create_session()
        sessions.append({
            'session': session,
            'seed_length': simulate_initial_requests(session)
        })
    
    try:
        while True:
            # Select a random session
            session_data = random.choice(sessions)
            send_fake_seed(session_data['session'], words_list, session_data['seed_length'])
            requests_sent += 1
            
            # Occasionally renew sessions
            if random.random() < 0.1:  # 10% probability
                session_data['session'] = create_session()
                session_data['seed_length'] = simulate_initial_requests(session_data['session'])
            
            if requests_sent % 50 == 0:
                print(f"\n📊 Statistics:\nRequests sent: {requests_sent}")
            
            # More realistic delay between requests
            time.sleep(random.uniform(0.5, 4))
            
    except KeyboardInterrupt:
        print("\n\nStopping script...")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScript stopped by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
