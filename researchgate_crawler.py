from bs4 import BeautifulSoup as soup
from unicodedata import normalize
from operator import itemgetter
from time import sleep
import urllib.request
from urllib.error import HTTPError


def main():
    url = 'https://www.researchgate.net/publication/328946507_Validation_of_a_wireless_shoe_insole_for_ground_reaction_force_measurement'
    keywords = "shoe insole ground reaction force pressure center"
    crawler = researchgate_crawler(url, keywords, output_file="./default_dump.csv", paper_output_count=10, http_request_delay=1)


class researchgate_crawler():
    # NECESSARY INITIALIZATIONS
    # init_url_string    -> str, researchgate URL up to the end of the paper title
    # keywords_string    -> str, space-separated words to search title and abstract for

    # OPTIONAL INITIALIZATIONS
    # output_file        -> str, path to output file for top-scoring links
    # paper_output_count -> int, number of top-scoring papers to output
    # http_request_delay -> int, seconds to wait after EACH http request to prevent Error 429: Too Many Requests

    def __init__(self, init_url_string, keywords_string, output_file="./default_dump.csv", paper_output_count=10, http_request_delay=1):
        # INPUTS FROM OBJECT INITIALIZATION
        self.keywords = keywords_string.split(" ")  # keywords for determining scoring
        self.filepath = output_file  # path to dump URLs to when done
        self.num_papers = paper_output_count  # total number of tracked papers
        self.loop_delay = http_request_delay #seconds, prevents Error 429: Too Many Requests

        # USER-MODIFIABLE VARIABLES
        self.score_threshold = max(2, len(self.keywords)//2) #minimum score threshold to pull links. min 2 or half number of keywords
        self.max_iter = 1000 #max number of checked papers

        # Class variable initializations
        self.processed_doi_list = [] #ALL processed papers have DOI added here to prevent duplicates
        self.link_list = [init_url_string] #Constantly changing buffer of links to process
        self.top_scores = [] #scores stored as [score,doi]
        self.iter = 0 #stores number of papers checked

        # Start crawler
        self.run()

    def run(self):
        while len(self.link_list) > 0 and self.iter < self.max_iter:
            self.iter += 1
            url = self.link_list[0]
            print(url)

            try:
                #process abstract of first link in stack: add to DOI store
                cite, doi, word_dump = self.pull_citation_info(url)
                if doi not in self.processed_doi_list:
                    self.processed_doi_list.append(doi)

                    #give paper score, check against top scores and update listings
                    paper_score = self.get_score(word_dump)
                    self.update_score(paper_score, url)

                    #if paper meets a minimum score, grab links and add to list
                    if paper_score > self.score_threshold:
                        self.link_list = self.link_list + self.pull_links(url)

            #Bypass rest of analysis and saving for paper if there is  problem with fields
            except TypeError:
                pass
            except ValueError:
                pass

            #Let user know if server has stopped allowing requests because we pissed it off
            except HTTPError as e:
                print(e)
                print("Please wait :")
                print(e.headers["Retry-After"])
                break

            # remove current link from end of link_list
            self.link_list.pop(0)

    def get_score(self, words):
        #Counts occurrences of keywords
        score = 0
        for keyword in self.keywords:
            score += words.lower().count(keyword)
        return score

    def write_top_scores_to_file(self):
        #Writes links from top-scoring papers into simple file
        f = open(self.filepath, "w+")
        for pair in self.top_scores:
            f.write(f'{pair[1]}+\n')
        f.close()

    def update_score(self, test_score, link):
        # If array is empty, put anything in it
        if len(self.top_scores) < self.num_papers:
            self.top_scores.append([test_score, link])
            self.top_scores = sorted(self.top_scores, key=itemgetter(0))

        # When array is not empty, heck if score is higher than lowest
        elif test_score > self.top_scores[0][0]:
            self.top_scores.append([test_score, link])
            self.top_scores = sorted(self.top_scores, key=itemgetter(0))
            self.top_scores.pop(0)
            self.write_top_scores_to_file()

        # If array is too full, start taking shit away without adding anything back
        elif len(self.top_scores) > self.num_papers:
            self.top_scores = sorted(self.top_scores, key=itemgetter(0))
            self.top_scores.pop(0)

    def get_soup(self, url):
        # Given a url, parse the HTML with soup as a fake firefox client and return
        url_client = urllib.request.Request(url, headers={'User-Agent': 'Firefox/5.0'})
        raw_page = urllib.request.urlopen(url_client).read()
        page = raw_page.decode('ISO-8859-1')
        soupage = soup(page, "html.parser")
        sleep(self.loop_delay)

        return soupage

    def iterate_containers(self, soupage):
        # Used to pull all links from either references or citations page

        # Initialize storage
        storage = []

        # Grab all reference/citation containers, then iterate over them to extract link
        try:
            item_containers = soupage.findAll("div", {"class": "nova-legacy-v-publication-item__stack nova-legacy-v-publication-item__stack--gutter-m"})
            for container in item_containers:
                paper_link = container.div.div.a["href"]
                paper_link = 'https://www.researchgate.net/' + paper_link
                storage.append(paper_link)
        except TypeError:
            pass

        return storage

    def pull_links(self, url):
        # Given a researchgate paper, grab links to all linked references and citations

        # Get links from resources
        soupage = self.get_soup(url + "/references")
        resource_storage = self.iterate_containers(soupage)

        # Get links from citations
        soupage = self.get_soup(url + "/citations")
        citation_storage = self.iterate_containers(soupage)

        # Concatenate and return
        link_storage = resource_storage + citation_storage
        return link_storage

    def print_soup(self, soupage):
        #Unused, dumps complete HTML source to file
        f = open('soupage.html', "w+")
        for char in soupage.prettify():
            try:
                f.write(char)
            except UnicodeEncodeError:
                pass

    def normalize_input_characters(self, data):
        #removes odd characters from strings
        enc_str = str(normalize('NFKD', data).encode('ASCII', 'ignore'))
        return enc_str[2:len(enc_str)-1]

    def pull_citation_info(self, url):
        soupage = self.get_soup(url)

        # Get title info
        title = soupage.find("h1", {"class": "nova-legacy-e-text nova-legacy-e-text--size-xl nova-legacy-e-text--family-sans-serif nova-legacy-e-text--spacing-none nova-legacy-e-text--color-grey-900 research-detail-header-section__title"})
        title = title.text

        # Get publication info (date, month, journal)
        pub_info = soupage.find("ul", {"class": "nova-legacy-e-list nova-legacy-e-list--size-m nova-legacy-e-list--type-inline nova-legacy-e-list--spacing-none"})
        pub_date = (pub_info.li).text
        pub_month, pub_year = pub_date.split(" ")
        journal_info = (pub_info.text).replace(pub_date, "")

        # Get DOI
        doi = soupage.find("a", {"class": "nova-legacy-e-link nova-legacy-e-link--color-inherit nova-legacy-e-link--theme-decorated", "rel":"noopener"})
        doi = doi.text

        # Get authors, process authors
        author_containers = soupage.findAll("div", {"class": "nova-legacy-v-person-list-item__stack nova-legacy-v-person-list-item__stack--gutter-s"})
        author_string = ""
        for author in author_containers:
            author_name = self.normalize_input_characters(author.div.div.div.div.a.text)
            author_string = author_string + author_name + " & "
        author_string = author_string[0:len(author_string)-3]
        author_string.replace(",","")
        author_string = author_string + ","

        # Get abstract
        abstract = soupage.find("div", {"class": "nova-legacy-c-card__body nova-legacy-c-card__body--spacing-inherit"})
        abstract = abstract.text

        # Create citation
        citation = f"{author_string} {pub_year}. \"{title}\" {journal_info}. doi:{doi}"
        word_search = title + " " + abstract

        return citation, doi, word_search


if __name__ == "__main__":
    main()
