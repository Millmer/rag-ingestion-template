import html
import logging
import re
from typing import List

import pandas as pd
import requests
import tiktoken
from bs4 import BeautifulSoup


def sanitise(string: str) -> str:
    """Ensure a string is an acceptable table column header"""
    replacement_ops = [
        (" - ", "_"),
        ("- ", "_"),
        (" -", "_"),
        ("-", "_"),
        (" ", "_"),
        (".", "_"),
        ("/", "_")
    ]
    invalid_regex = '[^A-Za-z0-9_]+'
    string = string.strip()
    for val, replace in replacement_ops:
        string = string.replace(val, replace)
    string = re.sub(invalid_regex, '', string)
    return string.lower()[:128]


def sanitise_columns(columns: List[str]) -> List[str]:
    """Return a sanitised list of acceptable table column headers"""
    return [sanitise(column) for column in columns]


def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    """Returns the number of tokens in a text string."""
    enconding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(enconding.encode(string))
    return num_tokens


def strip_text(text: str) -> str:
    text = html.unescape(text)
    # When BS can't decode something it is replaced with REPLACEMENT CHARACTER. Let's remove that
    text = text.replace('REPLACEMENT CHARACTER', '')
    # OpenAI recommends replacing newlines with spaces
    text = re.sub(r'\n+|\t+|\r+', ' ', text).replace('\xa0', ' ').strip()

    return text


def get_sections(soup: BeautifulSoup) -> List[str]:
    sections = []
    current_section = {'title': None, 'content': []}

    def is_heading(elem):
        headings = ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')
        if elem.name in headings:
            return True
        return False

    def process_tree(elem):
        nonlocal current_section
        if is_heading(elem):
            if current_section['content']:
                sections.append(current_section)
                current_section = {'title': None, 'content': []}
            current_section['title'] = strip_text(
                elem.get_text(" ", strip=True))
        elif elem.name in ('p', 'ul', 'ol', 'td', 'tr', 'aside', 'figcaption', 'pre', 'blockquote'):
            current_section['content'].append(
                strip_text(elem.get_text(" ", strip=True)))

        for child in elem.children:
            if not isinstance(child, str):
                process_tree(child)

    process_tree(soup)

    if current_section['content']:
        sections.append(current_section)

    return sections


def scrape_websites(df: pd.DataFrame) -> pd.DataFrame:
    scraped_data = []

    for _, row in df.iterrows():
        source = row['source']
        topic = row['topic']
        website_link = row['website_link']
        logging.info(f"Scraping {source}...")

        response = requests.get(website_link, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')

        main_element = soup.find('main')

        if main_element:
            soup = main_element

        # Remove elements we don't care about
        culled_elems = ['nav', 'header', 'footer', 'form', 'svg', 'img', 'iframe', 'script', 'input']
        [s.decompose() for s in soup(['nav', 'header', 'footer',
                                      'form', 'svg', 'img', 'iframe', 'script'])]

        # Remove stuff hidden to screen readers
        [tag.decompose() for tag in soup.find_all(lambda tag: tag.has_attr(
            'aria-hidden') and tag['aria-hidden'] == 'true')]
        [tag.decompose() for tag in soup.select('.sr-only')]

        # Specific things
        [tag.decompose() for tag in soup.find_all(class_=lambda cls: cls in ['tp-on-this-page', 'email_capture', 'table-contents', 'risk-factor-banner', 'webform', 'language-switcher-locale-url',
                                                                             'js-toc', 'column-layout__secondary', 'text-banner__share', 'document-list', 'next-section-link cf', 'side-section',
                                                                             'dk-breadcrumbs', 'dv-action-tile', 'content-grid', 'dv-deeper-look-tile', 'dv-content-tile']
                                                  )]
        [tag.decompose() for tag in soup.find_all(id="read-next")]

        # Try to remove any cookie banners
        cookie_pattern = re.compile(r'cookie')
        [banner.decompose() for banner in soup.find_all(
            'div', {'class': cookie_pattern})]

        sections = get_sections(soup)

        if not sections:
            # Fallback to the whole content if there are no meaningful sections
            sections = [
                {'title': None, 'content': [strip_text(soup.get_text())]}]

        for section in sections:
            section_title = section['title']
            section_content = ' '.join(section['content'])

            if section_content:
                scraped_data.append({
                    'source': source,
                    'topic': topic,
                    'website_link': website_link,
                    'section_title': section_title,
                    'section_content': section_content,
                    'token_count': num_tokens_from_string(section_content)
                })

    results_df = pd.DataFrame(scraped_data)

    # Drop any content with no headers or content (mostly nonsense - lose minor amount of good data doing this)
    results_df = results_df.dropna()

    # Remove rows where "Section Title" equals "Section Content" (where a heading is immediately followed by a subheading)
    results_df = results_df[results_df['section_title']
                            != results_df['section_content']]

    return results_df
