import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from langchain_community.document_loaders import AsyncHtmlLoader
from langchain_community.document_transformers import Html2TextTransformer


class ExtractClgData:
    def __init__(self):
        pass
  
    def is_valid_url(self,url, base_domain):
        """Check if the URL is valid, belongs to the same domain, is not a .pdf, does not contain javascript:void(0),
        and ends with a slash."""
        parsed_url = urlparse(url)
        same_domain = bool(parsed_url.netloc) and parsed_url.netloc == base_domain
        not_unwanted = not url.endswith('.pdf') and 'void(0)' and "blog" and "%" not in url and url.endswith('/')

        return same_domain and not_unwanted

    def get_all_subpages(self):
        """Get all subpages of the given URL."""
        url="https://gacsalem7.ac.in/staff/"
        base_domain = urlparse(url).netloc
        visited = set()
        pages_to_visit = {url}
        discovered_urls = set()
        failed_urls = []
        extraction_errors = []

        while pages_to_visit:
            current_page = pages_to_visit.pop()
            try:
                print(f"Visiting: {current_page}")
                response = requests.get(current_page)

                try:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    visited.add(current_page)

                    for link in soup.find_all('a', href=True):
                        full_url = urljoin(current_page, link['href'])
                        if self.is_valid_url(full_url, base_domain) and full_url not in discovered_urls:
                            pages_to_visit.add(full_url)
                            discovered_urls.add(full_url)
                            break
                except Exception as e:
                    return f"Error extracting content from {current_page}: {e}"
                    extraction_errors.append(current_page)

            except requests.RequestException as e:
                    return f"error {e}"

        return list(visited)

    def remove_header(self, input_content):
        # Define the pattern to remove the header
        header_pattern = re.compile(r"(?s)\* Home.*?\* STUDENTS")
        header_removed_text = re.sub(header_pattern, "", input_content).strip()
        return header_removed_text

    def remove_fooder(self, input_content):
        # Define the pattern to remove the footer
        footer_pattern = re.compile(r"(?s)__\n\n### Who we are.*?__")
        fooder_removed_text = re.sub(footer_pattern, "", input_content).strip()
        return fooder_removed_text


    def html2text_loader(self,url_list):
        loader = AsyncHtmlLoader(url_list)
        docs = loader.load()
        html2text = Html2TextTransformer()
        docs_transformed = html2text.transform_documents(docs)
        return docs_transformed
        
    def content_save_as_txt(self):
        url_list=self.get_all_subpages()
        data=""
        knowledge_base=[]
        docs_transformed=self.html2text_loader(url_list)

        for k in range(len(docs_transformed)):
            content=docs_transformed[k].page_content
            header_removed_text_=self.remove_header(content)
            fooder_removed_text=self.remove_fooder(header_removed_text_)
            knowledge_base.append(fooder_removed_text)
        url_content_=data.join(knowledge_base)

        filepath=f"collage_data.txt"
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(url_content_)
        return filepath


if __name__=="__main__":
  extract_clg_data=ExtractClgData()
  extract_clg_data.content_save_as_txt()