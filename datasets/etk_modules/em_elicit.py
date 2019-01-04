from etk.extractors.html_content_extractor import HTMLContentExtractor, Strategy
from etk.extractors.html_metadata_extractor import HTMLMetadataExtractor
from etk.etk_module import ETKModule
from etk.extractors.date_extractor import DateExtractor
from etk.extractors.glossary_extractor import GlossaryExtractor


class DemoElicitETKModule(ETKModule):
    """
    Abstract class for extraction module
    """

    def __init__(self, etk):
        ETKModule.__init__(self, etk)
        self.metadata_extractor = HTMLMetadataExtractor()
        self.content_extractor = HTMLContentExtractor()
        self.date_extractor = DateExtractor(self.etk, 'acled_date_parser')
        self.country_extractor = GlossaryExtractor(
            self.etk.load_glossary(
                "${GLOSSARY_PATH}/countries.txt"),
            "country_extractor",
            self.etk.default_tokenizer,
            case_sensitive=False, ngrams=3)
        self.cities_extractor = GlossaryExtractor(
            self.etk.load_glossary(
                "${GLOSSARY_PATH}/cities.txt"),
            "cities_extractor",
            self.etk.default_tokenizer,
            case_sensitive=False, ngrams=3)

    def process_document(self, doc):
        """
        Add your code for processing the document
        """

        raw = doc.select_segments("$.raw_content")[0]

        doc.store(doc.extract(self.content_extractor, raw, strategy=Strategy.ALL_TEXT), "etk2_text")
        doc.store(doc.extract(self.content_extractor, raw, strategy=Strategy.MAIN_CONTENT_STRICT),
                  "etk2_content_strict")
        doc.store(doc.extract(self.content_extractor, raw, strategy=Strategy.MAIN_CONTENT_RELAXED),
                  "etk2_content_relaxed")
        doc.store(doc.extract(self.metadata_extractor,
                              raw,
                              extract_title=True,
                              extract_meta=True,
                              extract_microdata=True,
                              extract_rdfa=True,
                              ), "etk2_metadata")
        doc.kg.add_value("description", json_path="$.etk2_content_strict")
        doc.kg.add_value("title", json_path="$.etk2_metadata.title")

        description_segments = doc.select_segments(jsonpath='$.etk2_content_strict')
        for segment in description_segments:
            extractions = doc.extract(extractor=self.date_extractor, extractable=segment)
            for extraction in extractions:
                doc.kg.add_value("event_date", value=extraction.value)

                extracted_countries = doc.extract(
                    self.country_extractor, segment)
                doc.kg.add_value('country', value=extracted_countries)

                extracted_cities = doc.extract(self.cities_extractor, segment)
                doc.kg.add_value('city', value=extracted_cities)

        return list()

    def document_selector(self, doc) -> bool:
        return doc.cdr_document.get("url").startswith("http://www.ce_news_article.org")
