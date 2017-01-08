---
title: "Mordecai: Full Text Geoparsing and Event Geocoding"
tags:
  - geocoding
  - geoparsing
  - natural language processing
  - Python
  - word embeddings
authors:
  - name: Andrew Halterman
    orcid: 0000-0001-9716-9555
    affiliation: 1
affiliations:
  - name: MIT
    index: 1
date: 8 December 2017
bibliography: paper.bib
---

# Summary

Mordecai is a new full-text geoparsing system that extracts place names from
text, resolves them to their correct entries in a gazetteer, and returns
structured geographic information for the resolved place name. Geoparsing can
be used in a number of tasks, including media monitoring, improved information
extraction, document annotation for search, and geolocating text-derived event
data, which is the task for which is was built. Mordecai was created to provide
provide several features missing in existing geoparsers, including better
handling of non-US place names, easy and portable setup and use though a Docker
REST architecture, and easy customization with Python and swappable named
entity recognition systems. Mordecai's key technical innovations are in a
language-agnostic architecture that uses word2vec [@mikolov2013efficient] for
inferring the correct country for a set of locations in a piece of text and
easily changed named entity recognition models. As a gazetteer, it uses
Geonames [@geonames] in a custom-build Elasticsearch database.

# References
