Scorer['score'] = result => {
  const [docName, title, anchor, descr, score, filename] = result
  if(filename.search("/reference\/modules\/.*\/autodoc\.html$/")) {
    // This is documentation that was automatically generated.
    // Put it last in the search results to prevent that a word,
    // that is present in each of this generated pages, clutters
    // the search results.
    return -5
  } else {
    // Rely on the score assigned by the default scoring algorithm.
    return score
  }
};
