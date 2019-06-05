# -*- coding: utf-8 -*-
"""
Created on Mon May  13 16:45:08 2019
 @author: Sina Ahmadi - Patricia Martín Chozas  .

"""
import requests
import pandas as pd
from collections import OrderedDict
from random import randint

# =========================================
# SKOS template
# =========================================
prefixes_templates = """
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>.
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix iso639: <http://lexvo.org/id/iso639-1/> .
@prefix wd: <http://www.wikidata.org/entity/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#>.
@prefix : <#> .
"""
concept_template = """
<http://lkg.lynx-project.eu/kos/labourlaw_terms/SCTMID> a skos:Concept; 
skos:closeMatch <https://www.wikidata.org/wiki/WDTMID>;
skos:prefLabel CONCAT;
"""

desc_template = """
skos:description CONCAT1;
"""

alt_template = """
skos:altLabel CONCAT2; 
"""

br_template = """
skos:broader <https://www.wikidata.org/wiki/WDBRTMID>; 
"""

nr_template = """
skos:narrower <https://www.wikidata.org/wiki/WDNRTMID>; 
"""
re_template = """
skos:related <https://www.wikidata.org/wiki/WDRLTMID>; 
"""

brconcept_temp = """
<http://lkg.lynx-project.eu/kos/labourlaw/LTBRTMID> a skos:Concept;
skos:exactMatch <https://www.wikidata.org/wiki/WDBRTMID> .
"""

brconceptlab_temp = """
skos:prefLabel CONCAT3 ;
"""

nrconcept_temp = """
<http://lkg.lynx-project.eu/kos/labourlaw/LTNRTMID> a skos:Concept;
skos:exactMatch <https://www.wikidata.org/wiki/WDNRTMID> .
"""
nrconceptlab_temp = """
skos:prefLabel CONCAT4 ;
"""

reconcept_temp = """
<http://lkg.lynx-project.eu/kos/labourlaw/LTRLTMID> a skos:Concept;
skos:exactMatch <https://www.wikidata.org/wiki/WDRLTMID> .
"""
reconceptlab_temp = """
skos:prefLabel CONCAT5 ;
"""


# =========================================
# Clean text by removing noisy characters
# =========================================
def clean_text(text):
    return text.replace("\n", "")


# =========================================
# Creation of numeric ID for source terms
# =========================================
def sctmid_creator():
    numb = randint(1000000, 9999999)

    SCTMID = "LT" + str(numb)
    return SCTMID


# =========================================
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
    wd:WDTMID (wdt:P361|wdt:P279|wdt:P31)+ wd:SUBJECT .
  }
  """

    original_query = """
  SELECT DISTINCT * WHERE {
  ?article schema:about wd:WDTMID;
           schema:inLanguage ?lang;
           schema:name ?name.
  wd:WDTMID schema:description ?desc.
  FILTER(?lang in ('es', 'de', 'nl', 'en'))  
  FILTER (lang(?name) = lang(?desc))
  } ORDER BY ?lang
  """
    Wikidata_dataset = dict()
    subjects = {"policy": "Q1156854", "leave of absence": "Q13561011", "sources of law": "Q846882", "rights policy": "Q2135597", "comparative law": "Q741338", "sociology of law ": "Q847034",
                "legal doctrine": "Q1192543", "area of law": "Q1756157", "law": "Q7748", "legal science": "Q382995",
                "social issue": "Q1920219", "jurisprudence": "Q4932206", "rule": "Q1151067", "Economy": "Q159810",
                "Economics": "Q8134", "labour law": "Q628967", "human action": "Q451967", "legal concept": "Q2135465"}
    ""
    for term in terms:
        try:
            print(term)
            query = retrieve_query.replace("TERM", term).replace("LANG", lang)
            r = requests.get(url, params={'format': 'json', 'query': query})
            data = r.json()

            if len(data['results']['bindings']) != 0:
                item_id = data['results']['bindings'][0]['item']['value'].split("/")[-1]

                retrieved_subjects = dict()
                for subject in subjects:
                    query = class_checker.replace("WDTMID", item_id).replace("SUBJECT", subjects[subject])
                    r = requests.get(url, params={'format': 'json', 'query': query})
                    data = r.json()
                    retrieved_subjects[subjects[subject]] = data['boolean']

                if True in retrieved_subjects.values():
                    query = original_query.replace("WDTMID", item_id)
                    r = requests.get(url, params={'format': 'json', 'query': query})
                    data = r.json()

                    retrieved = list()
                    for item in data['results']['bindings']:
                        retrieved.append(OrderedDict({
                            'desc': item['desc']['value'],
                            'lang': item['lang']['value'],
                            'name': item['name']['value']}))

                    df = pd.DataFrame(retrieved)

                    subj = list(retrieved_subjects.keys())[list(retrieved_subjects.values()).index(True)]

                    Wikidata_dataset[term] = {"WDTMID": item_id, "SBJCT": subj, "translations": df}

        except:
            pass

    return Wikidata_dataset


# =========================================
# Creation of SKOS model with the collected info
# he quitado el zip. no faltaría un return?
# =========================================
def skos_converter(info, sctmid):
    skos = open('results.rdf', 'w+')
    skos.write(prefixes_templates + '\n')
    errors = open('errors.txt','w+')


    for key in info:
        concat = ""
        concat1 = ""
        translations = info[key]["translations"]
        if translations.empty:
            errors.write(key+'\n')
        else:
            for lang, desc in zip(translations['lang'], translations['desc']):
                concat1 += "\"" + desc + "\"@" + lang + ", "
            concat1 = concat1[:-2]
            for lang,name in zip(translations['lang'], translations['name']):
                concat+=  "\"" + name + "\"@" + lang + ", "
            concat = concat[:-2]

            # for lang, name in translations.items():
            #     concat += "\"" + name + "\"@" + lang + ", "
            #
            # for lang, desc in translations.items():
            #     concat1 += "\"" + desc + "\"@" + lang + ", "

                # concat = concat[:-1]
                # concat1 = concat1[:-1]

            header = concept_template.replace("CONCAT", concat).replace("WDTMID", info[key]["WDTMID"]).replace("SCTMID",
                                                                                                                   sctmid[key])
            body = desc_template.replace("CONCAT1", concat1)

            file = header + '\n' + body + '\n'

            skos.write(file)
    skos.close()
    # for key in info:
    #     concat1 = ""
    #     translations = info[key]["translations"]
    #     for lang, desc in zip(translations['lang'], translations['desc']):
    #         concat1 += "\"" + desc + "\"@" + lang + ", "
    #     concat1 = concat1[:-2]
    #
    #     body = desc_template.replace("CONCAT1", concat1)




# =========================================
# main
# =========================================
## List of words
source_language = "english"
source_file_dir = "100term.csv"
source_file = open(source_file_dir, "r")
terms = [t for t in source_file.read().split("\n")]
terms_keys = terms  # [0:10]#[80:90]
scterm={}

#Giving an ID to each term and saving the dict in a csv file
for t in terms_keys:
    sctmid = sctmid_creator()
    scterm[t]=sctmid

a=open('scterm_dict.csv','w+')
for k,i in scterm.items():
    a.write(k+' , '+i+'\n')
a.close()

Wikidata_dataset = wikidata_retriever(terms_keys, lang=source_language[0:2])
print("Wikidata Data collected!")


b= skos_converter(Wikidata_dataset,scterm)
