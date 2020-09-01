'''
Given a domain example.com

# Subdomain discovery
1. Find all subdomains of example using findomain + amass. (+)
2. Use altdns to find more possible subdomains (+)
3. Use LiveTargetScanner/ httprobe to resolve domains
4. Do aquatone over all resolved domains
5. Do notification via telegram bot when new domains were found

'''

import argparse
import os
from subprocess import Popen as bash
import subprocess
from tqdm import tqdm
import pandas as pd
import datetime
import hashlib
import requests
import time

from config import Config
from helper import Helper

class Pipeline:

    def __init__(self, domain, prev_snap, permutations_wordlist):
        self.domain = self.folder = domain
        self.prev_snap = self.timestamp = prev_snap
        self.permutations_wordlist = permutations_wordlist
       
        self.cfg = Config()
        self.helper = Helper()

        if self.prev_snap is None:
            self.runFolder = None
        else:
            self.runFolder = f'{os.path.join(self.folder, self.prev_snap)}' 


        # try making root folder for the website
        try:
            os.mkdir(f'{self.folder}')
        except:
            pass


    def init_timestamp(self):
        '''
        Creates the directory for this run and also records the timestamp for further comparison
        '''

        print(f'----> Creating new snapshot ... \n')
        # encode current time with md5
        self.curTime = str(datetime.datetime.now())
        self.timestamp = hashlib.md5(self.curTime.encode("utf8")).hexdigest()[:10]

        # create cur time snapshot folder with md5 encoded name
        self.runFolder = f'{os.path.join(self.folder, self.timestamp)}' 
        try:
            os.mkdir(self.runFolder)
        except:
            pass


        snapshots_path = os.path.join(self.folder, 'snapshots.csv')
        if os.path.exists(snapshots_path):
            with open(snapshots_path, 'a') as f:
                f.write(','.join([self.timestamp, self.curTime])+'\n')
        else:
            snapshots = pd.DataFrame([[self.timestamp, self.curTime]])
            snapshots.columns = ['Hash', 'Time']
            snapshots.to_csv(snapshots_path, index = None)


    def find_domains(self):
        '''
        Find all subdomains;
        Currently use findomain, amass
        '''

        print(f'----> Finding domains ... \n')

        # find domains with findomain and amass
        allLinks = self.helper.get_domains(self.domain, self.runFolder)

        # store the domains as file
        domains = '\n'.join(allLinks)
        with open(os.path.join(self.runFolder, f'domains_{self.domain}.txt'), 'w') as f:
            f.write(domains)


    def generate_domain_permutations(self):
        '''
        Given permutation wordlist and domains list generate all possible permutations
        '''

        print(f'----> Generating domain permutations ... \n')

        input_path = os.path.join(self.runFolder, f'domains_{self.domain}.txt')
        output_path = os.path.join(self.runFolder, 'permuted_domains.txt')
        wordlist_path = self.permutations_wordlist
        cmd = self.cfg.ALTDNS(input_path, output_path, wordlist_path)

        subprocess.check_output(cmd, shell = True)

        # stack all list of domains together
        with open(output_path, 'r') as f:
            permuted_domains = f.read().split('\n')
    
        # store all domains at the same file
        domains = '\n'.join(permuted_domains) + '\n'
        with open(os.path.join(self.runFolder, f'domains_{self.domain}.txt'), 'a') as f:
            f.write(domains)
        
        
    def scan_targets(self):
        '''
        Resolve all the working hosts with LiveTargetsFinder
        '''

        print('----> Resolving target hosts with LiveTargetFinder \n')

        try:
            os.mkdir('output')
        except:
            pass
        
        # check working domains with LiveTargetsFinder
        cmd = self.cfg.LiveTargetsFinder(os.path.join(self.runFolder, f'domains_{self.domain}.txt'))
        subprocess.check_output(cmd, shell = True)

        # move all working urls to snapshot folder
        cmd = f'''sudo mv output/domains_{self.domain}_targetUrls.txt {os.path.join(self.runFolder, 'urls.txt')}'''
        subprocess.check_output(cmd, shell = True)

        # move all resolving domains to snapshot folder
        cmd = f'''sudo mv output/domains_{self.domain}_domains_alive.txt {os.path.join(self.runFolder, 'domains.txt')}'''
        subprocess.check_output(cmd, shell = True)

        # remove output folder
        cmd = f'sudo rm -r output/'
        subprocess.check_output(cmd, shell = True)

        # remove another output
        cmd = f'sudo rm output.csv'
        # subprocess.check_output(cmd, shell = True)

        # remove full list of domains
        cmd = f'''sudo rm -r {os.path.join(self.runFolder, f'domains_{self.domain}.txt')}'''
        subprocess.check_output(cmd, shell = True)

        # remove permuted domains
        cmd = f'''sudo rm -r {os.path.join(self.runFolder, f'permuted_domains.txt')}'''
        # subprocess.check_output(cmd, shell = True)

    def do_screenshots(self):
        '''
        Screenshot all domains and save to folder
        '''
        print(f'----> Screenshotting all subdomains ... \n')

        # screenshot all domains from domains.txt file
        file_path = os.path.join(self.runFolder, 'domains.txt')
        cmd = self.cfg.AQUATONE(file_path, self.runFolder)
        subprocess.check_output(cmd, shell = True)

        # deleted some aquatone stuff
        cmd = f'''sudo rm -r {os.path.join(self.runFolder, f'aquatone* headers/ html/')}'''
        # subprocess.check_output(cmd, shell = True)

    def find_new_domains(self):
        '''
        Checks 2 lists of latest scanned domains to find differences
        '''

        print('----> Checking for differences in snapshots ... \n')
        # get 2 latest snapshots (one is the current)
        snapshots = pd.read_csv(os.path.join(self.folder, 'snapshots.csv'))
        folders = snapshots['Hash'].tail(2).values
        if len(folders) < 2:
            return None
        folder_old, folder_new = folders[0], folders[1]

        old_domains = self.helper.read_link_file(os.path.join(self.folder, folder_old, 'urls.txt'))
        new_domains = self.helper.read_link_file(os.path.join(self.folder, folder_new, 'urls.txt'))

        # find added and deleted domains 
        deleted = []
        for d in old_domains:
            if d not in new_domains:
                deleted.append(d)
        
        added = []
        for d in new_domains:
            if d not in old_domains:
                added.append(d)

        
        # store added and deleted domains as files

        if len(deleted) > 0:
            deletedStr = '\n'.join(deleted)
            with open(os.path.join(self.runFolder, f'deleted_domains.txt'), 'w') as f:
                f.write(deletedStr)

        if len(added) > 0:
            addedStr = '\n'.join(added)
            with open(os.path.join(self.runFolder, f'added_domains.txt'), 'w') as f:
                f.write(addedStr)
        
        # notify about ned domains found
        self.notify(deleted, added)

    def notify(self, deleted, added):
        '''
        Notifies about detected differences via telegram bot
        '''

        # if number of deleted entries or added entries more than 0, send a message via telegram 
        deletedCounts, addedCounts = len(deleted), len(added)


        if addedCounts > 0:
            text = f'Snapshot {self.timestamp} for {self.domain}\nAdded domains: {addedCounts}'
            
            payload = {
                'chat_id': self.cfg.TELEGRAM_CHAT_ID,
                'caption': text,
            }

            added = open(os.path.join(self.runFolder, f'added_domains.txt'), 'r').read()

            fpayload = {
                'document': ('added.txt', added),
            }

            sendfile = requests.post("https://api.telegram.org/bot{token}/sendDocument".format(token=self.cfg.TELEGRAM_TOKEN),
                files = fpayload, data=payload)

        if deletedCounts > 0:
            text = f'Snapshot {self.timestamp} for {self.domain}\nDeleted domains: {deletedCounts}'
            
            payload = {
                'chat_id': self.cfg.TELEGRAM_CHAT_ID,
                'caption': text,
            }

            added = open(os.path.join(self.runFolder, f'deleted_domains.txt'), 'r').read()

            fpayload = {
                'document': ('deleted.txt', added),
            }

            sendfile = requests.post("https://api.telegram.org/bot{token}/sendDocument".format(token=self.cfg.TELEGRAM_TOKEN),
                files = fpayload, data=payload)



    def run(self):
        '''
        Runs all the recon pipeline
        '''
        # init faze
        if self.prev_snap is None:
            self.init_timestamp()

        # subdomain enumeration
        self.find_domains()
        # self.generate_domain_permutations()

        # resolve subdomains
        self.scan_targets()

        # screenshot
        # self.do_screenshots()

        # check for new subdomains and notify
        self.find_new_domains()

if __name__ == '__main__':

    # parse input arguments from console
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-u', type=str, nargs='?') # website url
    parser.add_argument('-pw', type=str, nargs='?') # permutations wordlist
    parser.add_argument('-psnap', type=str, nargs = '?') # id of snapshot to run
    parser.add_argument('-pause', type=float, nargs='?') # pause time in hours before next run
    
    args = parser.parse_args()
    
    url = args.u if args.u is not None else 'example.com'
    prev_snap = args.psnap if args.psnap is not None else None
    permutations_wordlist = args.pw if args.pw is not None else None
    pause = args.pause if args.pause is not None else 0

    pauseSeconds = pause * 3600

    # create and run the recon pipeline
    pipe = Pipeline(url, prev_snap, permutations_wordlist)
    while True:
        pipe.run()

        # delay between runs
        time.sleep(pauseSeconds)

