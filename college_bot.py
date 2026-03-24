import os
import re
import json
import logging
import hashlib
import requests

from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urljoin, urlsplit
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import AsyncHtmlLoader, PyPDFDirectoryLoader
from langchain_community.document_transformers import Html2TextTransformer
from langchain_mistralai import ChatMistralAI
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.prompts import MessagesPlaceholder

# Configure logging
logging.basicConfig(
    filename="college_bot.log",  
    level=logging.DEBUG,  
    format="%(asctime)s - %(levelname)s - %(message)s"  
)

os.environ["USER_AGENT"] = "college-chatbot/1.0"
class College:

    def add_pdf_to_knowledge_base(self, pdf_url):
        """
        Extracts content from a PDF URL and adds it to knowledge_base.json as {url: content}.
        """
        print(f"Extracting and adding PDF to knowledge base: {pdf_url}")
        pdf_content_map = self.extract_pdf_data([pdf_url])
        if not pdf_content_map:
            print("No content extracted or PDF could not be processed.")
            return
        # Load existing knowledge base
        try:
            with open(self.knowledge_file, "r", encoding="utf-8") as f:
                kb = json.load(f)
        except Exception:
            kb = {}
        # Add/overwrite PDF mapping
        for url, content in pdf_content_map.items():
            kb[url] = self._sanitize_text(content)
            print(f"Added mapping: {url} : (content length {len(content)})")
        # Save back
        with open(self.knowledge_file, "w", encoding="utf-8") as f:
            json.dump(kb, f, ensure_ascii=False, indent=4)
        print("knowledge_base.json updated with PDF content.")

        def test_pdf_url_mapping(self, pdf_url):
            """
            Fetches, extracts, and prints the mapping for a single PDF URL.
            Usage: College().test_pdf_url_mapping("https://gacsalem7.ac.in/wp-content/uploads/2021/10/Computer-Science-R.Pugazendi.pdf")
            """
            print(f"Testing PDF extraction for: {pdf_url}")
            pdf_content_map = self.extract_pdf_data([pdf_url])
            for url, content in pdf_content_map.items():
                print(f"URL: {url}\n---\nContent (first 500 chars):\n{content[:500]}\n...")
            if not pdf_content_map:
                print("No content extracted or PDF could not be processed.")
    def __init__(self):
        logging.info("Initializing College class...")  
        self.http_timeout = int(os.getenv("HTTP_TIMEOUT_SECONDS", "20"))
        self.http_session = self._build_http_session()

        api_key = os.getenv("MISTRAL_API_KEY", "DhcEZgZeWxa3faXsxiCpETM8d66wqJQw")
        llm_config = dict(
            model="mistral-large-latest",
            temperature=0,
            max_retries=2,
        )
        if api_key:
            llm_config["api_key"] = api_key
        self.llm = ChatMistralAI(
            **llm_config
        )

        self.sitemap_url_post_page = 'https://gacsalem7.ac.in/wp-sitemap-posts-page-1.xml'
        self.sitemap_url_our_team = 'https://gacsalem7.ac.in/wp-sitemap-posts-our_team-1.xml'
        
        # Define the local file path for storing data
        self.knowledge_file = "knowledge_base.json"

        # Load from local JSON if it exists, otherwise scrape and save
        if os.path.exists(self.knowledge_file):
            logging.info("Local knowledge base found. Loading from JSON...")
            with open(self.knowledge_file, "r", encoding="utf-8") as f:
                self.knowledge = json.load(f)
        else:
            logging.info("Local knowledge base not found. Scraping website...")
            self.knowledge = self.map_url_and_content()
            self.save_knowledge()

        # Initialize Chat History for conversations
        self.chat_history = ChatMessageHistory()

    def _normalize_url(self, url, base_url="https://gacsalem7.ac.in"):
        if not url:
            return ""
        return urljoin(base_url, url.strip())

    def _is_pdf_url(self, url):
        if not url:
            return False
        try:
            path = urlsplit(url).path.lower()
            return path.endswith('.pdf')
        except Exception:
            return False

    def _build_http_session(self):
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _sanitize_text(self, text):
        # Remove control characters except for common whitespace (tab, newline, carriage return)
        if not isinstance(text, str):
            return text
        return ''.join(ch for ch in text if ch == '\t' or ch == '\n' or ch == '\r' or 32 <= ord(ch) <= 126 or 160 <= ord(ch))

    def save_knowledge(self):
        """Saves the scraped dictionary to a local JSON file, sanitizing content."""
        logging.info("Saving extracted knowledge to local JSON file...")
        try:
            sanitized_knowledge = {k: self._sanitize_text(v) for k, v in self.knowledge.items()}
            with open(self.knowledge_file, "w", encoding="utf-8") as f:
                json.dump(sanitized_knowledge, f, ensure_ascii=False, indent=4)
            logging.info("Successfully saved to knowledge_base.json")
        except Exception as e:
            logging.error(f"Failed to save knowledge locally: {e}")

    def filter_urls(self, urls):
        logging.info("Filtering URLs...")
        filtered_urls = []
        pdf_urls = []
        for url in urls:
            normalized_url = self._normalize_url(url)
            if self._is_pdf_url(normalized_url):
                pdf_urls.append(normalized_url)
                continue
            if (
                'void(0)' in normalized_url or
                '/blog/' in normalized_url or
                '#' in normalized_url or
                normalized_url.endswith('.png') or
                'po-pso-co' in normalized_url or
                '%' in normalized_url or
                re.search(r'\d{1,2}-\d{1,2}-\d{4}|\d{4}-\d{4}', normalized_url)
            ):
                continue
            filtered_urls.append(normalized_url)

        logging.debug(f"Filtered URLs: {filtered_urls[:5]}... (total: {len(filtered_urls)})")
        return filtered_urls, pdf_urls

    def remove_header(self, input_content):
        try:
            logging.info("Removing header from content...")
            part_to_remove = re.compile(r"\* Home[\s\S]*?\* STUDENTS", re.MULTILINE)
            header_removed_text = re.sub(part_to_remove, "", input_content).strip()
            return header_removed_text
        except Exception as e:
            logging.error(f"Error in remove_header: {e}")

    def remove_footer(self, input_content):
        try:
            logging.info("Removing footer from content...")
            footer_pattern = re.compile(r"__0427-2413273[\s\S]*?Government Arts College \(Autonomous\),Salem-636007\s*__", re.MULTILINE)
            footer_removed_text = re.sub(footer_pattern, "", input_content).strip()
            return footer_removed_text
        except Exception as e:
            logging.error(f"Error in remove_footer: {e}")

    def get_valid_urls(self, sitemap_url):
        try:
            logging.info(f"Fetching URLs from sitemap: {sitemap_url}")
            response = self.http_session.get(sitemap_url, timeout=self.http_timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'xml')
            urls = [loc.get_text() for loc in soup.find_all('loc')]
            logging.debug(f"Fetched {len(urls)} URLs from {sitemap_url}")
            return urls
        except Exception as e:
            logging.error(f"Error fetching URLs from sitemap {sitemap_url}: {e}")
            return []

    def extract_data(self, list_url):
        try:
            logging.info(f"Extracting data from {len(list_url)} URLs...")
            loader = AsyncHtmlLoader(list_url)
            docs = loader.load()
            
            found_pdf_urls = set()
            for doc in docs:
                soup = BeautifulSoup(doc.page_content, 'html.parser')
                for a_tag in soup.find_all('a', href=True):
                    href = self._normalize_url(a_tag['href'])
                    if self._is_pdf_url(href):
                        found_pdf_urls.add(href)
                        
            html2text = Html2TextTransformer()
            docs_transformed = html2text.transform_documents(docs)
            logging.debug(f"Extracted {len(docs_transformed)} documents and {len(found_pdf_urls)} PDF links.")
            return docs_transformed, list(found_pdf_urls)
        except Exception as e:
            logging.error(f"Error in extract_data: {e}")
            return [], []

    def extract_pdf_data(self, pdf_urls):
        logging.info(f"Extracting data from {len(pdf_urls)} PDF URLs...")
        folder = "pdf_folder"
        os.makedirs(folder, exist_ok=True)
        pdf_url_and_content = {}

        for url in pdf_urls:
            parsed_path = urlsplit(url).path
            original_name = os.path.basename(parsed_path) or "document.pdf"
            filepath = os.path.join(folder, original_name)
            try:
                # Only download if it doesn't already exist
                if not os.path.exists(filepath):
                    r = self.http_session.get(url, timeout=self.http_timeout)
                    r.raise_for_status()
                    with open(filepath, "wb") as f:
                        f.write(r.content)
                    logging.info(f"Downloaded: {filepath}")
                # Extract content
                from langchain_community.document_loaders import PyPDFLoader
                loader = PyPDFLoader(filepath)
                docs = loader.load()
                content = "\n".join(doc.page_content for doc in docs)
                pdf_url_and_content[url] = content
            except Exception as e:
                logging.error(f"Error downloading or extracting {url}: {e}")

        return pdf_url_and_content

    def map_url_and_content(self):
        logging.info("Mapping URLs to content...")
        url_and_content = {}
        post_page_url_list = self.get_valid_urls(self.sitemap_url_post_page)
        filtered_post_page_url_list, pdf_urls_sitemap = self.filter_urls(post_page_url_list)

        our_team_url_list = self.get_valid_urls(self.sitemap_url_our_team)

        post_page, pdfs1 = self.extract_data(filtered_post_page_url_list)
        our_team_page, pdfs2 = self.extract_data(our_team_url_list)
        
        all_pdf_urls = list(set(pdf_urls_sitemap + pdfs1 + pdfs2))

        for post_page_context in post_page:
            clean_content = self.remove_footer(self.remove_header(post_page_context.page_content))
            url_and_content[post_page_context.metadata.get("source")] = clean_content

        for our_team_page_context in our_team_page:
            clean_content = self.remove_footer(self.remove_header(our_team_page_context.page_content))
            url_and_content[our_team_page_context.metadata.get("source")] = clean_content

        pdf_content_map = self.extract_pdf_data(all_pdf_urls)
        url_and_content.update(pdf_content_map)

        logging.info(f"Mapped {len(url_and_content)} URLs to content.")
        return url_and_content

    def extract_images_from_urls(self, urls):
        """
        Fetches raw HTML of each URL, extracts <img> tags.
        Returns list of {url, alt} dicts for images with meaningful alt/title.
        """
        found_images = []
        seen = set()
        for page_url in urls:
            try:
                r = self.http_session.get(page_url, timeout=self.http_timeout)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, 'html.parser')
                for img in soup.find_all('img'):
                    src = img.get('src', '') or img.get('data-src', '')
                    alt = (img.get('alt', '') or img.get('title', '')).strip()
                    if not src or not alt:
                        continue
                    if 'gacsalem7.ac.in' not in src:
                        continue
                    # Skip site-wide images (favicon, logo, theme)
                    lower_src = src.lower()
                    if any(skip in lower_src for skip in ['favicon', 'logo', 'cropped-']):
                        continue
                    if src not in seen:
                        seen.add(src)
                        found_images.append({'url': src, 'alt': alt})
            except Exception as e:
                logging.warning(f"Could not extract images from {page_url}: {e}")
        return found_images

    def get_top3_urls(self, question, url_combined, retry=3):
            logging.info(f"Fetching top 3 URLs for question: {question}")
            
            # FIX 1: Convert the massive list of URLs into a single string
            context_string = "\n".join(url_combined)

            prompt = ChatPromptTemplate.from_messages([
                    (
                        "system",
                        '''You are a specialized URL retriever assistant for a college website. Your task is to analyze the user's question and return the top 3 URLs from the provided list that best match the query. The list (provided as {context}) includes URLs for various college resources.

                Your response must be strictly in JSON format as follows:
                {{"urls": ["<URL1>", "<URL2>", "<URL3>"]}}

                - Focus primarily on retrieving URLs related to college staff and administrative personnel.
                - Only include URLs that are highly relevant to the user's query.
                - Do not include any extra text outside the JSON structure.
                - You should return the top 3 URLs that best match the user's query. Dont return one only ur l we need more accurate urls'''
                    ),
                    (
                        "human",
                        "User question: {question}"
                    )
                ])

            chain = prompt | self.llm
            attempts = max(1, int(retry))
            for attempt in range(1, attempts + 1):
                try:
                    result = chain.invoke({"question": question, "context": context_string})
                    print("Raw LLM Response:", result.content)

                    # Extract first JSON object even if model wraps output in extra text.
                    content = result.content.strip().replace("```json", "").replace("```", "")
                    match = re.search(r"\{[\s\S]*\}", content)
                    json_str = match.group(0) if match else content
                    result_json = json.loads(json_str)

                    logging.debug(f"Top 3 URLs: {result_json.get('urls')}")
                    urls = result_json.get("urls", [])
                    valid_urls = [url for url in urls if url in url_combined]
                    if valid_urls:
                        return valid_urls[:3]

                    logging.warning(
                        "Attempt %s/%s returned no valid URLs. Raw output: %s",
                        attempt,
                        attempts,
                        result.content,
                    )
                except Exception as e:
                    logging.warning("Attempt %s/%s failed in get_top3_urls: %s", attempt, attempts, e)

            logging.error("All attempts failed in get_top3_urls for question: %s", question)
            return []

    def reformulate_question(self, question, history_messages=None):
        """Reformulates a follow-up question into a standalone question using chat history."""
        if history_messages is None:
            history_messages = self.chat_history.messages

        # If there's no chat history, the question is already standalone
        if len(history_messages) == 0:
            return question

        logging.info("Reformulating question based on chat history...")
        reformulate_prompt = ChatPromptTemplate.from_messages([
            ("system", "Given the following chat history and the user's latest follow-up question, rephrase the follow-up question to be a standalone question that can be understood without the chat history. Do NOT answer the question, just reformulate it if needed. If it doesn't need to be reformulated, return it as is."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])

        chain = reformulate_prompt | self.llm
        try:
            result = chain.invoke({
                "chat_history": history_messages,
                "question": question
            })
            standalone_q = result.content.strip()
            logging.info(f"Original Question: {question}")
            logging.info(f"Standalone Question: {standalone_q}")
            return standalone_q
        except Exception as e:
            logging.error(f"Error reformulating question: {e}")
            return question  # Fallback to original question



    def _best_matching_image(self, images, question):
        """
        Given a list of {url, alt} image dicts and the user's question,
        return only the single image whose alt text best matches the query.
        Returns a list with 0 or 1 image.
        """
        if not images:
            return []
        
        query_words = set(re.sub(r'[^a-zA-Z0-9\s]', '', question.lower()).split())
        stop_words = {'who', 'is', 'the', 'a', 'an', 'of', 'in', 'at', 'and', 'or', 'for', 'to', 'about', 'tell', 'me', 'what', 'how', 'dr', 'mr', 'mrs', 'professor', 'assistant', 'associate', 'head', 'department'}
        query_words = query_words - stop_words
        
        best_img = None
        best_score = 0
        
        for img in images:
            alt_lower = img['alt'].lower().replace('.', ' ').replace('-', ' ').replace('_', ' ')
            alt_words = set(alt_lower.split())
            score = len(query_words & alt_words)
            if score > best_score:
                best_score = score
                best_img = img
        
        if best_img and best_score > 0:
            return [best_img]
        return []

    def chatbot_response(self, question, chat_history=None):
        """
        Returns a tuple: (response_text, images_list)
        images_list is a list of {url, alt} dicts extracted from the top URLs' HTML.
        """
        logging.info(f"Generating chatbot response for question: {question}")

        history = chat_history if chat_history is not None else self.chat_history
        history_messages = history.messages if isinstance(history, ChatMessageHistory) else history
        
        # 1. Reformulate question using history
        standalone_question = self.reformulate_question(question, history_messages=history_messages)
        
        # 2. Retrieve URLs using the standalone question
        url_combined_keys = list(self.knowledge.keys())
        top3_urls = self.get_top3_urls(standalone_question, url_combined_keys)
        print("top3 urls:", top3_urls)
        
        if not top3_urls:
            error_msg = "I couldn't find any relevant pages to answer your question. Please check the terminal for API errors."
            if isinstance(history, ChatMessageHistory):
                history.add_user_message(question)
                history.add_ai_message(error_msg)
            return error_msg, []

        # 3. Extract content from knowledge base
        similar_content_list = [self.knowledge.get(url) for url in top3_urls if self.knowledge.get(url)]
        context_string = "\n\n---\n\n".join(similar_content_list)
        print(f"Extracted content length: {len(context_string)} characters")

        # 4. Extract images from top URLs' HTML, pick only the best match
        page_urls = [u for u in top3_urls if not self._is_pdf_url(u)]
        all_images = self.extract_images_from_urls(page_urls)
        images = self._best_matching_image(all_images, standalone_question)
        logging.info(f"Best matching image: {images}")

        # 5. Generate final answer with history and context
        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a GAC Salem 7 AI Assistant. Answer the user's question using the provided data.\n\nData Context:\n{context}\n\nDo not mention that you were given context, just answer naturally. When referencing PDFs or documents, always include their full URL as a clickable markdown link like [Document Name](url)."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])

        chain = qa_prompt | self.llm
        try:
            result = chain.invoke({
                "context": context_string, 
                "chat_history": history_messages,
                "question": question
            })
            
            # 6. Save the exchange to history
            if isinstance(history, ChatMessageHistory):
                history.add_user_message(question)
                history.add_ai_message(result.content)
            
            return result.content, images
        except Exception as e:
            print(f"\nCRITICAL ERROR in chatbot_response: {e}\n")
            logging.error(f"Error in chatbot_response: {e}")
            return f"An error occurred while generating the final response: {e}", []