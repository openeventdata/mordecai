---
title: "Mordecai: Full Text Geoparsing and Event Geocoding"
tags:
  - Python
  - geocoding
  - geoparsing
  - natural language processing
  - word embeddings
authors:
  - name: Andrew Halterman
  - orcid: 0000-0001-9716-9555
affiliation: MIT
date: 4 September 2016
bibliography: paper.bib
---

# Summary

Mordecai is a new full-text geoparsing system that extracts place names from
text, resolves them to their correct entries in a gazetteer, and returns
structured geographic information for the resolved place name. Mordecai's key
innovations are in a language-agnostic architecture that uses word2vec
[@mikolov2013efficient] for inferring the correct country for a set of
locations in a piece of text and easily changed named entity recognition
models. As a gazetteer, it uses Geonames [@geonames] in a custom-build
Elasticsearch database.

# References
