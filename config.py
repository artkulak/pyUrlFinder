class Config:
    '''
    Contains important constants for the script
    '''

    def __init__(self):

        # bash commands
        self.FINDOMAIN = lambda link, output: f'findomain -t {link} -u {output}' # can add " | httprobe" here
        self.AMASS = lambda link, output: f'amass enum -d {link} -o {output}' # can add " | httprobe" here TODO: Add -brute param and understand it
        self.LiveTargetsFinder = lambda link: f'sudo python3 tools/LiveTargetsFinder/liveTargetsFinder.py --target-list {link}'
        self.ALTDNS = lambda input_path, output_path, wordlist_path: f'altdns -i {input_path} -o {output_path} -w {wordlist_path}'
        self.AQUATONE = lambda file_path, output_path: f'cat {file_path} | aquatone -ports 443 -out {output_path}' # --chrome-path ~/chrome-linux/chrome '

        # telegram api data
        self.TELEGRAM_CHAT_ID = 'TOKEN_CHAT_ID'
        self.TELEGRAM_TOKEN = 'TELEGRAM_TOKEN'
