# -*- coding: utf-8 -*-
"""
Created on Mon May  13 16:45:08 2019
 @author: Sina Ahmadi - Giulia Speranza - Carola Carlino - Patricia Martín Chozas - Itziar Gonzalez-Dios - Christian Lieske

  This project was presented in the 3rd Summer Datathon on
  Linguistic Linked Open Data (SD-LLOD-19) at Schloss Dagstuhl, 
  Leibniz Center for Informatics, Wadern, Germany. 
  More information at https://datathon2019.linguistic-lod.org/ .

"""
import re
import requests
import pandas as pd
from collections import OrderedDict
from wiktionaryparser import WiktionaryParser
from random import randint

# =========================================
# Templates
# =========================================
prefixes_templates = """
@prefix ontolex: <http://www.w3.org/ns/lemon/ontolex#> .
@prefix vartrans: <http://www.w3.org/ns/lemon/vartrans#> .
@prefix isocat: <http://www.isocat.org/datacat/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix iso639: <http://lexvo.org/id/iso639-1/> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix wd: <http://www.wikidata.org/entity/> .
@prefix : <#> .
"""
header_template = """
:TERM a ontolex:LexicalEntry, ontolex:Word ;
  ontolex:writtenRep "TERM"@LANG ;
  ontolex:sense :TERM_sense ;
  ontolex:denotes wd:TMID ;
  ontolex:denotes <TRMURL> ;
  dct:subject wd:SBJCT ; 
  dct:language <http://lexvo.org/id/iso639-1/LANG> .
"""

reference_template = """
:TERM_sense ontolex:reference <EXTURL> .
"""

plural_template = """
:TERM ontolex:otherForm TERM_plural .
:TERM_plural ontolex:writtenRep "TRMPLURAL"@LANG ;
lexinfo:number lexinfo:plural .
"""

pos_template = """
:TERM lexinfo:partOfSpeech lexinfo:POS ;
"""

gender_template = """
:TERM lexinfo:gender lexinfo:GENDER .
"""

translation_template = """
:LANG_NUM a ontolex:LexicalEntry;
  dct:language <http://lexvo.org/id/iso639-1/LANG> ;
  ontolex:sense :LANG_NUM_sense ;
  ontolex:writtenRep "TERMTARGET" .
:LANG_NUM_sense ontolex:reference <TERMTARGETURL> .

:trans a vartrans:Translation;
 vartrans:source :TERMSOURCE_sense ;
 vartrans:target :LANG_NUM_sense ;
 vartrans:category <http://purl.org/net/translation-categories#directEquivalent>.
"""

# =========================================
# Clean text by removing noisy characters
# =========================================
def clean_text(text):
  return text.replace("\n", "")
# =========================================
# Retrieving from Wiktionary
# =========================================
def wiktionary_retriever(word_list, lang):
  retrieved_words = dict()
  parser = WiktionaryParser()
  for word in word_list:
    retrieved_words[word] = parser.fetch(word, lang)

  wiktionary_dict = dict()
  for k, v in retrieved_words.items():
    try:
      if len(v) != 0:
        v = v[0]
        if len(v['definitions']) != 0:
          gender, plural = "", ""  
          # Check the information in the text field
          if lang == "italian":
            text = v['definitions'][0]['text'][0].replace(k, "").replace("\xa0", "").split(" (plural ")
          else:
            text = re.split(r'.*plural ', v['definitions'][0]['text'][0].replace(k, "").replace("\xa0", ""))

          if len(text) == 1:
            gender = text[0]
          elif len(text) >= 2:
            gender = text[0]
            if len(text[1].split(")")[0]) > 3:
              plural = text[1].split(")")[0].replace(")", "")
          else:
            pass        

          wiktionary_dict[k] = (clean_text(v['etymology']), v['definitions'][0]['partOfSpeech'], gender, plural)
        else:
          wiktionary_dict[k] = []  
      else:
        wiktionary_dict[k] = []
    except:
      print("wiktionary err:", k)

  return wiktionary_dict
# =========================================
# Create OntoLex triples based on the given variables
# =========================================
def ontolex_converter(info):
  header = header_template.replace("TERM", info["TERM"])
  for key in info:
    header = header.replace(key, str(info[key]))

  translation_text = header 
  translation_content_header = translation_template.replace("TERMSOURCE", info["TERM"])

  for tag in ["POS", "GENDER", "TRMPLURAL"]:
    if len(info[tag]) != 0:
      if tag == "POS":
        temp = pos_template
      elif tag == "GENDER":
        temp = gender_template
      elif tag == "TRMPLURAL":
        temp = plural_template
      else:
        pass
      translation_text += temp.replace("TERM", info["TERM"]).replace(tag, info[tag]).replace("LANG", info["LANG"])

  translations = info["translations"].values.tolist()
  for trans in translations:
    translation_content, pos_content, gender_content, plural_content = "", "", "", ""

    # Check not to include a triple of the language of the source term
    if trans[1] != info["LANG"]:
      translation_content = translation_content_header.replace("TERMTARGETURL", trans[0])
      translation_content = translation_content.replace("LANG", trans[1])
      translation_content = translation_content.replace("TERMTARGET", trans[2])
      translation_content = translation_content.replace("NUM", str(randint(10000, 99999)))

      if info["EXTURL"] != "":
        translation_content = translation_content.replace("EXTURL", info["EXTURL"])

      translation_text += "\n" + translation_content

  return translation_text

# =========================================
# Retrieving from Wikidata
# =========================================
def wikidata_retriever(terms, lang):
  url = 'https://query.wikidata.org/sparql'
  retrieve_query = """
  SELECT * {
   ?item rdfs:label "TERM"@LANG.
  }
  """
  # acroterio
  class_checker = """
  ask {
    wd:TERM_ID (wdt:P361|wdt:P279|wdt:P31)+ wd:SUBJECT .
  }
  """

  original_query = """
  SELECT DISTINCT * WHERE {
    ?article schema:about wd:TERM_ID;
             schema:inLanguage ?lang;
             schema:name ?name .
  }
  """
  Wikidata_dataset = dict()
  subjects = {"architecture":"Q12271", "archeology": "Q10855079", "law" : "Q7748",  "legal science" : "Q382995", "social issue" : "Q1920219", "jurisprudence" : "Q4932206", "rule" : "Q1151067", "Economy" : "Q159810", "Economics" : "Q8134", "labour law" : "Q628967", "human action" : "Q451967", "legal concept" : "Q2135465"}
  ""
  for term in terms: 
    try:
      print(term)
      if " " not in term: 
        query = retrieve_query.replace("TERM", term).replace("LANG", lang)
        r = requests.get(url, params = {'format': 'json', 'query': query})
        data = r.json()

        if len(data['results']['bindings']) != 0:
          item_id = data['results']['bindings'][0]['item']['value'].split("/")[-1]

          retrieved_subjects = dict()
          for subject in subjects: 
            query = class_checker.replace("TERM_ID", item_id).replace("SUBJECT", subjects[subject])
            r = requests.get(url, params = {'format': 'json', 'query': query})
            data = r.json()
            retrieved_subjects[subjects[subject]] = data['boolean']

          if True in retrieved_subjects.values():
            query = original_query.replace("TERM_ID", item_id)
            r = requests.get(url, params = {'format': 'json', 'query': query})
            data = r.json()

            retrieved = list()
            for item in data['results']['bindings']:
                retrieved.append(OrderedDict({
                    'article': item['article']['value'],
                    'lang': item['lang']['value'],
                    'name': item['name']['value']}))

            df = pd.DataFrame(retrieved)
            
            subj = list(retrieved_subjects.keys())[list(retrieved_subjects.values()).index(True)]
            termurl = ""
            
            for l in range(len(df['lang'])):
              if df['lang'][l] == "it":
                termurl = df['article'][l]
                break

            Wikidata_dataset[term] = {"TMID": item_id, "SBJCT": subj, "TRMURL": termurl, "translations": df, "LANG": lang}
    except:
      pass
  return Wikidata_dataset

# =========================================
# main
# =========================================
## List of words
# source_language = "english"
# source_language = "italian"
# source_file_dir = "SourceDatasets/100term.txt"
# source_file = open(source_file_dir, "r")
# terms = [t for t in source_file.read().split("\n")]
# terms_keys = terms#[0:10]#[80:90]
# ====
# ICCR 
source_language = "italian"
source_file_dir = "SourceDatasets/dataset-thesaurus_definizione_extracted.tsv"
source_file = open(source_file_dir, "r")
terms = {t.split("\t")[1].replace("\"", "").replace("@it", ""):t.split("\t")[0] for t in source_file.read().split("\n")}
terms_keys = list(terms.keys())[1000:]
  # terms_keys = ["colonna"]
output_file_name = "ICCR_dataset_1000END.txt"
# ====
source_file.close()

Wikidata_dataset = wikidata_retriever(terms_keys, lang=source_language[0:2])
print("Wikidata Data collected!")
Wiktionary_dataset = wiktionary_retriever(terms_keys, lang=source_language)
print("Wiktionary Data collected!")

genders = {"m": "masculine", "f": "feminine", "n": "neutral"}

# Writing the prefixes
with open(output_file_name, "a") as output_file:
  output_file.write(prefixes_templates)
  output_file.write("\n\n")

# Writing the body of the data
counter = 0
for term, v in Wikidata_dataset.items():
  # Adding additional information from Wiktionary entries to Wikidata collected data
  Wikidata_dataset[term]["TERM"] = term
  Wikidata_dataset[term]["EXTURL"] = ""
  Wikidata_dataset[term]["POS"] = ""
  Wikidata_dataset[term]["GENDER"] = ""
  Wikidata_dataset[term]["TRMPLURAL"] = ""

  # ICCR {Term: URI} dataset
  # Wikidata_dataset[term]["EXTURL"] = terms[term]
  Wikidata_dataset[term]["EXTURL"] = ""

  if len(Wiktionary_dataset[term]) != 0 and term != "":
    if len(Wiktionary_dataset[term][1]) > 2 and len(Wiktionary_dataset[term][1]) < 10:
      Wikidata_dataset[term]["POS"] = Wiktionary_dataset[term][1]
    # standarize gender
    if Wiktionary_dataset[term][2] == 1 :
      Wikidata_dataset[term]["GENDER"] = genders[Wiktionary_dataset[term][2]]

    if len(Wikidata_dataset[term]["TRMPLURAL"]) != 0:
      Wikidata_dataset[term]["TRMPLURAL"] = Wiktionary_dataset[term][3]

  ontolex_text = ontolex_converter(Wikidata_dataset[term])
  counter += 1
  with open(output_file_name, "a") as output_file:
    output_file.write(ontolex_text)
    output_file.write("\n\n")
  # except:
  #   pass

# print(ontolex_text)

print(counter)




