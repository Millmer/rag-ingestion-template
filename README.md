# rag-ingestion-template

Rough and ready pipeline to scrape, chunk and embed data for RAG.

Extremley bare bones but does the job.

Several improvments are:
- Clean up the code making it more configurable
- Generalise further the scraping code, adding in optional individual scrape scripts depending on the source for added customisation (helpful for those sites with specific scraping requirements).
- Deploy to the cloud and attach to a cron for automated refresh
- Add checksum column to see if content has changed before re-generating embeddings
- Allow source files to be easliy updated and changed, maybe even allowing for individual source re-scrape
- Improve the upload script to avoid loss of or overlap with existing data

# Ingestion
Make sure you export the relevant env vars and adjust the filename timestamps for the files you wish to process:
```sh
OPENAI_API_KEY=
SHOULD_REFRESH=True or False
PSQL_CONN_STRING=
```

Assumes a Postgres instance already running with `scraped_source` and `scraped_source_section` tables.

Assumes "cleaned_articles.csv" has the structure:

| Source | Topic | Subtopic | Website link |
| ------ | ----- | -------- | ------------ |


## Python Setup
1. Create a python env with `python -m venv rag`
2. Activate the env in your shell `. ./rag/bin/activate/`
3. Check you're using the right python `which python` (should print out the path of the new genrated python env)
4. Install the packages `pip install -r requirements.txt`
5. You're good to go!

### Use
1. Install the `requirements.txt`
2. Have the `OS_HOST`, `OS_PORT`, `OS_USER`, `OS_PASS` and `PSQL_CONN_STRING` env vars exported
3. (Optional) Uncomment final lines to upload to indexes
5. Run `python generate_embeddings.py` to generate embeddings
6. Optionally run `python upload.py` to upload to Postgres