import json
import logging
import os
from datetime import datetime as dt

import numpy as np
import openai
import pandas as pd
from openai.embeddings_utils import get_embedding
from utils import sanitise_columns, scrape_websites

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)


# Constants and env vars
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
SHOULD_REFRESH = bool(os.environ.get(
    'SHOULD_REFRESH', 'False').lower() in ('true'))
EMBEDDING_MODEL = 'text-embedding-ada-002'
TOKEN_ENCODING = 'cl100k_base'

# Setup OpenAI
logging.info("Setting up OpenAI")
openai.api_key = os.environ.get('OPENAI_API_KEY')


def generate_embeddings():
    if SHOULD_REFRESH:
        logging.info('Refresh set...')

        # Read in CSV
        logging.info("Reading in raw data...")
        df = pd.read_csv('./../data/cleaned_articles.csv')
        df = df.ffill()

        # Sanitise
        logging.info("Sanitising Columns")
        df.columns = sanitise_columns(df.columns)
        logging.info("Summary of data")
        logging.info(df.info())

        # Scrape and calculate tokens
        logging.info(f"Begin scraping of {len(df)} sites")
        df = scrape_websites(df)

        scrape_date = str(dt.utcnow()).split('.')[0].replace(' ', 'T')
        df.to_csv(f'./../data/scraped_{scrape_date}.csv', index=False)

        logging.info("Generate embeddings")
        for i, row in df.iterrows():
            text = row.section_content
            token_count = row.token_count
            if token_count <= 8191:
                df.at[i, 'embedding'] = json.dumps(
                    get_embedding(text, engine=EMBEDDING_MODEL))
                logging.info(f"Embedded {row.source} ({i})")
            else:
                logging.info(
                    f"Did not generate embeddings for heading {row['section_title']} from {row['source']}({row['website_link']}")
                df.at[i, 'embedding'] = np.nan

        df = df.dropna()

        # Save to CSV
        embeddings_date = str(dt.utcnow()).split('.')[0].replace(' ', 'T')
        file_name = f"chatbot_embeddings_{embeddings_date}.csv"
        df.to_csv(f'./../data/{file_name}', index=False)
    else:
        logging.info('No refresh needed. Using old tokens')
        df = pd.read_csv('./../data/chatbot_embeddings.csv')
        logging.info(df.info())


if __name__ == "__main__":
    generate_embeddings()
