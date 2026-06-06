from langchain_community.document_loaders import AsyncChromiumLoader
from langchain_community.document_transformers import Html2TextTransformer
from langchain_core.documents import Document
import os
import pandas as pd
from serpapi import GoogleSearch
from typing import List
import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor

class ChromiumLoader(AsyncChromiumLoader):
    async def load(self):
        raw_text = [await self.ascrape_playwright(url) for url in self.urls]
        # Return the raw documents:
        return [Document(page_content=text) for text in raw_text]


async def get_html_content_from_urls(
    df: pd.DataFrame, number_of_urls: int = 3, url_column: str = "link"
) -> List[Document]:
    # Get the HTML content of the first 3 URLs:
    urls = df[url_column].head(number_of_urls).tolist()

    # loader = AsyncHtmlLoader(urls) 
    loader = ChromiumLoader(urls)

    # --- WINDOWS JUPYTER PLAYWRIGHT FIX ---
    if sys.platform == "win32":
        def _run_playwright_in_thread():
            # 1. Force the Proactor policy for this new thread
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            # 2. Create a brand new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # 3. Run the loader in this new, compatible loop
                return loop.run_until_complete(loader.load())
            finally:
                loop.close()

        # 4. Run the thread function using Jupyter's main loop executor
        with ThreadPoolExecutor(max_workers=1) as pool:
            docs = await asyncio.get_event_loop().run_in_executor(pool, _run_playwright_in_thread)
    else:
        # For Mac/Linux, the default loop already supports subprocesses
        docs = await loader.load()
    # --------------------------------------

    return docs


def extract_text_from_webpages(documents: List[Document]):
    html2text = Html2TextTransformer()
    return html2text.transform_documents(documents)


async def collect_serp_data_and_extract_text_from_webpages(
    topic: str,
) -> List[Document]:
    search = GoogleSearch(
        {
            "q": topic,
            "location": "Austin,Texas",
            "api_key": os.environ["SERPAPI_API_KEY"],
        }
    )
    # Get the results:
    result = search.get_dict()

    # 1. Check for API errors first
    if "error" in result:
        raise ValueError(f"Search API returned an error: {result['error']}")
    
    # 2. Check if organic_results exists and is not empty
    if "organic_results" not in result or not result["organic_results"]:
        print(f"Warning: No organic results found for topic: '{topic}'")
        print(f"Full API Response: {result}") # This will help you debug the exact issue
        serp_results = pd.DataFrame() # Create an empty DataFrame
    else:
        # Put the results in a Pandas DataFrame:
        serp_results = pd.DataFrame(result["organic_results"])

    # Extract the html content from the URLs:
    html_documents = await get_html_content_from_urls(serp_results)

    # Extract the text from the URLs:
    text_documents = extract_text_from_webpages(html_documents)

    return text_documents
