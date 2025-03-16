import os
import re
import json
import logging
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import AsyncHtmlLoader
from langchain_community.document_transformers import Html2TextTransformer
from langchain_mistralai import ChatMistralAI

load_dotenv()
# Configure logging
logging.basicConfig(
    filename="college_bot.log",  # Log file name
    level=logging.DEBUG,  # Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(levelname)s - %(message)s"  # Log format
)

class College:
    def __init__(self):
        logging.info("Initializing College class...")  # Log initialization
        self.api_key = os.getenv("API_KEY")
        self.llm = ChatMistralAI(
            model="mistral-large-latest",
            temperature=0,
            max_retries=2,
            api_key=self.api_key
        )

        self.sitemap_url_post_page = 'https://gacsalem7.ac.in/wp-sitemap-posts-page-1.xml'
        self.sitemap_url_our_team = 'https://gacsalem7.ac.in/wp-sitemap-posts-our_team-1.xml'

        self.knowledge = self.map_url_and_content()

    def filter_urls(self, urls):
        logging.info("Filtering URLs...")
        filtered_urls = []
        for url in urls:
            if (
                url.endswith('.pdf') or
                'void(0)' in url or
                '/blog/' in url or
                '#' in url or
                url.endswith('.png') or
                'po-pso-co' in url or
                '%' in url or
                re.search(r'\d{1,2}-\d{1,2}-\d{4}|\d{4}-\d{4}', url)
            ):
                continue
            filtered_urls.append(url)

        logging.debug(f"Filtered URLs: {filtered_urls[:5]}... (total: {len(filtered_urls)})")
        return filtered_urls

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
            response = requests.get(sitemap_url)
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
            html2text = Html2TextTransformer()
            docs_transformed = html2text.transform_documents(docs)
            logging.debug(f"Extracted {len(docs_transformed)} documents.")
            return docs_transformed
        except Exception as e:
            logging.error(f"Error in extract_data: {e}")
            return []

    def map_url_and_content(self):
        logging.info("Mapping URLs to content...")
        url_and_content = {}
        post_page_url_list = self.get_valid_urls(self.sitemap_url_post_page)
        filtered_post_page_url_list = self.filter_urls(post_page_url_list)

        our_team_url_list = self.get_valid_urls(self.sitemap_url_our_team)

        post_page = self.extract_data(filtered_post_page_url_list)
        our_team_page = self.extract_data(our_team_url_list)

        for post_page_context in post_page:
            clean_content = self.remove_footer(self.remove_header(post_page_context.page_content))
            url_and_content[post_page_context.metadata.get("source")] = clean_content

        for our_team_page_context in our_team_page:
            clean_content = self.remove_footer(self.remove_header(our_team_page_context.page_content))
            url_and_content[our_team_page_context.metadata.get("source")] = clean_content

        logging.info(f"Mapped {len(url_and_content)} URLs to content.")
        return url_and_content

    def get_top3_urls(self, question, url_combined,retry=3):
        logging.info(f"Fetching top 3 URLs for question: {question}")

        prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    '''You are a specialized URL retriever assistant for a college website. Your task is to analyze the user's question and return the top 3 URLs from the provided list that best match the query. The list (provided as {context}) includes URLs for various college resources such as departmental pages, professor profiles, and staff directories.

            Your response must be strictly in JSON format as follows:

            json
            {{"urls": ["<URL1>", "<URL2>", "<URL3>"]}}

            Important instructions:
            - Focus primarily on retrieving URLs related to college staff and administrative personnel, especially if the question includes keywords such as "staff", "administration", "support staff", or "faculty staff".
            - Analyze and expand common college abbreviations found in the question. For example, interpret "cs" as "computer science", "bba" as "Bachelor of Business Administration", etc.
            - Use both the expanded forms and the specific keywords in the user's question to filter and rank the relevant URLs from the context.
            - Only include URLs that are highly relevant to the user's query.
            - If there are fewer than three relevant URLs, return only the available ones.
            - Do not include any extra text outside the JSON structure.'''
                ),
                (
                    "human",
                    "User question: {question}"
                )
            ])


        chain = prompt | self.llm
        try:

            result = chain.invoke({"question": question, "context": url_combined})
            print("result top3",result.content)
            result = json.loads(result.content.replace("```json\n", "").replace("\n```", ""))

            logging.debug(f"Top 3 URLs: {result.get('urls')}")
            return result.get("urls")
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            if retry > 0:
                logging.info(f"Retrying get_top3_urls, retries left: {retry}")
                return self.get_top3_urls(question, url_combined, retry=retry-1)
            else:
                logging.error("Max retries exceeded for get_top3_urls")
                return []
        except Exception as e:
            logging.error(f"Error in get_top3_urls: {e}")
            return []

    def chatbot_response(self, question):
        logging.info(f"Generating chatbot response for question: {question}")
        url_combined_keys = list(self.knowledge.keys())
        top3_urls = self.get_top3_urls(question, url_combined_keys)
        print("top3 urls:",top3_urls)
        similar_content = [self.knowledge.get(url) for url in top3_urls]
        print("similar content:",similar_content)
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a GAC Salem 7 AI Assistant. Your task is to answer the user's question using the provided data. Ensure that your response is clear, accurate, and directly references the context when relevant. If the provided data does not fully address the question, indicate any uncertainties or ask for clarification as needed.\n\nAdditionally, if the user's input is solely a greeting (for example, 'hello', 'hi', etc.), respond with an appropriate greeting message instead of the usual answer.\n\nUser question: {question}\n\nData: {context}"),
            ("human", "User question: {question}")
        ])

        chain = prompt | self.llm
        try:
            result = chain.invoke({"question": question, "context": similar_content})
            logging.debug(f"Chatbot response generated successfully.")
            return result.content
        except Exception as e:
            logging.error(f"Error in chatbot_response: {e}")
            return "An error occurred while processing your request."
