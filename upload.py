import os
import logging
import pandas as pd
from sqlalchemy import create_engine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

conn_string = os.environ.get('PSQL_CONN_STRING')

db = create_engine(conn_string)
conn = db.connect()

logging.info("Loading Data")
df = pd.read_csv('./../data/chatbot_embeddings.csv')
logging.info("Summary of data")
logging.info(df.info())

scraped_sources = df[['source', 'topic', 'website_link']].drop_duplicates().rename(columns={'website_link': 'url'})
scraped_sources = scraped_sources.reset_index(drop=True)
logging.info("Scraped Sources")
logging.info(scraped_sources.info())

scraped_source_sections = df[['website_link', 'section_title', 'section_content', 'token_count', 'embedding']].rename(columns={'website_link': 'url', 'section_title': 'heading', 'section_content': 'content'})
scraped_source_sections['scraped_source_id'] = scraped_source_sections['url'].apply(lambda x: scraped_sources.index[scraped_sources['url'] == x][0])
scraped_source_sections = scraped_source_sections.drop(columns=['url'])
logging.info("Scraped Source Sections")
logging.info(scraped_source_sections.head())

logging.info("Uploading to scraped_source table")
scraped_sources.to_sql('scraped_source', con=conn, if_exists='append', index=False)
logging.info("Uploading to scraped_source_section table")
scraped_source_sections.to_sql('scraped_source_section', con=conn, if_exists='append', index=False)