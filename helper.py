from config import Config

import subprocess
import os

class Helper:
    '''
    Contains helper functions for the pipeline
    '''

    def __init__(self):
        self.cfg = Config()


    def read_link_file(self, path):
        '''
        Reads file with the links and returns as array
        '''

        with open(path, 'r') as f:
            links = f.read().split('\n')
        return links
    
    def get_domains(self, link, directory):
        '''
        For a given link finds all subdomains
        '''

        # find domains with amass and findomain and save them to output
        findomainOut = os.path.join(directory, 'findomain.txt')
        amassOut = os.path.join(directory, 'amass.txt')
        subprocess.check_output(self.cfg.FINDOMAIN(link, findomainOut), shell = True).decode().split('\n')
        subprocess.check_output(self.cfg.AMASS(link, amassOut), shell = True).decode().split('\n')
        
        # read the output files and choose only unique links from them
        with open(findomainOut, 'r') as f:
            findomainLinks = f.read().split('\n')
        
        with open(amassOut, 'r') as f:
            amassLinks = f.read().split('\n')

        try:
            subprocess.check_output(f'rm {findomainOut} {amassOut}', shell = True)
        except:
            pass
            
        links = set(findomainLinks + amassLinks)
        
        return links
