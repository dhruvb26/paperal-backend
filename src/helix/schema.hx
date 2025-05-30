// Initial schema for the graph
// Each one of them also has an implicit ID field

N::Origin {
    content: String, // content of the chunk
}

N::Cited {
    title: String, // title of the cited paper
    content: String, // content of the cited paper (possibly a summary)
}

E::Cites {
    From: Origin,
    To: Cited,
}