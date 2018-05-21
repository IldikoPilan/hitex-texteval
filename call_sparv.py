# -*- coding: utf-8 -*-
import httplib
import urllib
import xml.etree.ElementTree as ET

# SPARV
SB_SERVER = "ws.spraakbanken.gu.se" 
SPARV = "/ws/sparv/v2/?"

def call_sparv(text):
    """
    Annotates 'text' with the Sparv API (previously Annotation Lab). 
    Returns a string with the annotated text as an XML.
    """
    conn = httplib.HTTPSConnection(SB_SERVER)
    try:
        text = text.encode("utf-8")
    except UnicodeDecodeError:
        text = text
    text_input = urllib.urlencode({"text" : text})
    conn.request("GET", SPARV + text_input)
    response = conn.getresponse()
    if response.status == 200:
        out = response.read()
    else:
        out = None
    conn.close()
    return out

def parse_resp(response):
    """
    Dummy XML parsing function, just an example.
    """
    result = ET.fromstring(response)
    corpus = result[1]
    for paragr in corpus:
        for sent in paragr:
            for token in sent:
                print token.attrib["pos"]
    return corpus

## Example run:
# response = call_sparv("Jag är hungrig ; och bla + bok.")
# print response
# parse_resp(response)