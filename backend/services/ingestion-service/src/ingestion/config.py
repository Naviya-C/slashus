"""
ingetion/config.py
===================

PURPOSE
-------
This is for handle .env file values by safely importing to here.
This contains:
    - DEFAULT_TEXT_THRESHOLD
    - DEFAULT_COVERAGE_THRESHOLD
"""

from dotenv import load_dotenv
import os

load_dotenv()

globalConfig = {}

def load_env():  
    globalConfig["DEFAULT_TEXT_THRESHOLD"] = int(os.getenv("DEFAULT_TEXT_THRESHOLD"))
    globalConfig["DEFAULT_COVERAGE_THRESHOLD"] = float(os.getenv("DEFAULT_COVERAGE_THRESHOLD"))
    
    return globalConfig
