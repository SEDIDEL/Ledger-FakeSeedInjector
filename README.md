# FakeSeedInjector README

## Introduction

Ledger-FakeSeedInjector is a Python script designed to inject fake seed phrases into phishing websites to prevent attackers from obtaining valid seed phrases. This tool helps protect against phishing attacks by flooding malicious endpoints with sh*t.

## Features

- Generates random PHPSESSID tokens.
- Retrieves realistic User-Agent strings.
- Downloads the BIP39 word list to generate seed phrases.
- Simulates user interactions with phishing sites.
- Sends fake seed phrases to disrupt phishing attempts.

## Targets File

The script uses a file named `targets.txt` to store the URLs of phishing websites it interacts with. By default, the script is configured to work with the following URL:

```
https://ledgerrecovery.info
```

### How to Use
1. Open the `targets.txt` file.
2. Add or modify the URLs of the phishing websites you want the script to target. Each URL should be on a new line.
3. Save the file and run the script.

### Example `targets.txt`:
```
https://ledgerrecovery.info
https://phishingsiteexample.com
https://anothermalicioussite.org
```

### Notes
- Ensure the URLs are correct and active.
- Use this script responsibly and only on websites you have permission to test.

## Dependencies

- Python 3.x
- requests
- random
- string
- time
- concurrent.futures

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/SEDIDEL/Ledger-FakeSeedInjector.git
   ```
2. Navigate to the directory:
   ```
   cd Ledger-FakeSeedInjector
   ```
3. Ensure all dependencies are installed:
   ```
   pip install requests
   ```

## Usage

Run the script using Python:
```
python FakeSeedInjector.py
```

## Technical Details

The script creates multiple sessions, each simulating a user visiting the phishing site. It generates random seed phrases from the BIP39 word list and sends them to the endpoint with randomized headers and delays, mimicking human behavior.

## Warning

This script is for educational and ethical testing purposes only. Do not use it on any website without explicit permission. The author is not responsible for any misuse of this tool.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

MIT License
